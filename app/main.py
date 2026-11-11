import os
import secrets

from fastapi import Depends, Header, HTTPException
from pydantic import Field

from app.control import approve, execute, proposals, propose
from app.platform import StrictModel, audit, make_app, mount_ui

app = make_app("Agent Permit")


def agent_auth(x_agent_key: str = Header(default="")):
    if not secrets.compare_digest(x_agent_key, os.getenv("AGENT_API_KEY", "local-demo-agent")):
        raise HTTPException(401, "Invalid agent key")


def reviewer_auth(x_reviewer_key: str = Header(default="")):
    if not secrets.compare_digest(x_reviewer_key, os.getenv("REVIEWER_API_KEY", "local-demo-reviewer")):
        raise HTTPException(401, "Independent reviewer key required")


class Proposal(StrictModel):
    tool: str = Field(min_length=1, max_length=80)
    arguments: dict


class Execution(StrictModel):
    capability: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=100)


@app.post("/api/proposals", dependencies=[Depends(agent_auth)])
def proposal(body: Proposal):
    result = propose(body.tool, body.arguments)
    audit("proposal", {"id": result["id"], "state": result["state"], "digest": result["argument_digest"]})
    return result


@app.get("/api/proposals", dependencies=[Depends(reviewer_auth)])
def listing():
    return {"proposals": proposals()}


@app.post("/api/proposals/{identifier}/approve", dependencies=[Depends(reviewer_auth)])
def approval(identifier: str):
    result = approve(identifier)
    audit("approval", {"id": identifier})
    return result


@app.post("/api/proposals/{identifier}/execute", dependencies=[Depends(agent_auth)])
def execution(identifier: str, body: Execution):
    result = execute(identifier, body.capability, body.idempotency_key)
    audit("execution", {"id": identifier, "replayed": result["replayed"]})
    return result


mount_ui(app)
