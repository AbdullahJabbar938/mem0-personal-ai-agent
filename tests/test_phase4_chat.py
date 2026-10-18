import importlib.metadata
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


def main():
    question = "What personal AI agent project am I building?"

    memory = create_memory()

    search_result = memory.search(
        question,
        filters={"user_id": USER_ID},
    )
    results = search_result.get("results", [])

    memory_context = "\n".join(
        f"- {item['memory']}"
        for item in results
        if item.get("memory")
    )

    print("Question:", question)
    print("\nRetrieved memory context:")
    print(memory_context or "No relevant memories were found.")

    llm_config = MEMORY_CONFIG["llm"]["config"]
    client = Client(host=llm_config["ollama_base_url"])

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

    response = client.chat(
        model=llm_config["model"],
        messages=messages,
        format={
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
            },
            "required": ["answer"],
        },
        options={
            "temperature": 0,
            "num_predict": 120,
        },
        think=False,
    )

    raw = (response.message.content or "").strip()

    print("\nOllama package version:",
          importlib.metadata.version("ollama"))
    print("Raw model output length:", len(raw))

    answer = ""
    try:
        parsed = json.loads(raw)
        answer = (parsed.get("answer") or "").strip()
    except json.JSONDecodeError as exc:
        print("\nModel did not return valid JSON:", exc)
        print("Raw output:")
        print(raw)
        raise SystemExit("Chat test failed: model output was not valid JSON.")

    print("Answer length:", len(answer))
    print("\nAssistant:")
    if answer:
        print(answer)
    else:
        print("The model returned an empty answer.")
        raise RuntimeError("Chat test failed: empty answer field.")


if __name__ == "__main__":
    main()