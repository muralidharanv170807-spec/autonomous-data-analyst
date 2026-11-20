import os
import re
import json
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from src.config import NEXUSAI_DATA_DIR
from src.agents.graph import run_query, db_engine, vector_store

app = FastAPI(title="NexusAI API")

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    route: str
    sql_query: str
    sql_results: List[Dict[str, Any]]
    chart_json: Optional[Dict[str, Any]] = None
    citations: List[Dict[str, Any]]
    groundedness_score: int

@app.get("/")
def serve_ui():
    return FileResponse("frontend/index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/files")
def list_files():
    os.makedirs(NEXUSAI_DATA_DIR, exist_ok=True)
    return {"files": [f for f in sorted(os.listdir(NEXUSAI_DATA_DIR)) if f.endswith((".csv", ".pdf"))]}

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    try:
        os.makedirs(NEXUSAI_DATA_DIR, exist_ok=True)
        saved = []
        for f in files:
            safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", f.filename)
            dest = os.path.join(NEXUSAI_DATA_DIR, safe_name)
            with open(dest, "wb") as out:
                out.write(await f.read())
            if safe_name.lower().endswith(".pdf"):
                vector_store.add_files([dest])
            saved.append(safe_name)
        db_engine._load_csv_files()
        return {"uploaded": saved}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Upload failed: {str(e)}"})

@app.delete("/files/{filename}")
def delete_file(filename: str):
    safe_name = os.path.basename(filename)
    target = os.path.join(NEXUSAI_DATA_DIR, safe_name)
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        os.remove(target)
        if safe_name.lower().endswith(".csv"):
            db_engine.drop_table_for_file(safe_name)
        elif safe_name.lower().endswith(".pdf"):
            source_stem = os.path.splitext(safe_name)[0]
            vector_store.delete_by_source(source_stem)
        return {"deleted": safe_name}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Delete failed: {str(e)}"})

@app.post("/analyze", response_model=QueryResponse)
def analyze(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        db_engine._load_csv_files()
        raw_result = run_query(req.question)
        clean_result = json.loads(json.dumps(raw_result, default=str))
        return clean_result
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Analysis error: {str(e)}"})
