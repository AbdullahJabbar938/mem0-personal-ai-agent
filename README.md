# Mem0 Personal AI Agent

A local-first, privacy-focused conversational AI agent with long-term memory. 
Built with **Mem0**, **Ollama**, **Qwen3**, and **Qdrant**.

This agent remembers facts about you across sessions, retrieves them intelligently using semantic search, and answers questions using a local language model—without sending your data to the cloud.

## 🏗️ Architecture

- **Memory Framework:** [Mem0](https://mem0.ai) (handles extraction, deduplication, and retrieval)
- **Language Model:** Ollama running `qwen3:4b` (local inference)
- **Embeddings:** Ollama running `nomic-embed-text` (local vectorization)
- **Vector Database:** Qdrant (persistent Docker volume)

## 📋 Prerequisites

- Windows (PowerShell) / macOS / Linux
- Python 3.11+
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Ollama](https://ollama.com) installed and running

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/mem0-personal-ai-agent.git
cd mem0-personal-ai-agent