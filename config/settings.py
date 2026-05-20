"""
Central configuration for EY AI Challenge - Law Agent.
All constants, paths, and environment-dependent settings live here.
Never hardcode these values elsewhere in the codebase.
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
DATA_GRAPH_DIR = BASE_DIR / "data" / "graph"

# ── LLM ───────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = "claude-3-5-sonnet-20241022"
LLM_MAX_TOKENS = 1024

# ── Embeddings ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
FAISS_INDEX_PATH = DATA_GRAPH_DIR / "faiss_index"

# ── Legal codes ───────────────────────────────────────────────────────────────
SUPPORTED_CODES = {
    "CT": "Código do Trabalho",
    "CC": "Código Civil",
}

# ── Regex (compiled once, reused everywhere) ──────────────────────────────────
ARTICLE_REF_PATTERN = re.compile(
    r'\bart(?:igo)?\.?\s*(\d+\.º(?:-[A-Z])?)',
    re.IGNORECASE
)

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
