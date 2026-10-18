"""Phase 5: Repeat-run idempotency across processes, and get_all behavior."""

import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.memory import create_memory


def test_repeat_run_across_processes():
    """Run this script twice with the same RUN_ID; second run should NOOP."""
    print("\n--- Test 6: Repeat-run idempotency across processes ---")

    run_id = os.environ.get("PHASE5_RUN_ID")
    if not run_id:
        run_id = uuid.uuid4().hex[:8]
        print(f"No PHASE5_RUN_ID in environment; generating a new one: {run_id}")
        print(f"To test the second run, set it first:")
        print(f"  $env:PHASE5_RUN_ID = '{run_id}'")
    else:
        print(f"Using PHASE5_RUN_ID from environment: {run_id}")

    user_id = f"phase5-repeat-{run_id}"
    fact = f"My repeat-run test code is REPEAT-{run_id}."

    memory = create_memory()

    print(f"Adding fact (infer=True) for user '{user_id}'...")
    result = memory.add(fact, user_id=user_id, infer=True)
    print("Add result:", result)

    events = [r.get("event") for r in result.get("results", [])]
    print(f"Events returned: {events}")

    res = memory.search(f"REPEAT-{run_id}", filters={"user_id": user_id})
    results = res.get("results", [])
    print(f"Found {len(results)} record(s) after add.")

    # On the first run we expect exactly one ADD and 1 record.
    # On the second run (same RUN_ID), we expect NOOP or an empty results list
    # from the add, and still 1 record.
    if "ADD" in events:
        assert len(results) == 1, (
            f"FAIL: First run should store exactly 1 record, found {len(results)}."
        )
        print("First run: ADD stored 1 record.")
        print(f"\nTo run the second phase:")
        print(f"  $env:PHASE5_RUN_ID = '{run_id}'")
        print(f"  python .\\tests\\test_repeat_runs.py")
    else:
        # Second run: dedupe
        assert len(results) == 1, (
            f"FAIL: Second run should still see 1 record, found {len(results)}."
        )
        print("Second run: duplicate detected and deduplicated (no new record).")

    print("PASS: Repeat-run behavior recorded.")


def test_get_all_matches_search():
    """Confirm get_all and search return consistent memories for the same user."""
    print("\n--- Test 7: get_all vs search consistency ---")

    user_id = f"phase5-getall-{uuid.uuid4().hex[:6]}"
    facts = [
        "My favorite food is biryani.",
        "I work on a local AI agent project.",
        "I live in a city with four seasons.",
    ]

    memory = create_memory()
    for f in facts:
        memory.add(f, user_id=user_id, infer=False)

    all_res = memory.get_all(filters={"user_id": user_id})
    # mem0 2.2.1 may return a list or a dict
    all_items = (
        all_res.get("results", []) if isinstance(all_res, dict) else all_res
    )
    print(f"get_all returned {len(all_items)} record(s).")

    search_res = memory.search("tell me about the user", filters={"user_id": user_id})
    search_items = search_res.get("results", [])
    print(f"search returned {len(search_items)} record(s).")

    all_ids = {r.get("id") for r in all_items}
    search_ids = {r.get("id") for r in search_items}

    print(f"get_all ids: {all_ids}")
    print(f"search ids: {search_ids}")

    # search may return only the top-K, but every returned search id must
    # exist in get_all for the same user.
    extra = search_ids - all_ids
    assert not extra, (
        f"FAIL: search returned IDs not present in get_all: {extra}"
    )

    print("PASS: get_all and search are consistent for the same user.")


if __name__ == "__main__":
    try:
        test_repeat_run_across_processes()
        test_get_all_matches_search()
        print("\nAll Phase 5 repeat-run/get_all tests passed.")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {type(e).__name__}: {e}")
        sys.exit(1)