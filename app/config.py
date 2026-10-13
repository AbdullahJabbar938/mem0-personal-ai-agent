
import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_EMBEDDING_MODEL = os.getenv(
    "OLLAMA_EMBEDDING_MODEL",
    "nomic-embed-text",
)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv(
    "QDRANT_COLLECTION",
    "personal_memories",
)
