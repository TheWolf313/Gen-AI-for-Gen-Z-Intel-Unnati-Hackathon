# AI-Powered Education Tutor for Remote India

An AI tutoring system for rural/remote learners that ingests large state-board textbooks and provides **personalized, curriculum-aligned answers** using **context pruning** to minimize token usage, API cost, and data transfer—built for **low-bandwidth environments** by a small beginner-friendly team.

---

## Core goals

- **Beginner-friendly**: clear modules, minimal moving parts, strong defaults.
- **Modular + scalable**: ingestion/preprocessing separated from serving.
- **Cost-efficient**: tight retrieval + pruning + caching.
- **Low-bandwidth first**: small payloads, offline-friendly patterns.

---

## Step 1: Core features (purpose → how → why)

### Textbook ingestion system
- **Purpose**: Bring official textbooks (PDF/EPUB/Scans) into the system reliably.
- **How it works**: Upload or batch-import files → store raw files → run an asynchronous pipeline that extracts text + structure + metadata → persist outputs.
- **Why it is important**: Everything downstream (retrieval, pruning, alignment) depends on clean, stable source data; ingestion must be repeatable and auditable.

### Structured content extraction (chapters, topics, examples)
- **Purpose**: Convert books into a navigable curriculum structure (Board → Grade → Subject → Chapter → Topic → Example/Exercise).
- **How it works**:
  - Parse table-of-contents when available.
  - Detect headings and boundaries (layout-aware extraction + heuristics).
  - Tag blocks (definition/example/theorem/exercise/solution) using rules + light classification.
  - Store a “content tree” with stable IDs and references back to original page ranges.
- **Why it is important**: Structure enables precise retrieval and better pruning than raw text chunking.

### Context pruning mechanism
- **Purpose**: Send only the minimum sufficient context to the LLM.
- **How it works**:
  - Identify likely chapters/topics using a fast retrieval pass.
  - Re-rank and filter to a small set of best sections.
  - Compress sections into short bullet summaries + include only essential quotes.
  - Enforce a strict token budget with a fallback (short answer + clarifying question).
- **Why it is important**: LLM cost and latency scale with tokens; pruning is the main lever for affordability and low bandwidth.

### Query processing pipeline
- **Purpose**: Turn a user question into a structured, curriculum-aware request.
- **How it works**:
  - Language detection (Hindi/English/mixed) and normalization.
  - Intent detection (definition, derivation, solve example, MCQ, etc.).
  - Map to grade/subject/chapter from user profile + retrieval + lightweight classification.
  - Choose response mode: short / step-by-step / exam-focused / practice.
- **Why it is important**: Good routing reduces retrieval mistakes and prevents unnecessary context from being sent to the LLM.

### Personalized response generation
- **Purpose**: Adapt explanations to grade, language preference, and learning level.
- **How it works**:
  - Maintain a small user profile: grade/board/subjects, language, difficulty, past misconceptions.
  - Use profile + intent to control style (“very simple”, “step-by-step”, “exam points”).
  - Ground answers in retrieved content and return citations (chapter/topic/page).
- **Why it is important**: Personalization improves learning outcomes and trust, especially with mixed language and uneven foundations.

### Offline/low-bandwidth optimization (caching + lightweight responses)
- **Purpose**: Work well with unstable connectivity and low-end devices.
- **How it works**:
  - Cache on server: frequent questions, embeddings, pruned contexts, final answers.
  - Cache on device: recent answers, chapter summaries, “study cards”.
  - Response shaping: default to concise answers + an “expand” option; small JSON payloads.
- **Why it is important**: Reduces data transfer, improves latency, and keeps the product usable in remote areas.

### Cost optimization strategies
- **Purpose**: Keep the system affordable at scale.
- **How it works**:
  - Two-stage retrieval (cheap embeddings → small re-rank).
  - Strict token budgets and compression.
  - Aggressive caching (query→answer, query→context, chapter summaries).
  - Model routing: smallest viable model for the task; escalate only when needed.
  - Batch ingestion + offline preprocessing to avoid runtime costs.
