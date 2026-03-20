from fastapi import APIRouter
from vectorstore.chroma_store import ChromaStore

router = APIRouter()
_store = ChromaStore()


@router.get("/admin/stats")
def stats():
    return {"total_chunks": _store.count()}


@router.delete("/admin/document/{doc_id}")
def delete_document(doc_id: str):
    _store.delete_document(doc_id)
    return {"message": f"Document {doc_id} deleted"}