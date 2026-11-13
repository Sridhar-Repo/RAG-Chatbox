"""Thin wrapper around Chroma so the rest of the app doesn't care about it."""
import chromadb

from .config import settings

_collection = None


def collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=settings.data_dir)
        _collection = client.get_or_create_collection("docs", metadata={"hnsw:space": "cosine"})
    return _collection


def add_document(filename: str, chunks: list[dict]) -> int:
    delete_document(filename)
    if not chunks:
        return 0
    collection().add(
        ids=[f"{filename}::{i}" for i in range(len(chunks))],
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "page": c["page"]} for c in chunks],
    )
    return len(chunks)


def delete_document(filename: str) -> None:
    collection().delete(where={"source": filename})


def list_documents() -> list[dict]:
    metas = collection().get(include=["metadatas"])["metadatas"]
    counts: dict[str, int] = {}
    for m in metas:
        counts[m["source"]] = counts.get(m["source"], 0) + 1
    return [{"name": n, "chunks": c} for n, c in sorted(counts.items())]


def search(question: str, k: int) -> list[dict]:
    col = collection()
    if col.count() == 0:
        return []
    res = col.query(query_texts=[question], n_results=min(k, col.count()))
    return [
        {"text": t, "source": m["source"], "page": m["page"], "distance": d}
        for t, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]
