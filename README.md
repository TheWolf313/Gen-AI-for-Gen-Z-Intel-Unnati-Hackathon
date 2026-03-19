
````markdown
# AI-Powered Education Tutor for Remote India

An AI tutoring system for rural and remote learners that answers textbook-based questions using retrieval, filtering, and lightweight context pruning. The project is designed as a beginner-friendly hackathon MVP with a FastAPI backend, a minimal frontend, structured textbook data loading, caching, and curriculum-aware answers with citations.

The current implementation focuses on:
- low-cost answering through compact context selection
- textbook-grounded responses instead of open-ended guessing
- simple deployment and testing on a local machine
- beginner-friendly modular structure for future upgrades

---

## Current Features

This project currently includes the following implemented features:

- **FastAPI backend**
- **`/chat` endpoint** for asking textbook-grounded questions
- **`/health` endpoint** for quick backend health checking
- **Embedding-based retrieval** over structured textbook entries
- **Basic context pruning / token reduction reporting**
- **Caching** with `cache_hit` in response metadata
- **Grade-aware response formatting**
- **Intent-aware responses**
  - definition
  - process
  - inputs/outputs
  - explanation
  - factoid
- **Chapter and topic filtering**
- **Optional board and book metadata support**
- **Structured dataset loading from JSON**
- **Raw textbook ingestion script** for generating processed JSON
- **Minimal frontend demo UI**
- **Swagger API docs** for easy testing

---

## What the App Currently Does

A student enters a question such as:

- What is photosynthesis?
- How do plants make food?
- What is gravity?
- What are atoms?

The system then:

1. accepts the question through the API or frontend
2. normalizes and classifies the query
3. retrieves the most relevant textbook entries using embeddings
4. applies filters like grade, subject, chapter, and topic when available
5. compresses the selected evidence into a smaller answer context
6. generates a short, curriculum-style answer
7. returns citations and metadata such as confidence, token reduction, and cache status

---

## Project Structure

Below is the practical structure of the project as used in the current MVP.

```text
Gen-AI-for-Gen-Z-Intel-Unnati-Hackathon/
│
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI routes like /chat and /health
│   │   ├── data/                # Vector store and dataset loading logic
│   │   ├── ingestion/           # Raw textbook -> processed JSON pipeline
│   │   ├── llm/                 # Embedding provider / model utilities
│   │   ├── schemas/             # Request and response schemas
│   │   ├── services/            # Query pipeline, retrieval, pruning, formatting
│   │   └── main.py              # FastAPI app entry point
│   │
│   └── requirements.txt         # Python dependencies
│
├── data/
│   ├── raw/                     # Raw textbook input files
│   └── processed/               # Processed structured textbook JSON
│
├── frontend/
│   └── index.html               # Minimal static frontend demo
│
├── .gitignore
├── LICENSE
└── README.md
````

### Important folders and files

* **`backend/app/main.py`**
  Starts the FastAPI application and wires routes and middleware.

* **`backend/app/api/`**
  Contains API route handlers.

* **`backend/app/services/query_pipeline.py`**
  Main pipeline for intent detection, retrieval, pruning, formatting, and metadata generation.

* **`backend/app/data/vector_store.py`**
  Loads processed dataset entries, creates embeddings, and supports filtering/retrieval.

* **`backend/app/ingestion/textbook_ingestor.py`**
  Converts a raw textbook-style text file into structured JSON used by the app.

* **`data/raw/`**
  Stores raw textbook input used for ingestion.

* **`data/processed/demo_textbook.json`**
  Main processed dataset loaded by the backend.

* **`frontend/index.html`**
  Simple browser-based UI for testing the tutor.

---

## Requirements

Install the following before running the project:

* **Python 3.10 or higher** recommended
* **pip**
* **Git**
* Optional:

  * **VS Code**
  * **Cursor**

### Notes

* On first run, the local embedding model may download from Hugging Face.
* Internet may be required the first time for model download.
* Later runs will be faster once the model is cached locally.

---

## Setup From Scratch on a New Computer

This section explains how to run the project from zero on a fresh machine.

### 1. Clone the repository

```powershell
git clone https://github.com/TheWolf313/Gen-AI-for-Gen-Z-Intel-Unnati-Hackathon
cd Gen-AI-for-Gen-Z-Intel-Unnati-Hackathon
```

Replace `<your-repo-url>` with your actual GitHub repository URL.

---

### 2. Create a virtual environment

Using a virtual environment is strongly recommended.

```powershell
python -m venv .venv
```

---

### 3. Activate the virtual environment

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

You should then see `(.venv)` at the start of the terminal line.

---

### 4. Install dependencies

From the project root:

```powershell
pip install -r backend\requirements.txt
```

If your repo uses a root-level `requirements.txt`, then use that instead. For the current project structure, `backend\requirements.txt` is the safer documented path.

---

## How to Run the Backend

### Important

The backend should be started **from inside the `backend` folder**.

If you run it from the wrong folder, Python import paths may fail and you may get errors like:

* `No module named 'app'`
* import errors from `app.services...`

### Correct backend startup

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

### Expected result

You should see something like:

```text
Uvicorn running on http://127.0.0.1:8000
```

### Useful backend URLs

* **Backend server**
  `http://127.0.0.1:8000`

