"""Phase 5: Persistence across process restarts."""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.memory import create_memory


STATE_FILE = os.path.join(os.path.dirname(__file__), ".persistence_state.json")
USER_ID = "phase5-persistence-user"
MARKER = "PHASE5-PERSISTENCE-MARKER-9931"
FACT = f"My persistence verification code is {MARKER}."


def write_phase():
    """Process 1: add a fact, save the memory ID to disk, exit."""
    print("=== WRITE PHASE ===")
    memory = create_memory()

    print(f"Adding: '{FACT}' with infer=False")
    result = memory.add(FACT, user_id=USER_ID, infer=False)
    print("Add result:", result)

    memory_id = result["results"][0]["id"]
    print(f"Saved memory id: {memory_id}")

    with open(STATE_FILE, "w") as f:
        json.dump({"memory_id": memory_id, "marker": MARKER}, f)

    print(f"Wrote state to {STATE_FILE}")


def read_phase():
    """Process 2 (separate run): load memory ID, verify it's still retrievable."""
    print("=== READ PHASE (fresh process) ===")
    if not os.path.exists(STATE_FILE):
        raise FileNotFoundError(
            f"State file not found: {STATE_FILE}. Run write phase first."
        )

    with open(STATE_FILE) as f:
        state = json.load(f)

    expected_id = state["memory_id"]
    marker = state["marker"]
    print(f"Loaded state: memory_id={expected_id}, marker={marker}")

    memory = create_memory()

    print(f"Searching for marker: {marker}")
    res = memory.search(marker, filters={"user_id": USER_ID})
    results = res.get("results", [])
    print(f"Found {len(results)} record(s):")
    for r in results:
        print(f"  - id={r.get('id')}  memory={r.get('memory')}")

    ids = [r.get("id") for r in results]
    assert expected_id in ids, (
        f"FAIL: Expected memory ID {expected_id} not found in fresh process. "
        f"Found IDs: {ids}"
    )
    print("PASS: Memory persisted across Python process restart.")


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "read":
            read_phase()
        else:
            write_phase()
            print("\nWrite phase complete. Now run:")
            print(f"  python .\\tests\\test_memory_persistence.py read")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {type(e).__name__}: {e}")
        sys.exit(1)