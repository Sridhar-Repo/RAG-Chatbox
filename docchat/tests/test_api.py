from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def test_health():
    assert c.get("/health").json() == {"ok": True}


def test_rejects_bad_extension():
    r = c.post("/api/upload", files={"file": ("virus.exe", b"x")})
    assert r.status_code == 400


def test_rejects_empty_question():
    assert c.post("/api/chat", json={"question": "  "}).status_code == 400