* **Swagger docs**
  `http://127.0.0.1:8000/docs`

* **OpenAPI JSON**
  `http://127.0.0.1:8000/openapi.json`

* **Health check**
  `http://127.0.0.1:8000/health`

---

## How to Run the Frontend

The frontend is a minimal static HTML page.

### Recommended method

Open a **new terminal** from the project root and run:

```powershell
python -m http.server 5500
```

Then open this in your browser:

```text
http://127.0.0.1:5500/frontend/index.html
```

### Important note

If you open only:

```text
http://127.0.0.1:5500
```

you will just see a folder listing. That is normal. Open:

```text
http://127.0.0.1:5500/frontend/index.html
```

instead.

### Backend requirement

The backend must already be running on `http://127.0.0.1:8000` before the frontend can successfully send requests.

---

## How to Run the Ingestion Script

The ingestion script converts a raw textbook-like text file into structured JSON used by the tutor.

### Raw file location

```text
data/raw/demo_textbook.txt
```

### Processed output location

```text
data/processed/demo_textbook.json
```

### Run ingestion

From inside the `backend` folder:

```powershell
python -m app.ingestion.textbook_ingestor
```

### Expected result

* processed JSON file is created or updated
* console should print how many entries were parsed
* backend can then load the processed dataset automatically on startup

---

## How to Test the App

You can test the project in two ways:

1. **Swagger UI**
2. **Frontend UI**

---

## Testing Through Swagger UI

Open:

```text
http://127.0.0.1:8000/docs
```

Then:

1. Find the `POST /chat` endpoint
2. Click **Try it out**
3. Paste a test JSON request
4. Click **Execute**

### Sample test JSON 1

```json
{
  "question": "What is photosynthesis?",
  "grade": "9",
  "subject": "Science",
  "language": "en"
}
```

### Sample test JSON 2

```json
{
  "question": "How do plants make food?",
  "grade": "9",
  "subject": "Science",
  "chapter": "Plant Biology",
  "topic": "Photosynthesis",
  "language": "en"
}
```

### Sample test JSON 3

```json
{
  "question": "What is gravity?",
  "grade": "9",
  "subject": "Science",
  "chapter": "Physics Basics",
  "topic": "Gravity",
  "language": "en"
}
```

### Sample test JSON 4

```json
{
  "question": "What are atoms?",
  "grade": "9",
  "subject": "Science",
  "chapter": "Chemistry Basics",
  "topic": "Atoms and Molecules",
  "language": "en"
}
```

### Sample test JSON 5

```json
{
  "question": "What is quantum tunneling?",
  "grade": "9",
  "subject": "Science",
  "language": "en"
}
```

### Expected response style

You should get:

* a short answer
* citations
* metadata such as confidence
* token usage information
* cache hit status

---

## Testing Through the Frontend

1. Make sure backend is running
2. Make sure frontend server is running
3. Open:

```text
http://127.0.0.1:5500/frontend/index.html
```

4. Fill in:

   * question
   * grade
   * subject
   * optional chapter
   * optional topic

5. Click **Ask**

Expected result:

* answer appears on screen
* citations are shown
* confidence and token reduction are displayed
* repeated identical queries may return `cache_hit: true`

---

## Example API Request

### Request

```json
{
  "question": "What is photosynthesis?",
  "grade": "9",
  "subject": "Science",
  "language": "en"
}
```

### Example response

```json
{
  "answer": "Photosynthesis is how green plants make food using sunlight, carbon dioxide, and water.",
  "citations": [
    {
      "source": "demo-textbook",
      "chapter": "Plant Biology",
      "page": 12
    }
  ],
  "meta": {
    "grade": "9",
    "subject": "Science",
    "confidence": "medium",
    "intent": "definition",
    "token_usage": {
      "before": 64,
      "after": 21,
      "reduction_percent": 67
    },
    "cache_hit": false
  }
}
```

---

## API Endpoints

### `GET /health`

Used to verify that the backend is running.

Typical response:

```json
{
  "status": "ok"
}
```

### `POST /chat`

Main endpoint for asking questions.

Input:

* question
* grade
* subject
* language
* optional chapter
* optional topic
* optional board
* optional book_id

Output:

* answer
* citations
* meta

---

## How the System Works Internally

