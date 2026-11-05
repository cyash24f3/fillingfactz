from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = PROJECT_ROOT / "data" / "filings.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RUNTIME_DIR = PROJECT_ROOT / "runtime"
DATABASE_PATH = RUNTIME_DIR / "corpus.sqlite"

MODEL_NAME = "qwen3.5:9b"

CHUNK_SIZE = 1800
CHUNK_OVERLAP = 300
INDEX_VERSION = "3"
MEMORY_PATH = RUNTIME_DIR / "evidence_memory.sqlite"
