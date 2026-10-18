"""Final Phase 4 regression and persistence test."""

import sys

from app.constants import USER_ID
from app.memory import create_memory


TEST_MARKER = "PHASE-4-FINAL-VERIFICATION"
TEST_FACT = f"My final Phase 4 verification code is {TEST_MARKER}."


def write_memory():
    print("Initializing Mem0...")
    memory = create_memory()

    print(f"Adding test fact with infer=True...")
    result = memory.add(TEST_FACT, user_id=USER_ID, infer=True)
    print("Add result:", result)

    print("\nSearching for the memory in this same process...")
    search_result = memory.search(TEST_MARKER, filters={"user_id": USER_ID})
    results = search_result.get("results", [])

    if results:
        print(f"PASS: Found {len(results)} memory record(s) in current process.")
    else:
        print("FAIL: Could not find the memory immediately after adding it.")
        sys.exit(1)


if __name__ == "__main__":
    write_memory()