The current MVP pipeline works like this:

1. User sends a question
2. Query is normalized
3. Intent is detected using lightweight rules
4. Dataset is filtered using grade, subject, chapter, topic, and optional metadata
5. Relevant entries are embedded and compared
6. Top matching textbook entries are selected
7. Context is compressed into a short answer form
8. Final answer is shaped based on intent and grade
9. Citations are deduplicated
10. Metadata is added
11. Response is cached for repeated requests

---

## Troubleshooting

This section covers real problems that occurred during development.

### 1. `uvicorn` is not recognized

Error example:

```text
uvicorn : The term 'uvicorn' is not recognized...
```

### Fix

Use:

```powershell
python -m uvicorn app.main:app --reload
```

instead of just:

```powershell
uvicorn app.main:app --reload
```

---

### 2. `No module named 'app'`

This usually happens when you run the backend from the wrong directory.

### Fix

Run backend from inside the `backend` folder:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

---

### 3. Frontend says `Failed to fetch`

Possible reasons:

* backend is not running
* wrong frontend URL was opened
* CORS was not configured properly
* browser is calling the wrong backend URL

### Fix checklist

* confirm backend is running at `http://127.0.0.1:8000`
* confirm docs open at `http://127.0.0.1:8000/docs`
* confirm frontend is opened at
  `http://127.0.0.1:5500/frontend/index.html`
* confirm CORS is enabled in `main.py`

---

### 4. Opening `127.0.0.1:5500` shows only a file listing

That is expected when serving from the project root.

### Fix

Open:

```text
http://127.0.0.1:5500/frontend/index.html
```

---

### 5. First startup downloads the embedding model

This is normal. The project uses a local sentence-transformer model when an external embedding API is not configured.

The first run may take longer.

---

### 6. `/chat` says `Method Not Allowed`

This happens if you open `/chat` directly in the browser using GET.

### Fix

`/chat` is a **POST-only** endpoint. Use:

* Swagger UI
* frontend
* Postman
* curl
* any API client

---

### 7. Backend starts but import errors appear

Most common cause:

* incorrect working directory
* partially changed imports
* inconsistent local edits

### Fix

* activate virtual environment
* ensure dependencies are installed
* run backend from `backend/`
* check that imports use the `app.` package path consistently

---

## Current Limitations

This is still an MVP / hackathon-style system. Current limitations include:

* textbook dataset is still demo-scale
* full PDF ingestion pipeline is not finalized
* no production database/authentication layer
* retrieval and pruning are MVP quality, not production-grade
* response generation is template/rule-driven rather than full LLM tutoring
* Hindi is not finalized as a stable response path
  for now, unsupported languages fall back safely to English
* frontend is minimal and built only for demo/testing

---

## Planned / Future Improvements

These are good next steps for future development:

* full PDF textbook ingestion
* stronger chapter/topic extraction
* multi-book and multi-board expansion
* better context pruning pipeline
* multilingual response support
* richer frontend experience
* better confidence calibration
* persistent database and storage
* proper analytics and teacher/student dashboards
* real LLM-backed answer generation where needed

---

## Tech Stack

* **Python**
* **FastAPI**
* **Uvicorn**
* **sentence-transformers**
* **HTML / CSS / JavaScript**
* Optional future direction:

  * FAISS / Chroma
  * SQLite / PostgreSQL
  * hosted LLM APIs

---

## Environment Configuration

If your project uses environment variables later, create a local `.env` file and never commit secrets.

Possible future variables:

* `LLM_PROVIDER`
* `LLM_MODEL_PRIMARY`
* `LLM_MODEL_CHEAP`
* `EMBEDDINGS_PROVIDER`
* `EMBEDDINGS_MODEL`
* `VECTOR_STORE_PATH`
* `DATABASE_URL`

At the current MVP stage, local embeddings are sufficient for running the app.

---

## Contribution / Notes

This project was built in a hackathon / MVP style with simplicity and modularity in mind. The code is intentionally structured so a beginner team can understand the flow and gradually replace mock or simplified parts with more production-ready components.

The main goal of the project is not to be a full production tutoring platform yet. The current goal is to demonstrate a working, retrieval-based, low-cost educational assistant that can grow into a larger system.

---

## Quick Start Summary

If you just want the shortest working path:

### Terminal 1: backend

```powershell
cd Gen-AI-for-Gen-Z-Intel-Unnati-Hackathon\backend
python -m uvicorn app.main:app --reload
```

### Terminal 2: frontend

```powershell
cd Gen-AI-for-Gen-Z-Intel-Unnati-Hackathon
python -m http.server 5500
```

### Browser

Open:

```text
http://127.0.0.1:5500/frontend/index.html
```

### Swagger Docs

Open:

```text
http://127.0.0.1:8000/docs
```

---

```

