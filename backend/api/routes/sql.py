from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.pipelines.sql_pipeline import SQLPipeline

router = APIRouter()
_pipeline = SQLPipeline()


class SQLGenerateRequest(BaseModel):
    query: str
    session_id: str = "default"


class SQLApproveRequest(BaseModel):
    pending_id: str


@router.post("/sql/generate")
async def sql_generate(req: SQLGenerateRequest):
    """Generate SQL from a NL question (awaits human approval)."""
    return await _pipeline.run(
        query=req.query,
        history=[],
        require_approval=True,
        session_id=req.session_id,
    )


@router.post("/sql/approve")
async def sql_approve(req: SQLApproveRequest):
    """Execute the approved pending SQL query."""
    result = await _pipeline.approve_and_execute(req.pending_id)
    if result.get("status") == "error":
        raise HTTPException(400, result.get("error"))
    return result