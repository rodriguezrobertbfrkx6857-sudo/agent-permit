from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException

from app.control import approve, connect, execute, policy, propose


@pytest.mark.parametrize(
    "path",
    [
        "../secret.md",
        "reports/../secret.md",
        "reports//x.md",
        "reports/./x.md",
        "reports/%2e%2e/x.md",
        "reports\\x.md",
        "/reports/x.md",
        "reports/x.exe",
        "reports/c:x.md",
    ],
)
def test_paths(path):
    assert policy("notes.read", {"path": path})[0] == "deny"


def test_allowlist():
    assert policy("shell", {"command": "pwd"})[0] == "deny"
    assert policy("notes.read", {"path": "reports/a.md", "extra": True})[0] == "deny"


def test_approval_consumption_and_retry():
    p = propose("notes.write", {"path": "reports/a.md", "content": "approved content"})
    assert p["state"] == "pending"
    a = approve(p["id"])
    first = execute(p["id"], a["capability"], "request-0001")
    assert first["output"]["bytes_written"] == 16
    assert execute(p["id"], a["capability"], "request-0001")["replayed"]
    with pytest.raises(HTTPException) as e:
        execute(p["id"], a["capability"], "request-0002")
    assert e.value.status_code == 409
    read = propose("notes.read", {"path": "reports/a.md"})
    assert execute(read["id"], read["capability"], "request-0003")["output"]["content"] == "approved content"


def test_expiry():
    p = propose("notes.read", {"path": "reports/a.md"})
    with connect() as db:
        db.execute("UPDATE proposals SET expires=0 WHERE id=?", (p["id"],))
    with pytest.raises(HTTPException) as e:
        execute(p["id"], p["capability"], "request-0001")
    assert e.value.status_code == 410


def test_mutated_arguments_rejected():
    p = propose("notes.read", {"path": "reports/a.md"})
    with connect() as db:
        db.execute("UPDATE proposals SET args=? WHERE id=?", ('{"path":"reports/b.md"}', p["id"]))
    with pytest.raises(HTTPException) as e:
        execute(p["id"], p["capability"], "request-0001")
    assert e.value.status_code == 403


def test_cross_proposal_token():
    a = propose("notes.read", {"path": "reports/a.md"})
    b = propose("notes.read", {"path": "reports/b.md"})
    with pytest.raises(HTTPException):
        execute(b["id"], a["capability"], "request-0001")


def test_concurrent_retry_single_effect():
    p = propose("notes.write", {"path": "reports/a.md", "content": "once"})
    a = approve(p["id"])
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: execute(p["id"], a["capability"], "same-request"), range(2)))
    assert sorted(r["replayed"] for r in results) == [False, True]


def test_auth_separation(client):
    body = {"tool": "notes.write", "arguments": {"path": "reports/a.md", "content": "a"}}
    assert client.post("/api/proposals", json=body).status_code == 401
    p = client.post("/api/proposals", json=body, headers={"X-Agent-Key": "local-demo-agent"}).json()
    assert (
        client.post(
            "/api/proposals/" + p["id"] + "/approve", headers={"X-Agent-Key": "local-demo-agent"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/proposals/" + p["id"] + "/approve", headers={"X-Reviewer-Key": "local-demo-reviewer"}
        ).status_code
        == 200
    )


def test_denied_not_approvable():
    p = propose("shell", {})
    with pytest.raises(HTTPException):
        approve(p["id"])