- **Why it is important**: Textbook-scale RAG gets expensive quickly without deliberate cost controls.

---

## Step 2: System architecture

### Frontend (user interaction layer)
- **Responsibilities**:
  - Chat UI (Hindi/English), “short vs detailed” toggle, offline view.
  - Shows citations (chapter/topic/page) and “expand/explain more”.
  - Local caching of recent answers and downloaded summaries (optional).

### Backend (API + processing logic)
- **Responsibilities**:
  - User profiles and basic auth (minimal in MVP).
  - Query pipeline: normalize → retrieve → prune → generate.
  - Caching, rate limiting, basic metrics.
  - Async job management for ingestion (queue/worker).

### Data layer (vector DB + structured storage)
- **Structured storage (SQLite for MVP, Postgres later)**:
  - Books, chapters, topics, content blocks, page ranges, metadata.
  - User profiles and conversation summaries.
- **Vector store (FAISS/Chroma)**:
  - Embeddings for content blocks (and optionally chapter summaries).

### LLM integration layer
- **Responsibilities**:
  - Unified interface for embeddings + chat models.
  - Model routing (cheap vs better), retries, timeouts.
  - Prompt templates for answering, summarization, compression, translation.

### Preprocessing pipeline (PDF → structured data)
- **Responsibilities**:
  - Text extraction (layout-aware).
  - Structure extraction (TOC/headings) + block typing.
  - Chunking + embedding generation.
  - Index build (vector + metadata) and quality checks.

---

## Data flow (query → response)

1. User asks a question (optionally picks subject/chapter).
2. Backend normalizes query (language, intent, difficulty).
3. Retrieval stage 1: embedding search returns top blocks (within board/grade/subject).
4. Chapter/topic narrowing: aggregate scores; keep top candidate chapters/topics.
5. Retrieval stage 2: re-rank within candidates (type-aware + optional light cross-encoder).
6. Context pruning: select minimal blocks; compress into a tight “study context”; enforce token budget.
7. LLM generation: answer in requested style + language, grounded with citations.
8. Cache: store answer and pruned context; update user memory summary.
9. Frontend: show short answer first; expand on demand; show citations and practice prompts.

---

## Step 3: Production-grade (beginner-friendly) folder structure

This repo currently contains only a minimal `README.md`. Use the following layout as the target structure.

```text
/project-root
  /backend
    /app
      /api              # FastAPI routes: chat, ingest, books, users
      /core             # settings, logging, dependency injection
      /services         # query pipeline: retrieval, pruning, generation
      /ingestion        # PDF parsing, structure extraction, chunking, embeddings
      /llm              # providers, prompt templates, model routing
      /data             # SQL models, repositories, migrations, vector adapters
      /schemas          # request/response validation models
      /utils            # text normalization, language tools, hashing
    /tests
    pyproject.toml (or requirements.txt)

  /frontend
    /src
      /components
      /pages
      /services         # API client, cache, connectivity detection
      /styles
    package.json

  /data
    /raw                # original PDFs (gitignored)
    /processed          # extracted structured JSON/text (gitignored)
    /indexes            # persisted vector indexes (gitignored)
    /cache              # cache snapshots (gitignored)

  /docs
    architecture.md
    ingestion.md
    pruning.md
    api.md

  /config
    example.env         # environment template (no secrets)

  docker-compose.yml    # optional
  .gitignore
  LICENSE
  README.md
```

### What goes where (and why)
- **`backend/app/ingestion/`**: heavy preprocessing stays out of request-time code; can become a worker service later.
- **`backend/app/services/`**: pipeline brain is modular and testable (retrieve → prune → answer).
- **`backend/app/data/`**: storage boundary (SQL + vector) stays clean and swappable.
- **`frontend/`**: UI can evolve independently (web now, mobile later).
- **`data/`**: big artifacts live outside git; predictable paths help ops and low-bandwidth sync.
- **`docs/`**: reduces confusion for beginner teams; decisions are written down.
- **`config/`**: a single obvious place for environment templates.

