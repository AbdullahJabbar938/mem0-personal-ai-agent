"""Interactive conversational agent for the mem0-personal-ai-agent project."""

import json

from ollama import Client

from app.config import MEMORY_CONFIG
from app.constants import USER_ID
from app.memory import create_memory


SYSTEM_PROMPT = (
    "You are a personal assistant. "
    "Answer the user's question directly using only the supplied memory context. "
    "Return a JSON object with exactly one field named 'answer'. "
    "The 'answer' value must be the final answer, in at most two sentences. "
    "Do not include analysis, reasoning, drafts, or extra fields. "
    "If the answer is not in the context, set answer to: "
    "'I don't have that information in memory.'"
)

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
}


def retrieve_context(memory, question: str) -> str:
    try:
        search_result = memory.search(question, filters={"user_id": USER_ID})
    except Exception as exc:
        print(f"[memory search error] {exc}")
        return ""
    results = search_result.get("results", []) if isinstance(search_result, dict) else []
    return "\n".join(
        f"- {item['memory']}" for item in results if item.get("memory")
    )


def ask_model(client, model: str, question: str, memory_context: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Memory context:\n"
                f"{memory_context or 'No relevant memories found.'}\n\n"
                f"Question: {question}"
            ),
        },
    ]
    try:
        response = client.chat(
            model=model,
            messages=messages,
            format=ANSWER_SCHEMA,
            options={"temperature": 0, "num_predict": 120},
            think=False,
        )
    except Exception as exc:
        return f"[ollama error] {exc}"

    raw = (response.message.content or "").strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return f"[malformed model output] {raw or '<empty>'}"
    return (parsed.get("answer") or "").strip()


def main() -> None:
    print("MemO Personal AI Agent")
    print("Type 'exit' or 'quit' to stop.\n")

    # --- startup: memory ---
    try:
        memory = create_memory()
    except Exception as exc:
        print(f"[startup error] Could not initialize Mem0: {exc}")
        print("Check that Qdrant (localhost:6333) and Ollama (localhost:11434) are running.")
        return

    llm_config = MEMORY_CONFIG["llm"]["config"]
    client = Client(host=llm_config["ollama_base_url"])

    # --- startup: ollama liveness ---
    try:
        client.list()
    except Exception as exc:
        print(f"[startup error] Could not reach Ollama at {llm_config['ollama_base_url']}: {exc}")
        return

    while True:
        try:
            raw_input = input("\nYou: ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        question = raw_input.strip()
        if not question:
            # Blank or whitespace-only input: skip entirely, no model call.
            continue
        if question.lower() in {"exit", "quit"}:
            print("Exiting.")
            break

        memory_context = retrieve_context(memory, question)
        answer = ask_model(client, llm_config["model"], question, memory_context)

        if not answer:
            print("Assistant: The model returned an empty answer.\n")
        else:
            print(f"Assistant: {answer}\n")


if __name__ == "__main__":
    main()