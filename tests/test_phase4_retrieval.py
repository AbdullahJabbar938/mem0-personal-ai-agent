
from app.constants import USER_ID
from app.memory import create_memory

FACT = (
    "My name is Abdullah. "
    "I am building a personal AI agent using Mem0, Ollama, and Qdrant. "
    "My current project phase is Phase 4, conversational agent."
)

QUESTION = "What personal AI agent project am I building?"


def main():
    print("Initializing memory...")
    memory = create_memory()

    print("\n1. Saving a test fact...")
    add_result = memory.add(FACT, user_id=USER_ID, infer=True)
    print(add_result)

    print("\n2. Searching for the fact using a natural-language question...")
    search_result = memory.search(
        QUESTION,
        filters={"user_id": USER_ID},
    )
    print(search_result)

    results = search_result.get("results", [])
    if results:
        print("\nPASS: Search returned at least one memory.")
    else:
        print("\nNOT CONFIRMED: Search returned no memories.")
        raise RuntimeError("Retrieval test did not find a memory.")


if __name__ == "__main__":
    main()
