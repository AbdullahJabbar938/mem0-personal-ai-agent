
MEMORY_CONFIG = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "abdullah_memories",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 768,
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "qwen3:4b",
            "ollama_base_url": "http://localhost:11434",
            "temperature": 0,
            "max_tokens": 2000,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text:latest",
            "ollama_base_url": "http://localhost:11434",
        },
    },
}
