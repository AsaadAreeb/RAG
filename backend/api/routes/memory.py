from fastapi import APIRouter
from backend.services.memory_service import MemoryService

router = APIRouter()
_mem = MemoryService()


@router.get("/memory/{session_id}")
async def get_memory(session_id: str):
    history = await _mem.get_formatted(session_id)
    return {"session_id": session_id, "history": history}


@router.delete("/memory/{session_id}")
async def clear_memory(session_id: str):
    await _mem.clear(session_id)
    return {"message": f"Memory cleared for session {session_id}"}
