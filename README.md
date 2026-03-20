# Enterprise RAG System

A local, privacy-first question-answering system that works across two data sources — PDF documents and SQL databases — through a single chat interface.

Upload a PDF, ask a question, get an answer with the exact source passages it came from. Connect a database, ask in plain English, get SQL generated and executed with your approval. Everything runs on your machine.

---

## What It Does

**Document Q&A**
- Upload any PDF through the UI
- Ask questions in plain English
- Get answers grounded in the actual document text
- See exactly which passages were used, with relevance scores
- Confidence score on every response

**Database Q&A**
- Connect any SQLite database
- Ask natural language questions about your data
- System generates the SQL and shows it to you before running anything
- Results returned as a natural sentence or a formatted table depending on what makes sense

**One chat interface for both.** The system decides which pipeline to use based on what you ask.

---

## How It Works

```
Your Question
     │
     ▼
┌─────────────┐
│ Query Router │  ──── decides: PDF pipeline or SQL pipeline
└─────────────┘
     │                          │
     ▼                          ▼
┌──────────────────┐    ┌──────────────────┐
│   PDF Pipeline   │    │   SQL Pipeline   │
│                  │    │                  │
│ 1. Dense search  │    │ 1. Read schema   │
│    (embeddings)  │    │ 2. Generate SQL  │
│ 2. BM25 search   │    │ 3. Validate SQL  │
│ 3. Hybrid merge  │    │ 4. Show you SQL  │
│ 4. Reranker      │    │ 5. You approve   │
│ 5. LLM answer    │    │ 6. Execute       │
│ 6. Guardrails    │    │ 7. Naturalize    │
└──────────────────┘    └──────────────────┘
     │                          │
     └──────────┬───────────────┘
                ▼
         Answer + Sources
```

---

## Guardrails

Security and reliability are built into every layer.

