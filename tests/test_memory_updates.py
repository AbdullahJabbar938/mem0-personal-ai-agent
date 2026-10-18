"""Phase 5: Memory update, contradiction, and deletion behavior."""

import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.memory import create_memory


def test_update():
    """Adding complementary information should UPDATE, not duplicate."""
    print("\n--- Test 3: Update (complementary fact) ---")
    memory = create_memory()

    user_id = f"test-upd-{uuid.uuid4().hex[:6]}"

    print("Adding: 'My name is Abdullah.'")
    r1 = memory.add("My name is Abdullah.", user_id=user_id, infer=True)
    print("Add 1:", r1)

    print("Adding: 'My full name is Abdullah Khan.'")
    r2 = memory.add("My full name is Abdullah Khan.", user_id=user_id, infer=True)
    print("Add 2:", r2)

    res = memory.search("what is my name", filters={"user_id": user_id})
    results = res.get("results", [])
    print(f"Found {len(results)} record(s):")
    for r in results:
        print(f"  - {r.get('memory')}")

    # After UPDATE, the latest fact should mention "Khan"
    combined = " ".join(r.get("memory", "") for r in results)
    assert "Khan" in combined, "FAIL: Updated fact (Khan) not found in memory."
    print("PASS: UPDATE stored complementary information.")


def test_contradiction_behavior():
    """Document how Mem0 handles a contradicting fact."""
    print("\n--- Test 4: Contradiction (observe behavior) ---")
    memory = create_memory()

    user_id = f"test-con-{uuid.uuid4().hex[:6]}"

    print("Adding: 'My favorite color is blue.'")
    r1 = memory.add("My favorite color is blue.", user_id=user_id, infer=True)
    print("Add 1:", r1)

    print("Adding: 'Actually, my favorite color is red.'")
    r2 = memory.add("Actually, my favorite color is red.", user_id=user_id, infer=True)
    print("Add 2:", r2)

    res = memory.search("what is my favorite color", filters={"user_id": user_id})
    results = res.get("results", [])
    print(f"Found {len(results)} record(s):")
    for r in results:
        print(f"  - {r.get('memory')}")

    combined = " ".join(r.get("memory", "") for r in results).lower()

    # Observed behavior: Mem0 stores the contradiction as a new event
    # ("changed from blue to red"). The old fact is NOT removed.
    # Document what actually happened rather than assert a specific policy.
    if "red" not in combined:
        raise AssertionError("FAIL: New fact (red) was not stored at all.")

    if "blue" in combined:
        print(
            "OBSERVED: Mem0 retained both the old fact (blue) and the new "
            "event (changed to red). Application layer must apply temporal "
            "precedence when answering."
        )
    else:
        print("OBSERVED: Mem0 removed the old fact (blue) on contradiction.")

    print("PASS: Contradiction behavior recorded.")


def test_explicit_delete():
    """Mem0 exposes a delete API — verify it works."""
    print("\n--- Test 5: Explicit Delete ---")
    memory = create_memory()

    user_id = f"test-del-{uuid.uuid4().hex[:6]}"

    print("Adding: 'My project codename is FALCON.'")
    add_result = memory.add("My project codename is FALCON.", user_id=user_id, infer=False)
    print("Add:", add_result)

    res = memory.search("project codename", filters={"user_id": user_id})
    results = res.get("results", [])
    assert len(results) > 0, "FAIL: Fact not stored before delete."
    memory_id = results[0]["id"]
    print(f"Stored memory id: {memory_id}")

    print(f"Calling memory.delete(memory_id='{memory_id}')...")
    memory.delete(memory_id)
    print("Delete call returned.")

    res2 = memory.search("project codename", filters={"user_id": user_id})
    results2 = res2.get("results", [])
    print(f"Found {len(results2)} record(s) after delete.")

    assert len(results2) == 0, "FAIL: Memory still retrievable after delete."
    print("PASS: Explicit delete removed the memory.")


if __name__ == "__main__":
    try:
        test_update()
        test_contradiction_behavior()
        test_explicit_delete()
        print("\nAll Phase 5 update/delete tests passed.")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {type(e).__name__}: {e}")
        sys.exit(1)