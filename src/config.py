import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))
NEXUSAI_DATA_DIR = os.getenv("NEXUSAI_DATA_DIR", "data")
NEXUSAI_CHROMA_DIR = os.getenv("NEXUSAI_CHROMA_DIR", "./chroma_db")