| Layer | What it catches |
|---|---|
| Input guardrail | Prompt injections, jailbreaks, out-of-scope requests |
| Output guardrail | Ungrounded answers, low-confidence responses, harmful content |
| SQL guardrail | Only SELECT allowed — no DELETE / DROP / UPDATE / INSERT ever runs |
| SQL approval gate | No query runs without you seeing and approving it first |
| Confidence scoring | Every PDF answer includes a grounding confidence score |
| LLM fallback | Primary model rate-limited? Automatically switches to backup model |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, Tailwind CSS, TypeScript |
| Backend | FastAPI, Python 3.10+ |
| Vector store | ChromaDB (persistent, local) |
| Embeddings | `BAAI/bge-small-en-v1.5` (runs locally) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` (runs locally) |
| Memory | Redis |
| Database | SQLite via SQLAlchemy + aiosqlite |
| Primary LLM | Grok (xAI) |
| Fallback LLM | Gemini (Google) |
| Container | Docker |

---

## Project Structure

```
.
├── backend/
│   ├── api/
│   │   └── routes/          # FastAPI route handlers
│   ├── core/
│   │   ├── config.py        # Settings from .env
│   │   ├── orchestrator.py  # Routes query to correct pipeline
│   │   └── query_router.py  # PDF vs SQL decision logic
│   ├── guardrails/
│   │   ├── input_guardrails.py
│   │   ├── output_guardrails.py
│   │   └── sql_guardrails.py
│   ├── pipelines/
│   │   ├── rag_pipeline.py
│   │   └── sql_pipeline.py
│   └── services/
│       ├── llm_service.py   # Grok + Gemini with fallback
│       ├── memory_service.py
│       └── rate_limiter.py
├── ingestion/
│   └── pdf_ingestor.py      # PDF → chunks → embeddings
├── vectorstore/
│   └── chroma_store.py      # ChromaDB wrapper + BM25
├── sql/
│   ├── schema_inspector.py  # Reads live DB schema
│   └── query_executor.py    # Executes approved SQL
├── ui/                      # Next.js frontend
│   └── src/
│       ├── app/
│       └── components/
│           ├── ChatInterface.tsx
│           ├── EvidencePanel.tsx
│           ├── SQLPanel.tsx
│           ├── AdminPanel.tsx
│           └── MessageContent.tsx
├── storage/
│   ├── uploads/             # PDFs go here
│   ├── chroma/              # Vector index (auto-created)
│   └── your_database.sqlite
├── .env.example
├── requirements.txt
└── docker-compose.yml
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker (for Redis)
- An xAI API key → [console.x.ai](https://console.x.ai)
- A Google Gemini API key → [aistudio.google.com](https://aistudio.google.com)

### 1. Clone the repo

```bash
git clone
cd RAG
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

```bash
XAI_API_KEY=your_xai_key_here
GEMINI_API_KEY=your_gemini_key_here

GROK_MODEL=grok-3
GEMINI_MODEL=gemini-2.5-flash

REDIS_URL=redis://localhost:6379/0
CHROMA_PATH=./storage/chroma
CHROMA_COLLECTION=rag_documents

# Windows — use 4 slashes for absolute path:
# DATABASE_URL=sqlite+aiosqlite:////C:/full/path/to/your.sqlite
# Mac/Linux:
DATABASE_URL=sqlite+aiosqlite:///./storage/app.db

EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

CHUNK_SIZE=600
CHUNK_OVERLAP=100
TOP_K=5
UPLOAD_DIR=./storage/uploads
ANONYMIZED_TELEMETRY=False
```

### 3. Start Redis

```bash
docker run -d --name redis-rag --restart always -p 6379:6379 redis:7-alpine
```

### 4. Run the backend

```bash
# Create and activate virtual environment
python -m venv rag
source rag/bin/activate        # Mac/Linux
rag\Scripts\activate           # Windows

pip install -r requirements.txt

# Create storage folders
mkdir -p storage/uploads storage/chroma

# Start backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend is ready when you see:
```
INFO: Application startup complete.
```

Verify: `curl http://localhost:8000/health` → `{"status":"ok"}`

### 5. Run the frontend

```bash
cd ui
npm install
npm run dev
```

Open **http://localhost:3000**

---

## Using a Sample Database

The [Chinook database](https://github.com/lerocha/chinook-database) is a good starting point — it's a music store with artists, albums, tracks, customers and invoices.

```bash
# Download the SQLite version
curl -L https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite \
     -o storage/Chinook_Sqlite.sqlite
```

Update `.env`:
```bash
DATABASE_URL=sqlite+aiosqlite:////full/path/to/storage/Chinook_Sqlite.sqlite
```

Then try:
```
How many artists are there?
List the top 10 customers by total spending.
Which genre has generated the most revenue?
```

---

## Using Sample PDFs

Any PDF works. Good free sources:

- **arXiv** — `arxiv.org` — research papers
- **OpenStax** — `openstax.org` — free textbooks
- **Project Gutenberg** — `gutenberg.org` — public domain books
- **SEC EDGAR** — `sec.gov/edgar` — company filings

---

## Example Queries

**PDF questions**
```
What are the main conclusions of this paper?
Summarize section 3 in simple terms.
Does this document mention anything about performance benchmarks?
```

**Database questions**
```
How many customers are in the database?
Which artist has the most tracks?
Show me total revenue broken down by country.
List all tracks that have never been purchased.
```

**Multi-turn conversation**
```
You:  Who are the top 5 customers by spending?
You:  Which of them is from Brazil?
You:  How many invoices does that customer have?
```
The system remembers context across the conversation.

---

## Extending This

Some directions to take it further:

- **More file types** — add DOCX, CSV, or web page ingestion to `ingestion/`
- **Better routing** — replace regex router with an LLM classifier for ambiguous queries
- **Streaming** — the `/query` endpoint already supports SSE streaming, wire it up in the UI
- **Authentication** — add JWT auth to the FastAPI routes
- **Cloud deployment** — containerize with Docker Compose and deploy to any VPS or cloud provider
- **Larger models** — swap `bge-small` for `bge-large` or any HuggingFace embedding model
- **Multiple databases** — extend `SchemaInspector` to handle PostgreSQL or MySQL

---

## Environment Variables Reference

| Variable | Description | Default |
|---|---|---|
| `XAI_API_KEY` | xAI (Grok) API key | required |
| `GEMINI_API_KEY` | Google Gemini API key | required |
| `GROK_MODEL` | Grok model name | `grok-3` |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.5-flash` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `DATABASE_URL` | SQLAlchemy async DB URL | required |
| `CHROMA_PATH` | ChromaDB storage folder | `./storage/chroma` |
| `EMBEDDING_MODEL` | HuggingFace embedding model | `BAAI/bge-small-en-v1.5` |
| `RERANKER_MODEL` | HuggingFace reranker model | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `CHUNK_SIZE` | PDF chunk size in tokens | `600` |
| `CHUNK_OVERLAP` | Overlap between chunks | `100` |
| `TOP_K` | Chunks used in final answer | `5` |
| `UPLOAD_DIR` | Where uploaded PDFs are stored | `./storage/uploads` |
| `RATE_LIMIT_RPM` | Provider requests per minute | `20` |

---

## License

MIT — use it, modify it, build on it.

---
