import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ingest, rag, store
from .config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
app = FastAPI(title="Chat with your docs")


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[Turn] = []


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/docs")
def docs():
    return store.list_documents()


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    name = file.filename or ""
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in settings.allowed_ext:
        raise HTTPException(400, "Only PDF, TXT and MD files are supported.")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB.")
    try:
        chunks = ingest.build_chunks(name, data)
    except Exception:
        raise HTTPException(400, "Couldn't read that file. Is it corrupted or password-protected?")
    if not chunks:
        raise HTTPException(400, "No text found. Scanned PDFs need OCR first.")
    return {"name": name, "chunks": store.add_document(name, chunks)}


@app.delete("/api/docs/{name}")
def remove(name: str):
    store.delete_document(name)
    return {"ok": True}


@app.post("/api/chat")
def chat(req: ChatRequest):
    q = req.question.strip()
    if not q:
        raise HTTPException(400, "Ask a question first.")
    if len(q) > settings.max_question_chars:
        raise HTTPException(400, f"Keep questions under {settings.max_question_chars} characters.")
    history = [t.model_dump() for t in req.history]
    return StreamingResponse(rag.answer(q, history), media_type="text/event-stream")


app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def index():
    return FileResponse("app/static/index.html")
