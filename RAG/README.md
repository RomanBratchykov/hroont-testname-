# Kherson Agricultural Crop Rotation Dashboard — Backend

Backend API and hybrid SQL + Vector RAG ingestion pipeline built for the **NASA Space Apps Challenge**. The system supports agricultural crop rotation planning for the **Kherson region** by combining structured historical trial/yield datasets in **PostgreSQL** with unstructured agronomic guidelines, farmer interviews, and scientific literature in **Qdrant**, powered by a local **DeepSeek** model.

---

## Architecture & Tech Stack

- **API Framework:** Python 3.11+, FastAPI, Uvicorn
- **Relational Database:** PostgreSQL 15 (`sqlalchemy`, `psycopg2-binary`, `pandas`, `openpyxl`) for historical crop yields, soil parameters, management logs, and nutrient data
- **Vector Database (RAG):** Qdrant (`qdrant-client`) storing `384`-dimensional `all-MiniLM-L6-v2` embeddings (`sentence-transformers`) in collection `agronomy_knowledge`
- **Document Processing:** `pdfplumber` (PDFs), `langchain-text-splitters` (`RecursiveCharacterTextSplitter`), custom JSONL/Markdown readers
- **LLM Integration:** `openai` SDK configured for a local DeepSeek OpenAI-compatible server (e.g., Ollama, vLLM, or LM Studio)
- **Infrastructure:** Docker Compose (containerized PostgreSQL 15 and Qdrant; FastAPI runs locally during development)

---

## Project Structure

```text
RAG/
├── app/
│   ├── __init__.py
│   ├── db.py                # PostgreSQL read-only query helper for crop/soil tables
│   ├── llm_service.py       # Local DeepSeek (OpenAI SDK) + RAG prompt orchestration
│   ├── main.py              # FastAPI app (/health, /retrieve, /chat, /recommend, /api/chat)
│   └── qdrant_service.py    # Qdrant retriever using all-MiniLM-L6-v2 on agronomy_knowledge
├── data/
│   ├── .gitkeep
│   └── *.zip                # Raw agricultural datasets (extracted automatically by ETL)
├── scripts/
│   ├── .gitkeep
│   └── ingest_data.py       # Recursive zip extraction + SQL & Qdrant ETL pipeline (--if-empty)
├── tests/
│   └── test_rag_service.py  # Offline unit & integration tests
├── .env.example             # Environment variable template
├── .gitignore
├── docker-compose.yml       # PostgreSQL 15 & Qdrant containers
├── README.md
└── requirements.txt         # Python dependencies
```

---

## Datasets & ETL Pipeline (`scripts/ingest_data.py`)

The `data/` directory contains raw compressed archives covering multiple agronomic domains:

- **Kherson:** Regional crop rotation candidates and documentation (`Kherson-*.zip`)
- **USDA / Marchfeld & Dryad / ERA:** Crop sequence boundaries, soil parameters, agricultural management, and long-term yield trials (`3. USDA — Crop Sequence Boundaries-*.zip`)
- **Broadbalk (Rothamsted):** Long-term winter wheat crop nutrient content and yield datasets (`Dataset_ Broadbalk Crop Nutrient Content, Wheat 1968-2017-*.zip`)
- **CIMMYT:** Long-term crop experiment Excel data (`CIMMYT — Long-term crop experiments-*.zip`)
- **Agronomy QA & Evaluation Datasets:** Agricultural Q&A CSVs (`Agronomy QA — Agriculture-*.zip`) and structured JSONL sets covering farmer interviews, soil/climate interpretation, rotation history checks, and constraints (`Chatgpt datasets-*.zip`)

Running `scripts/ingest_data.py` executes three sequential stages with per-file error recovery:

1. **`extract_all_zips()`** — Recursively discovers and extracts all `.zip` files (including nested sub-archives) into sibling folders using Windows long-path (`\\?\`) support.
2. **`ingest_sql()`** — Walks `data/` for `.csv` (auto-detecting `,` vs `;` delimiters and `utf-8`/`cp1252`/`latin1` encodings) and `.xlsx` workbooks (all sheets), converts `.` placeholders to `NaN`, sanitizes and deduplicates table/column names (`<= 60` chars), and writes tables into PostgreSQL.
3. **`ingest_vector()`** — Extracts text from `.jsonl` (formatted into readable `key: value` records), `.md`, and `.pdf` files, chunks text with `RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)`, embeds with `SentenceTransformer("all-MiniLM-L6-v2")`, and upserts points (`source_file`, `text`) in batches of `64` into the Qdrant collection `agronomy_knowledge`.

---

## Quick Start

### 1. Clone the Repository & Configure Environment

**Windows (PowerShell):**
```powershell
git clone https://github.com/BoHdANchIck/rag.git
cd rag
Copy-Item .env.example .env
```

**Linux / macOS (Bash):**
```bash
git clone https://github.com/BoHdANchIck/rag.git
cd rag
cp .env.example .env
```

### 2. Start PostgreSQL 15 & Qdrant

```bash
docker compose up -d
```

### 3. Set Up Python Virtual Environment & Install Dependencies

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux / macOS (Bash):**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the ETL Ingestion Pipeline

```bash
python scripts/ingest_data.py
```

### 5. Run the FastAPI Server

From `RAG/`:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Or launch the full unified stack (Docker DBs + ETL `--if-empty` + RAG + main backend + frontend) from the repository root:

```bash
./run.sh        # Linux / macOS
.\run.ps1       # Windows PowerShell
```

---

## Service Endpoints

| Service | URL | Notes |
| --- | --- | --- |
| FastAPI Health Check | http://127.0.0.1:8001/health | Returns service status, Qdrant & PostgreSQL status |
| Hybrid Retrieval | `POST http://127.0.0.1:8001/retrieve` | Returns Qdrant chunks + PostgreSQL table samples |
| RAG Chat / Recommend | `POST http://127.0.0.1:8001/chat` / `/recommend` | Grounded local DeepSeek + Qdrant + PostgreSQL answer |
| Frontend NDJSON Stream | `POST http://127.0.0.1:8001/api/chat` | Compatible with the `frontend/` NDJSON chat contract |
| FastAPI Swagger Docs | http://127.0.0.1:8001/docs | Interactive OpenAPI documentation |
| Qdrant Dashboard | http://localhost:6333/dashboard | Inspect `agronomy_knowledge` collection & vectors |
| PostgreSQL 15 | `localhost:5432` | Database `kherson_crop_db` (default creds in `.env.example`) |

---

## Environment Variables (`.env.example`)

| Variable | Default | Description |
| --- | --- | --- |
| `APP_ENV` | `development` | Application environment label |
| `APP_HOST` / `APP_PORT` | `0.0.0.0` / `8000` | Local FastAPI bind host and port |
| `POSTGRES_USER` | `agro_user` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `agro_password` | PostgreSQL password |
| `POSTGRES_DB` | `kherson_crop_db` | PostgreSQL database name |
| `DATABASE_URL` | `postgresql+psycopg2://agro_user:agro_password@localhost:5432/kherson_crop_db` | SQLAlchemy PostgreSQL connection string |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant HTTP endpoint |
| `QDRANT_COLLECTION_NAME` | `agronomy_knowledge` | Target Qdrant collection name |
| `OPENAI_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible base URL for local DeepSeek |
| `OPENAI_API_KEY` | `sk-local-deepseek-dummy-key` | Placeholder key for local inference server |
| `DEEPSEEK_MODEL` | `deepseek-r1:8b` | Local DeepSeek model identifier |