---

## Step 4: Context pruning design (detailed)

### 1) Remove irrelevant chapters early
- **Hard filters**: board/grade/subject from user profile (and chapter selection if provided).
- **Chapter narrowing**:
  - Maintain short **chapter summaries** (embedded) to quickly identify likely chapters.
  - Run retrieval over chapter summaries first → keep top \(K\) chapters.
- **Why**: prevents the system from considering huge irrelevant text regions.

### 2) Select relevant sections precisely
- Store “blocks” with types (definition/example/exercise/derivation).
- Retrieve top \(N\) blocks within the candidate chapters.
- Re-rank with intent and type awareness:
  - “solve” → examples/solutions
  - “define” → definition blocks
  - “derivation” → derivation/theory blocks
- Optional: small cross-encoder re-rank for top 30–50 candidates.

### 3) Compress content before LLM
Use three tiers, always preferring the smallest:
- **Tier A (default)**: bullet “key points” summary (definitions, formulas, steps).
- **Tier B**: key points + a few short verbatim quotes (for exact definitions/formulas).
- **Tier C (rare)**: small original snippets (only when necessary).

Compression is ideally precomputed during ingestion (and cached if computed on-demand).

### 4) Enforce token budgets
- Hard cap: e.g., 800–1200 context tokens (tunable).
- Greedy packing: add best blocks until budget; then replace with Tier A summaries.
- Fail-safe: if confidence is low, answer briefly and ask **one** clarifying question.

### 5) Extra token minimization
- Summarize chat history into “student memory”; don’t send full conversation.
- Deduplicate repeated lines across blocks.
- Avoid bilingual duplication unless requested.

---

## Step 5: Tech stack (simple + realistic)

- **Backend**: Python + **FastAPI** (simple APIs, typing, docs).
- **Frontend**: **React + Vite** (fast setup) or minimal HTML for the MVP.
- **Vector DB**: **FAISS** (local, cheap) or **Chroma** (metadata + persistence).
- **Embeddings**: open-source sentence embeddings (low cost, can run offline during ingestion); OpenAI embeddings optional.
- **LLM**: low-cost hosted model for generation + cheaper model for summarization/compression; route by task.

Why these choices:
- Minimal infrastructure burden for a 3-person beginner team.
- Strong cost control levers (retrieval quality + pruning + caching + routing).
- Works in low-bandwidth settings by sending small contexts and short responses.

---

## Step 6: Hackathon MVP plan

### Day 1–2: Basic ingestion + simple Q&A
- Ingest 1 textbook (PDF → text blocks).
- Store blocks with chapter/page metadata.
- Basic chat API: retrieve top blocks and call LLM with citations.
- Minimal UI: chat + citations.

### Day 3–4: Retrieval + pruning (core innovation)
- Add structured extraction (chapters/topics).
- Add vector index with metadata filtering.
- Implement pruning: chapter narrowing → block rerank → compression tiers → token budget.
- Add caching: query→answer and chapter/topic summaries.

### Day 5+: Optimization + UI
- Low-bandwidth UX: short answer first, “expand” button, downloads for summaries.
- Cost controls: model routing, chat summarization, better caching.
- Basic metrics: latency, token usage, cache hit rate.

---

## Environment configuration (template)

Create a local `.env` from `config/example.env` (never commit secrets). Suggested variables:
- `LLM_PROVIDER`, `LLM_MODEL_PRIMARY`, `LLM_MODEL_CHEAP`
- `EMBEDDINGS_PROVIDER`, `EMBEDDINGS_MODEL`
- `VECTOR_STORE_PATH`
- `DATABASE_URL`
