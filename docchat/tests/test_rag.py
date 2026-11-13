import json

from app import rag


def events(gen):
    return [json.loads(e[len("data: "):]) for e in gen]


def test_no_relevant_chunks_skips_llm(monkeypatch):
    monkeypatch.setattr(rag.store, "search", lambda q, k: [
        {"text": "unrelated", "source": "a.txt", "page": 0, "distance": 0.95}])
    monkeypatch.setattr(rag, "stream_llm", lambda *a, **k: (_ for _ in ()).throw(AssertionError("LLM must not be called")))
    out = events(rag.answer("what is the meaning of life?", []))
    assert out[0] == {"type": "sources", "data": []}
    assert out[1]["data"] == rag.NO_ANSWER


def test_short_followup_borrows_previous_question(monkeypatch):
    seen = {}
    monkeypatch.setattr(rag.store, "search", lambda q, k: seen.setdefault("q", q) and [])
    rag.retrieve("and the cost?", [{"role": "user", "content": "How does the pricing plan work?"}])
    assert "pricing plan" in seen["q"]
