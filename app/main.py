
from app.config import (
    OLLAMA_MODEL,
    QDRANT_COLLECTION,
)


def main():
    print("Mem0 Personal AI Agent")
    print(f"Configured Ollama model: {OLLAMA_MODEL}")
    print(f"Qdrant collection: {QDRANT_COLLECTION}")


if __name__ == "__main__":
    main()
