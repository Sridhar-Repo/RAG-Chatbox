# Chat with your docs

Upload a few PDFs / text files and ask questions. Answers stream in, cite the passages they came from, and say "I don't know" when the documents don't cover the question.

> **Screenshots:** add yours in `docs/` and link them here.

## Quick setup

```bash
# 1. Install Ollama (https://ollama.com) and download a small open model
ollama pull llama3.2

# 2. Run the app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # open http://localhost:8000
pytest                          # tests
```

Docker: `docker build -t docchat . && docker run -p 8000:8000 -e LLM_BASE_URL=http://host.docker.internal:11434/v1 -v docchat-data:/data docchat` (Ollama keeps running on your machine; on Linux add `--add-host=host.docker.internal:host-gateway`).

No GPU or no Ollama? Use a free hosted model such as Groq's free tier by setting `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY` (see `.env.example`).

Try it with `sample_docs/remote_work_policy.md` ("How much is the home-office stipend?").

## Architecture

```
Browser (single HTML page)
   │  upload / chat (SSE stream)
   ▼
FastAPI ── ingest.py: extract text → chunk (~800 chars, 100 overlap)
   │
   ├── store.py: Chroma (local, persisted) + MiniLM embeddings
   │
   └── rag.py: retrieve top 5 → drop weak matches → prompt → open-source LLM via Ollama (streamed)
```

Four small modules, each doing one thing. The chat endpoint streams three kinds of events: `sources`, `token`, `done`, so the UI can show the passages while the answer is still being written.

## RAG / LLM decisions

| Piece | Chose | Also considered | Why |
|---|---|---|---|
| LLM | Llama 3.2 3B via Ollama (any OpenAI-compatible model via `LLM_MODEL` / `LLM_BASE_URL`) | Claude, GPT-4o, Qwen 2.5 7B, Groq free tier | Free, runs offline on a laptop, no API key. Smaller models follow instructions less reliably, so try `qwen2.5:7b` if answers drift |
| Embeddings | all-MiniLM-L6-v2, local (Chroma default, open source) | `nomic-embed-text` via Ollama, `bge-small`, paid APIs | Free, no key, fast on CPU. Weaker on long/technical text |
| Vector DB | Chroma, persisted to disk | pgvector, FAISS, Qdrant | Zero setup, metadata filtering, easy to delete one document |
| Orchestration | None — plain Python | LangChain, LlamaIndex | The pipeline is ~100 lines; a framework would hide the parts I want to explain |
| Chunking | Paragraph-aware, ~800 chars, 100 overlap | Fixed-size, semantic chunking | Paragraphs usually hold one idea; only split inside a paragraph if it's huge |

**Prompt and context:** system prompt says to use only the excerpts, cite as `[n]`, admit when unsure, and treat excerpt text as untrusted. Each excerpt is numbered and labelled with file and page. Last 6 turns of history are sent. Short follow-ups ("and the cost?") borrow the previous question for retrieval only.

**Guardrails:** relevance cut-off (`MAX_DISTANCE`) — if nothing is close enough we skip the LLM and say so; upload type and size limits; question length limit; prompt-injection instruction in the system prompt; errors from the model shown plainly instead of a blank screen.

**Quality:** unit tests for chunking, the "nothing relevant" path and follow-up retrieval. No automated answer-quality eval yet (see below).

**Observability:** one JSON log line per chat with hit count, best score, time-to-first-token, total time and token usage.

## Productionizing (AWS example; same shape on GCP/Azure)

- **Compute:** container on ECS Fargate (or Cloud Run / Container Apps), behind an ALB. App is stateless once storage moves out.
- **Storage:** raw files in S3; vectors in pgvector on RDS/Aurora (or OpenSearch / managed Qdrant) instead of local Chroma.
- **Ingestion:** move to async — upload to S3 → queue (SQS) → worker extracts, chunks, embeds. Required for big files and OCR.
- **Embeddings/LLM:** managed embedding endpoint; host the open model on a GPU service (vLLM on EKS/SageMaker) or use a managed model such as Bedrock, so traffic stays in the cloud account.
- **Auth and tenancy:** SSO/JWT, per-user or per-tenant document collections, filter every query by tenant id.
- **Security:** secrets in Secrets Manager, VPC endpoints, virus scan on upload, PII policy.
- **Observability:** logs to CloudWatch, traces and metrics via OpenTelemetry, dashboards for latency, cost per answer, "no answer" rate.
- **Scale and cost:** autoscale on CPU/requests, cache embeddings of repeated questions, rate limits per user.
- **CI/CD:** GitHub Actions → build, test, push image → deploy with infra as code (Terraform).

## Key technical decisions

1. **No framework.** Easier to read and debug in a small project.
2. **Refuse before calling the LLM** when retrieval is weak. Cheaper and avoids made-up answers.
3. **Free and local end to end.** Open-source LLM and embeddings, no API keys. Trade-off: lower answer quality than frontier models.
6. **OpenAI-compatible API, plain httpx.** Swapping Ollama for another free provider is a config change, not a code change.
4. **Stream sources first.** The user sees evidence immediately.
5. **Single HTML file, no build step.** The point is the RAG, not a front-end toolchain.

## Engineering standards

Followed: small modules, config via env vars, typed request models, tests for the logic that matters, Dockerfile, structured logs.
Skipped (on purpose, for time): auth, rate limiting, CI pipeline, OCR, integration tests with a real LLM, linting config.

Known gaps: scanned PDFs return "no text found"; tables in PDFs extract poorly; one shared collection for everyone; chat history lives in the browser only.