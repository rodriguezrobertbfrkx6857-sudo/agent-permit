"""Transactional tool authorization with opaque, expiring, single-use capabilities."""

import hashlib
import json
import secrets
import time
from pathlib import PurePosixPath

from fastapi import HTTPException

from app.platform import canonical, database


def connect():
    db = database()
    db.execute(
        "CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY,tool TEXT,args TEXT,digest TEXT,state TEXT,token_hash TEXT,expires REAL,result TEXT,idempotency TEXT)"
    )
    db.execute("CREATE TABLE IF NOT EXISTS notes(path TEXT PRIMARY KEY,content TEXT)")
    return db


def policy(tool, args):
    if tool not in {"notes.read", "notes.write"}:
        return "deny", "Tool is outside the allowlist. Network and shell execution are unavailable."
    expected = {"path"} if tool == "notes.read" else {"path", "content"}
    if set(args) != expected:
        return "deny", "Arguments do not match the exact tool schema."
    path = args.get("path")
    if not isinstance(path, str) or len(path) > 150:
        return "deny", "Invalid resource path."
    parts = path.split("/")
    if any(p in {"", ".", ".."} for p in parts) or any(c in path for c in ["\\", "%", ":", "\0"]):
        return "deny", "Path traversal or ambiguous encoding."
    if not path.startswith("reports/") or PurePosixPath(path).suffix != ".md":
        return "deny", "Capability is scoped to reports/*.md."
    if tool == "notes.write" and (not isinstance(args["content"], str) or len(args["content"]) > 4000):
        return "deny", "Content must be a string of at most 4000 characters."
    return (
        ("approve", "Writes require independent reviewer approval.")
        if tool == "notes.write"
        else ("allow", "Read operation within the notes namespace.")
    )


def issue():
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def propose(tool, args):
    decision, reason = policy(tool, args)
    identifier = secrets.token_hex(12)
    digest = hashlib.sha256(canonical({"tool": tool, "args": args}).encode()).hexdigest()
    token, hashed = issue() if decision == "allow" else ("", "")
    state = {"allow": "approved", "approve": "pending", "deny": "denied"}[decision]
    expires = time.time() + 300
    with connect() as db:
        db.execute(
            "INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?,?)",
            (identifier, tool, canonical(args), digest, state, hashed, expires, None, None),
        )
    return {
        "id": identifier,
        "state": state,
        "reason": reason,
        "argument_digest": digest,
        "capability": token or None,
        "expires_at": expires,
        "tool": tool,
    }


def approve(identifier):
    token, hashed = issue()
    expires = time.time() + 300
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM proposals WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise HTTPException(404, "Proposal not found")
        if row["state"] != "pending":
            raise HTTPException(409, "Only pending proposals can be approved")
        if row["expires"] < time.time():
            raise HTTPException(410, "Proposal expired; submit a new proposal")
        db.execute(
            "UPDATE proposals SET state='approved',token_hash=?,expires=? WHERE id=?",
            (hashed, expires, identifier),
        )
    return {
        "id": identifier,
        "state": "approved",
        "capability": token,
        "expires_at": expires,
        "argument_digest": row["digest"],
    }


def execute(identifier, token, key):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM proposals WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise HTTPException(404, "Proposal not found")
        if not row["token_hash"] or not secrets.compare_digest(
            hashlib.sha256(token.encode()).hexdigest(), row["token_hash"]
        ):
            raise HTTPException(403, "Invalid capability")
        if row["state"] == "executed":
            if row["idempotency"] == key:
                return {**json.loads(row["result"]), "replayed": True}
            raise HTTPException(409, "Capability already consumed")
        if row["state"] != "approved":
            raise HTTPException(403, "Proposal is not approved")
        if row["expires"] < time.time():
            raise HTTPException(410, "Capability expired")
        args = json.loads(row["args"])
        digest = hashlib.sha256(canonical({"tool": row["tool"], "args": args}).encode()).hexdigest()
        if digest != row["digest"] or policy(row["tool"], args)[0] == "deny":
            raise HTTPException(403, "Arguments changed or policy denied")
        if row["tool"] == "notes.write":
            db.execute(
                "INSERT INTO notes VALUES(?,?) ON CONFLICT(path) DO UPDATE SET content=excluded.content",
                (args["path"], args["content"]),
            )
            output = {"path": args["path"], "bytes_written": len(args["content"].encode())}
        else:
            note = db.execute("SELECT content FROM notes WHERE path=?", (args["path"],)).fetchone()
            output = {"path": args["path"], "content": note[0] if note else None}
        result = {"id": identifier, "state": "executed", "output": output, "replayed": False}
        db.execute(
            "UPDATE proposals SET state='executed',result=?,idempotency=? WHERE id=?",
            (canonical(result), key, identifier),
        )
    return result


def proposals():
    with connect() as db:
        return [
            dict(r)
            for r in db.execute(
                "SELECT id,tool,args,digest,state,expires FROM proposals ORDER BY rowid DESC LIMIT 40"
            )
        ]
