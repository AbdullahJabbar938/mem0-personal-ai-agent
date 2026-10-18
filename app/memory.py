
from ollama import Client
from mem0 import Memory

from app.config import MEMORY_CONFIG


def disable_ollama_thinking():
    """Disable Qwen3 thinking for Ollama chat requests."""
    if getattr(Client.chat, "_thinking_disabled_for_mem0", False):
        return

    original_chat = Client.chat

    def chat_without_thinking(self, *args, **kwargs):
        kwargs.setdefault("think", False)
        return original_chat(self, *args, **kwargs)

    chat_without_thinking._thinking_disabled_for_mem0 = True
    Client.chat = chat_without_thinking


def create_memory():
    """Create Mem0 with local Ollama and persistent Qdrant storage."""
    disable_ollama_thinking()
    return Memory.from_config(MEMORY_CONFIG)
