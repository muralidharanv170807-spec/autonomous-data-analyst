# NexusAI — Autonomous Multi-Agent Data Analyst

NexusAI is a privacy-first data analysis workspace that answers business and compliance questions using local CSV datasets and PDF policy documents. Its agent workflow combines structured analysis, policy retrieval, and hybrid audits, then evaluates the answer's groundedness before presenting results.

## What it does

- **Runs locally:** Uses Ollama with `qwen3.5:9b`; prompts, datasets, and results stay on your machine.
- **Routes with LangGraph:** Chooses SQL analytics, Policy RAG, or Hybrid analysis based on the question.
- **Analyzes CSV data:** Loads CSV files into DuckDB and generates read-only queries, result tables, and interactive Plotly charts.
- **Retrieves policy evidence:** Indexes PDF documents in ChromaDB and returns excerpts with source and page citations.
- **Evaluates answers:** A self-evaluation step assigns a groundedness score from 1 to 5.
- **Manages sources:** Upload CSV/PDF files through drag-and-drop or the file picker, and remove indexed files from Active Sources.
- **Exports results:** Download the latest SQL result rows as a timestamped `NexusAI_results_<timestamp>.csv` file.
- **Serves a browser UI:** FastAPI serves the NexusAI interface and provides the query, upload, and source-management endpoints.

## Architecture

```text
UI -> FastAPI -> LangGraph Router [SQL / Policy RAG / Hybrid]
                         |                 |
                         +---- DuckDB / ChromaDB
                                   |
                            Self-Evaluator
```

SQL routes query DuckDB; Policy RAG retrieves evidence from ChromaDB; Hybrid routes combine both. The LangGraph workflow synthesizes the evidence and evaluates answer groundedness.

## Project structure

```text
autonomous-data-analyst/
├── .env.example               # Safe local configuration defaults
├── frontend/
│   └── index.html             # Browser-based NexusAI workspace
├── src/
│   ├── config.py              # Environment and local runtime settings
│   ├── agents/
│   │   └── graph.py           # LangGraph routing, analysis, and evaluation
│   ├── api/
│   │   └── main.py            # FastAPI UI and data endpoints
│   ├── database/
│   │   └── duckdb_engine.py   # CSV loading and DuckDB queries
│   └── rag/
│       └── vector_store.py    # PDF indexing and ChromaDB retrieval
├── data/
│   ├── generate_sample_data.py
│   └── *.csv / *.pdf          # Sample datasets and policy sources
├── chroma_db/                 # Local ChromaDB persistence
├── app.py                     # Streamlit interface
├── Modelfile                  # Ollama model configuration
└── requirements.txt           # Python dependencies
```

Files in `data/` are sample/demo inputs. Run `python data/generate_sample_data.py` from the repository root to generate synthetic `sales_transactions.csv` and `company_compliance_policy.pdf`; the other sample CSV and PDF files are provided as example inputs. Review the employee names/compensation and transaction-style records in the sample CSVs and confirm they are synthetic or anonymized before distributing the repository publicly. `chroma_db/` and Python virtual environments are local runtime data and are excluded from Git.

## Windows / PowerShell setup

Prerequisites: Python 3.12 (or another compatible Python version), Git, and [Ollama for Windows](https://ollama.com/download).

1. Open PowerShell in the cloned project folder and create/activate a virtual environment:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, allow it for the current terminal only, then activate:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the Python dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Create a local environment file from the safe defaults and customize it if needed:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   `.env` is ignored by Git; `.env.example` contains only non-secret local defaults. It configures `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_NUM_CTX`, `NEXUSAI_DATA_DIR`, and `NEXUSAI_CHROMA_DIR`.

4. Pull the local model and make sure Ollama is running:

   ```powershell
   ollama pull qwen3.5:9b
   ollama run qwen3.5:9b
   ```

   Keep Ollama available while using NexusAI. If Ollama is already running as a background service, the model can be pulled in one terminal and the API started in another.

5. In a second PowerShell terminal, activate the environment and start the API:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
   ```

6. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. The interactive API documentation is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Example questions

- **SQL:** “What is total revenue and profit by region?”
- **Policy RAG:** “What are the regional discount caps and minimum profit margin rules?”
- **Hybrid audit:** “Which transactions violate our regional discount caps?”
- **SQL:** “What is the total amount_usd and average flag_count by txn_type in wire_transfers?”

Upload CSV and PDF sources from the left-hand panel. CSV files are loaded into DuckDB; PDF policy sources are indexed in ChromaDB. Remove a source from the Active Sources list when it is no longer needed.

## Push to GitHub

From the project directory, stage and commit the project, configure the GitHub remote, and push the `main` branch:

```powershell
git remote set-url origin https://github.com/muralidharanv170807-spec/autonomous-data-analyst.git
git add .
git commit -m "Update NexusAI project configuration and documentation"
git push -u origin main
```

For a new local repository without an `origin` remote, add it once:

```powershell
git remote add origin https://github.com/muralidharanv170807-spec/autonomous-data-analyst.git
```
