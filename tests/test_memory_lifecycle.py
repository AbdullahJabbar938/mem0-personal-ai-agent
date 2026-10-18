"""Phase 5: Memory behavior tests for Scoping and Duplicates."""

import sys
import os
import uuid

# Add the project root to sys.path so we can import 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.memory import create_memory


def test_user_scoping():
    """Verify that memories are strictly isolated by user_id."""
    print("\n--- Test 1: User Scoping ---")
    memory = create_memory()
    
    # Use dynamic IDs so the test can be run repeatedly without collision
    user_a = f"test-user-a-{uuid.uuid4().hex[:6]}"
    user_b = f"test-user-b-{uuid.uuid4().hex[:6]}"
    
    fact_a = "User A's secret code is ALPHA-1."
    fact_b = "User B's secret code is BETA-2."

    print(f"Adding fact for {user_a}...")
    memory.add(fact_a, user_id=user_a, infer=False)
    
    print(f"Adding fact for {user_b}...")
    memory.add(fact_b, user_id=user_b, infer=False)

    # Search for User A's fact, filtered by User A
    res_a = memory.search("secret code", filters={"user_id": user_a})
    results_a = res_a.get("results", [])
    
    # Search for User A's fact, filtered by User B (should be empty)
    res_b = memory.search("secret code", filters={"user_id": user_b})
    results_b = res_b.get("results", [])

    # Assertions
    assert len(results_a) > 0, "FAIL: User A should see their own memory."
    assert "ALPHA-1" in str(results_a), "FAIL: User A should retrieve ALPHA-1."
    assert "BETA-2" not in str(results_a), "FAIL: User A should NOT see User B's memory."

    assert len(results_b) > 0, "FAIL: User B should see their own memory."
    assert "BETA-2" in str(results_b), "FAIL: User B should retrieve BETA-2."
    assert "ALPHA-1" not in str(results_b), "FAIL: User B should NOT see User A's memory."

    print("PASS: User scoping is strictly enforced.")


def test_duplicate_handling():
    """Verify how Mem0 handles adding the same fact twice under infer=True."""
    print("\n--- Test 2: Duplicate Handling (infer=True) ---")
    memory = create_memory()
    
    user_id = f"test-dup-{uuid.uuid4().hex[:6]}"
    fact = "My favorite color is blue."

    print("Adding fact (1st time, infer=True)...")
    add_1 = memory.add(fact, user_id=user_id, infer=True)
    print("Add 1 result:", add_1)
    
    print("Adding fact (2nd time, infer=True)...")
    add_2 = memory.add(fact, user_id=user_id, infer=True)
    print("Add 2 result:", add_2)

    res = memory.search("favorite color", filters={"user_id": user_id})
    results = res.get("results", [])

    print(f"Found {len(results)} record(s) after adding the same fact twice with infer=True.")
    for r in results:
        print(f"  - id={r.get('id')}  memory={r.get('memory')}")

    # With infer=True, the LLM should NOT create a second identical record.
    # It should either NOOP or UPDATE the existing one.
    assert len(results) == 1, (
        f"FAIL: Expected 1 record with infer=True, found {len(results)}. "
        "Mem0 failed to deduplicate under inference."
    )
    
    print("PASS: Mem0 deduplicated the fact under infer=True.")


if __name__ == "__main__":
    try:
        test_user_scoping()
        test_duplicate_handling()
        print("\nAll Phase 5 foundation tests passed.")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)