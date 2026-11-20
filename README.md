# NexusAI — Autonomous Multi-Agent Data Analyst & Self-Evaluating RAG System

A 100% local, privacy-preserving AI data analyst that answers natural language business and compliance questions across structured CSV datasets and unstructured PDF policy documents.

## Key Features
- **Intelligent Multi-Agent Routing (LangGraph):** Automatically routes queries to SQL Analytics, Policy RAG, or Hybrid Audit mode.
- **Structured Data Analytics (DuckDB):** Converts plain-English questions into SQL queries and generates interactive Plotly charts.
- **Unstructured Document RAG (ChromaDB):** Retrieves and cites exact policy rules from uploaded PDF documents.
- **Self-Evaluating Verification:** Grades every generated answer on a 1-5 Groundedness Scale against retrieved evidence.
- **Modern Web UI (FastAPI + Tailwind + Plotly):** Drag-and-drop CSV/PDF ingestion, live source tracking, SQL inspection, and interactive visualizations.
- **100% Offline Execution:** Powered locally via Ollama (qwen3.5:9b).

## Tech Stack
- **LLM Engine:** Ollama (qwen3.5:9b)
- **Agent Orchestration:** LangGraph & LangChain
- **Structured Query Engine:** DuckDB
- **Vector Database:** ChromaDB
- **Backend API:** FastAPI & Uvicorn
- **Frontend UI:** HTML5, Tailwind CSS, Plotly.js, Marked.js

## Quick Start
1. Activate environment: `.\.venv\Scripts\Activate.ps1`
2. Start Ollama model: `ollama run qwen3.5:9b`
3. Start web server: `.\.venv\Scripts\uvicorn src.api.main:app --port 8000`
4. Open `[http://127.0.0.1:8000](http://127.0.0.1:8000)` in your browser.
