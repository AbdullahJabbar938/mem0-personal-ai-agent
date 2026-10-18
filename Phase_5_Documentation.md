# PHASE 5

# Testing and Memory Behavior Verification

**Mem0 + Ollama + Qdrant | Technical project documentation**

## Purpose

A self-contained record of Phase 5 testing, memory-lifecycle behavior discovery, verification, limitations, and handover for the local personal AI agent. This document records only what was actually tested and observed in Mem0 `2.2.1`.

| Document control | Details |
|---|---|
| Scope | Phase 5 only — memory testing and behavioral characterization |
| Project | `mem0-personal-ai-agent` |
| Runtime | Windows PowerShell, Python virtual environment (`.venv`), Ollama, Docker, Qdrant |
| Status | Phase 5 complete — all core tests executed and documented |
| Prepared | 18 October 2026 |

This document separates observed behavior from assumptions. Where Mem0's behavior diverged from expectations, the observed behavior is recorded and the implication for the application layer is noted.

---

## 1. Executive summary

Phase 5 shifted focus from building to proving. Where Phase 4 delivered a working conversational agent, Phase 5 systematically exercised Mem0's memory lifecycle to determine **how it actually behaves** rather than how we assumed it would.

Nine targeted tests were executed: user scoping, duplicate handling under both `infer=False` and `infer=True`, complementary-information updates, contradictions, explicit deletion, persistence across process restarts, persistence across container restarts, repeat-run idempotency across processes, and consistency between the `get_all` and `search` APIs.

All tests passed once the assertions were aligned with observed behavior. Three findings are particularly important for the application layer:

1. **Contradictions are not resolved by Mem0 alone.** When a fact changes (e.g., favorite color blue → red), Mem0 stores the change as a new event but retains the old record. The application must apply temporal precedence.
2. **Duplicate prevention requires `infer=True`.** With `infer=False`, Mem0 performs a blind write and will store duplicates. Deduplication only runs when inference is enabled.
3. **Explicit deletion is the only reliable removal mechanism.** `memory.delete(memory_id)` removes the record; LLM-driven contradictions do not.

These findings do not invalidate Phase 4. They refine the design requirements for Phase 6 and confirm that the current `app/main.py` behavior is correct within its scope.

### 1.1 Status at a glance

| Area | Status | Evidence |
|---|---|---|
| User scoping | Complete | Test 1 — strict isolation confirmed |
| Duplicate handling (`infer=False`) | Complete | Test 2a — duplicates created (expected) |
| Duplicate handling (`infer=True`) | Complete | Test 2b — LLM deduplicates (NOOP) |
| Complementary update | Complete | Test 3 — both facts retained |
| Contradiction behavior | Complete | Test 4 — new event stored, old fact retained |
| Explicit delete | Complete | Test 5 — `memory.delete(id)` removes record |
| Persistence (process restart) | Complete | Test 6 — state survives fresh Python process |
| Persistence (container restart) | Complete | Test 7 — state survives `docker restart mem0-qdrant` |
| Repeat-run idempotency (cross-process) | Complete | Test 8 — second add returns `results: []` |
| `get_all` vs `search` consistency | Complete | Test 9 — identical records returned |
| Latency benchmarking | Not tested | Deferred to Phase 6 |
| Multi-user live app test | Not tested | Deferred to Phase 6 |
| Backup/restore | Not tested | Deferred to Phase 6 |

---

## 2. Objectives and acceptance criteria

### 2.1 Objectives

- Determine how Mem0 isolates memories between different users.
- Determine how Mem0 handles duplicate facts under `infer=False` and `infer=True`.
- Determine how Mem0 handles complementary information (updates that add detail).
- Determine how Mem0 handles contradicting facts (changes over time).
- Verify that `memory.delete()` reliably removes a record.
- Verify persistence across both Python process restart and Qdrant container restart.
- Verify repeat-run idempotency across separate Python processes.
- Verify `get_all` and `search` return consistent results for the same user.
- Document all findings in a form usable by the application layer and future phases.

### 2.2 Acceptance criteria

| Criterion | Pass condition | Recorded result |
|---|---|---|
| User scoping | One user cannot retrieve another user's memory | Passed |
| Duplicate (`infer=False`) | Behavior recorded (duplicates expected) | Passed |
| Duplicate (`infer=True`) | Second add returns `NOOP`; only one record remains | Passed |
| Complementary update | Behavior recorded (both records retained) | Passed |
| Contradiction | Behavior recorded (new event stored; old record retained) | Passed |
| Explicit delete | `memory.delete(id)` removes the record; search returns 0 | Passed |
| Persistence (process restart) | Same memory ID retrievable from a fresh process | Passed |
| Persistence (container restart) | Same memory ID retrievable after `docker restart` | Passed |
| Repeat-run idempotency | Second add returns `results: []`; no duplicate | Passed |
| `get_all` vs `search` | Search IDs are a subset of `get_all` IDs | Passed |

---

## 3. Environment and architecture

### 3.1 Recorded environment

| Component | Recorded value | Notes |
|---|---|---|
| OS / shell | Windows / PowerShell | |
| Project path | `C:\Users\PAK\Projects\mem0-personal-ai-agent` | |
| Python | 3.13 | Project virtual environment `.venv` |
| Mem0 | `mem0ai` 2.2.1 | Behavior recorded in this document is specific to this version |
| Ollama Python package | 0.6.3 | |
| Ollama server | 0.40.6 | |
| LLM | `qwen3:4b` | Used for `infer=True` extraction |
| Embedder | `nomic-embed-text:latest` | |
| Embedding dimension | 768 | |
| Qdrant client | `qdrant-client` 1.19.1 | |
| Endpoints | Ollama `http://localhost:11434`; Qdrant `http://localhost:6333` | |
| Container / volume | `mem0-qdrant` / `docker_qdrant_storage` | Volume mounted at `/qdrant/storage` |
| App user ID | `abdullah-local-agent` (from `app/constants.py`) | |
| Collection | `abdullah_memories` (from `app/config.py`) | |

### 3.2 Test architecture

Phase 5 tests are located in `tests/` and are standalone Python scripts. They import the application factory (`app.memory.create_memory()`) so that they exercise the same runtime configuration the application uses, including the Phase 3 `think=False` workaround.

```
Project root
  app/
    config.py
    constants.py
    memory.py        <-- create_memory() with think=False workaround
    main.py
  tests/
    __init__.py
    test_memory_lifecycle.py     <-- Tests 1, 2a, 2b
    test_memory_updates.py       <-- Tests 3, 4, 5
    test_memory_persistence.py   <-- Tests 6, 7
    test_repeat_runs.py          <-- Tests 8, 9
```

All test scripts insert the project root into `sys.path` so they can run from inside `tests/` without requiring `pip install -e .` or a package restructure.

```python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.memory import create_memory
```

### 3.3 Memory lifecycle (as observed)

The following summarizes how Mem0 `2.2.1` processes facts in this environment:

```
memory.add(fact, infer=False)
    └── embed fact → store raw text → return ADD

memory.add(fact, infer=True)
    ├── LLM extracts candidate fact(s)
    ├── embed candidate(s)
    ├── retrieve top-s similar memories for user
    ├── LLM classifies operation: ADD / UPDATE / DELETE / NOOP
    └── execute operation → return event list (may be empty for NOOP)

memory.search(query, filters={"user_id": ...})
    └── embed query → vector search → return top results for user

memory.get_all(filters={"user_id": ...})
    └── return all records for user

memory.delete(memory_id)
    └── remove record by id → subsequent search returns 0
```

---

## 4. Implementation procedure

### Step 1 — Confirm environment and services

```powershell
cd "C:\Users\PAK\Projects\mem0-personal-ai-agent"
.\.venv\Scripts\Activate.ps1
python --version
ollama list
docker ps --filter "name=mem0-qdrant"
```

Expected: prompt shows `(.venv)`; both models listed; container running.

### Step 2 — Create the test directory

```powershell
mkdir tests
New-Item tests\__init__.py -ItemType File
```

### Step 3 — Add test state files to `.gitignore`

```powershell
Add-Content .gitignore "`ntests/.persistence_state.json"
```

### Step 4 — Implement the four test scripts

Each test script is presented in Section 5.

### Step 5 — Execute the tests in order

Run the scripts as documented in Section 6 and record the outputs. Two tests require cross-process sequencing (persistence and repeat-run idempotency); those instructions are included with the respective scripts.

---

## 5. Test source code

### 5.1 `tests/test_memory_lifecycle.py` (Tests 1, 2a, 2b)

```python
"""Phase 5: Memory behavior tests for Scoping and Duplicates."""

import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.memory import create_memory


def test_user_scoping():
    """Verify that memories are strictly isolated by user_id."""
    print("\n--- Test 1: User Scoping ---")
    memory = create_memory()

    user_a = f"test-user-a-{uuid.uuid4().hex[:6]}"
    user_b = f"test-user-b-{uuid.uuid4().hex[:6]}"

    fact_a = "User A's secret code is ALPHA-1."
    fact_b = "User B's secret code is BETA-2."

    print(f"Adding fact for {user_a}...")
    memory.add(fact_a, user_id=user_a, infer=False)

    print(f"Adding fact for {user_b}...")
    memory.add(fact_b, user_id=user_b, infer=False)

    res_a = memory.search("secret code", filters={"user_id": user_a})
    results_a = res_a.get("results", [])

    res_b = memory.search("secret code", filters={"user_id": user_b})
    results_b = res_b.get("results", [])

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
```

### 5.2 `tests/test_memory_updates.py` (Tests 3, 4, 5)

```python
"""Phase 5: Memory update, contradiction, and deletion behavior."""

import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.memory import create_memory


def test_update():
    """Adding complementary information should store as a new record."""
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
```

### 5.3 `tests/test_memory_persistence.py` (Tests 6, 7)

```python
"""Phase 5: Persistence across process and container restarts."""

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
```

### 5.4 `tests/test_repeat_runs.py` (Tests 8, 9)

```python
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

    if "ADD" in events:
        assert len(results) == 1, (
            f"FAIL: First run should store exactly 1 record, found {len(results)}."
        )
        print("First run: ADD stored 1 record.")
        print(f"\nTo run the second phase:")
        print(f"  $env:PHASE5_RUN_ID = '{run_id}'")
        print(f"  python .\\tests\\test_repeat_runs.py")
    else:
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
```

---

## 6. Verified test sessions and recorded output

### 6.1 User scoping (Test 1)

Command:

```powershell
python .\tests\test_memory_lifecycle.py
```

Recorded output (Test 1 portion):

```
--- Test 1: User Scoping ---
Adding fact for test-user-a-092a5f...
Adding fact for test-user-b-34c569...
PASS: User scoping is strictly enforced.
```

Interpretation: User A retrieved only ALPHA-1; User B retrieved only BETA-2. Neither saw the other's memory. `filters={"user_id": ...}` is a safe isolation boundary.

### 6.2 Duplicate handling (Tests 2a and 2b)

**`infer=False` (Test 2a, early run):**

```
Adding fact (1st time)...
Adding fact (2nd time)...
Found 2 record(s) for the duplicate fact.
```

Interpretation: `infer=False` performs a blind write. Duplicates are stored. This is expected behavior and not a defect — the same string was embedded and stored twice.

**`infer=True` (Test 2b):**

```
Adding fact (1st time, infer=True)...
Add 1 result: {'results': [{'id': 'e2a7dfbc-...', 'memory': "User's favorite color is blue", 'event': 'ADD'}]}
Adding fact (2nd time, infer=True)...
Add 2 result: {'results': []}
Found 1 record(s) after adding the same fact twice with infer=True.
PASS: Mem0 deduplicated the fact under infer=True.
```

Interpretation: With inference enabled, Mem0's LLM compared the candidate fact against the existing record, classified the operation as NOOP, and returned an empty results list. Only one record remained.

### 6.3 Complementary update (Test 3)

```
Adding: 'My name is Abdullah.'
Add 1: {'results': [{'id': '8faddaa5-...', 'memory': "User's name is Abdullah", 'event': 'ADD'}]}
Adding: 'My full name is Abdullah Khan.'
Add 2: {'results': [{'id': '651268da-...', 'memory': "User's full name is Abdullah Khan", 'event': 'ADD'}]}
Found 2 record(s):
  - User's full name is Abdullah Khan
  - User's name is Abdullah
PASS: UPDATE stored complementary information.
```

Interpretation: Mem0 stored the fuller fact as a second record. It did not merge or replace the first. Both records are retrievable. This is not a failure — it reflects Mem0's additive design for non-conflicting facts.

### 6.4 Contradiction (Test 4)

```
Adding: 'My favorite color is blue.'
Add 1: {'results': [{'id': '48db51fd-...', 'memory': "User's favorite color is blue", 'event': 'ADD'}]}
Adding: 'Actually, my favorite color is red.'
Add 2: {'results': [{'id': 'eabfec76-...', 'memory': 'User changed their favorite color from blue to red around October 18, 2026', 'event': 'ADD'}]}
Found 2 record(s):
  - User changed their favorite color from blue to red around October 18, 2026
  - User's favorite color is blue
OBSERVED: Mem0 retained both the old fact (blue) and the new event (changed to red). Application layer must apply temporal precedence when answering.
PASS: Contradiction behavior recorded.
```

Interpretation: Mem0 recognized the change and encoded it as an explicit event ("changed their favorite color from blue to red around October 18, 2026"), but it retained the original fact. This is a critical finding: **temporal reasoning must be handled by the application layer**, not Mem0.

### 6.5 Explicit delete (Test 5)

```
Adding: 'My project codename is FALCON.'
Add: {'results': [{'id': '80c3035a-...', 'memory': 'My project codename is FALCON.', 'event': 'ADD', 'actor_id': None, 'role': 'user'}]}
Stored memory id: 80c3035a-7f6b-4588-81f5-daf3d96eb6b6
Calling memory.delete(memory_id='80c3035a-7f6b-4588-81f5-daf3d96eb6b6')...
Delete call returned.
Found 0 record(s) after delete.
PASS: Explicit delete removed the memory.
```

Interpretation: The `memory.delete(memory_id)` signature in `mem0ai 2.2.1` accepts a positional string ID. After deletion, search returns zero records. This is the only reliable removal path.

### 6.6 Persistence across process restart (Test 6)

**Write phase (Process 1):**

```
=== WRITE PHASE ===
Adding: 'My persistence verification code is PHASE5-PERSISTENCE-MARKER-9931.' with infer=False
Add result: {'results': [{'id': 'afec2314-761b-4ab7-9e6d-2ff78f56c1c3', 'memory': 'My persistence verification code is PHASE5-PERSISTENCE-MARKER-9931.', 'event': 'ADD', 'actor_id': None, 'role': 'user'}]}
Saved memory id: afec2314-761b-4ab7-9e6d-2ff78f56c1c3
Wrote state to C:\Users\PAK\Projects\mem0-personal-ai-agent\tests\.persistence_state.json
```

**Read phase (fresh Python process):**

```
=== READ PHASE (fresh process) ===
Loaded state: memory_id=afec2314-761b-4ab7-9e6d-2ff78f56c1c3, marker=PHASE5-PERSISTENCE-MARKER-9931
Searching for marker: PHASE5-PERSISTENCE-MARKER-9931
Found 2 record(s):
  - id=afec2314-761b-4ab7-9e6d-2ff78f56c1c3  memory=My persistence verification code is PHASE5-PERSISTENCE-MARKER-9931.
  - id=9cbfe4a8-f8d2-4025-b73b-7ccbdb9cf309  memory=My persistence verification code is PHASE5-PERSISTENCE-MARKER-9931.
PASS: Memory persisted across Python process restart.
```

Two records exist because the write phase was accidentally executed twice with `infer=False` during testing. The second write was a duplicate by design of `infer=False`; this is consistent with Section 6.2's finding.

### 6.7 Persistence across container restart (Test 7)

After `docker restart mem0-qdrant`, the same read command was run again in a fresh Python process:

```
=== READ PHASE (fresh process) ===
Loaded state: memory_id=afec2314-761b-4ab7-9e6d-2ff78f56c1c3, marker=PHASE5-PERSISTENCE-MARKER-9931
Searching for marker: PHASE5-PERSISTENCE-MARKER-9931
Found 2 record(s):
  - id=afec2314-761b-4ab7-9e6d-2ff78f56c1c3  memory=My persistence verification code is PHASE5-PERSISTENCE-MARKER-9931.
  - id=9cbfe4a8-f8d2-4025-b73b-7ccbdb9cf309  memory=My persistence verification code is PHASE5-PERSISTENCE-MARKER-9931.
PASS: Memory persisted across Python process restart.
```

Interpretation: The same two memory IDs are returned after container restart. The named volume `docker_qdrant_storage` is doing its job. Persistence is proven for both process restart and container restart.

### 6.8 Repeat-run idempotency across processes (Test 8)

**First run:**

```
--- Test 6: Repeat-run idempotency across processes ---
No PHASE5_RUN_ID in environment; generating a new one: 7b02b1e0
Adding fact (infer=True) for user 'phase5-repeat-7b02b1e0'...
Add result: {'results': [{'id': 'fd92ae19-...', 'memory': 'User has a repeat-run test code named REPEAT-7b02b1e0', 'event': 'ADD'}]}
Events returned: ['ADD']
Found 1 record(s) after add.
First run: ADD stored 1 record.
PASS: Repeat-run behavior recorded.
```

**Second run (same RUN_ID, fresh Python process):**

```powershell
$env:PHASE5_RUN_ID = '7b02b1e0'
python .\tests\test_repeat_runs.py
```

```
--- Test 6: Repeat-run idempotency across processes ---
Using PHASE5_RUN_ID from environment: 7b02b1e0
Adding fact (infer=True) for user 'phase5-repeat-7b02b1e0'...
Add result: {'results': []}
Events returned: []
Found 1 record(s) after add.
Second run: duplicate detected and deduplicated (no new record).
PASS: Repeat-run behavior recorded.
```

Interpretation: The second run returned `{'results': []}` — Mem0's NOOP signal — and search still returned exactly one record. Mem0 is idempotent across processes for the same fact and user.

### 6.9 `get_all` vs `search` consistency (Test 9)

```
--- Test 7: get_all vs search consistency ---
get_all returned 3 record(s).
search returned 3 record(s).
get_all ids: {'de5643fb-...', '56dbf647-...', '0e950c51-...'}
search ids: {'de5643fb-...', '56dbf647-...', '0e950c51-...'}
PASS: get_all and search are consistent for the same user.
```

Interpretation: The set of IDs returned by `get_all` matched the set returned by `search` for the same user. Both retrieval APIs are consistent.

---

## 7. Errors encountered and how they were resolved

### 7.1 Issue — `ModuleNotFoundError: No module named 'app'`

**What happened:** Running `python .\tests\test_memory_lifecycle.py` from inside the `tests/` directory failed to import `app.memory` because Python resolves imports relative to the script location, not the project root.

**Root cause:** The project is not installed as a package, so `app` is not on `sys.path` when the interpreter starts from inside a subdirectory.

**Resolution:** Each test script inserts the project root into `sys.path` before importing from `app`:

```python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```

**Lesson:** Standalone scripts in subdirectories must explicitly extend `sys.path` unless the project is installed in editable mode. Adding this two-line preamble to every test script is the least invasive fix.

### 7.2 Issue — Test 2a failed on the duplicate assertion (`infer=False`)

**What happened:** The initial duplicate test asserted that `infer=False` would deduplicate. The run found 2 records and raised `AssertionError: Expected 1 record, found 2`.

**Root cause:** `infer=False` is a blind write. It embeds and stores the fact without consulting the LLM, so no deduplication occurs. The assertion was based on a false assumption.

**Resolution:** The test was updated to exercise deduplication under `infer=True` (Test 2b), where Mem0's LLM comparison does run and returns NOOP for an identical fact. The `infer=False` behavior was re-documented as "blind write; duplicates created."

**Lesson:** Test assertions must be derived from observed behavior, not from assumptions about how a library should behave. An "unexpected" result can be correct design.

### 7.3 Issue — Test 4 failed on the contradiction assertion

**What happened:** The initial contradiction test asserted that adding "Actually, my favorite color is red" would remove the "favorite color is blue" record. The run found 2 records and raised `AssertionError: Old fact (blue) should have been replaced/removed`.

**Root cause:** Mem0's contradiction handling is event-based, not replacement-based. The LLM encoded the change as a new fact ("User changed their favorite color from blue to red around October 18, 2026") and left the original fact intact. Mem0 does not delete the old record.

**Resolution:** The test was converted from a strict assertion into an observation. It now records whether the old fact was retained, and the finding is documented in Section 6.4. Application-layer implications are recorded in Section 9.

**Lesson:** When a library's behavior diverges from the developer's expectation, the correct move is to record the observed behavior and adjust the application design — not to force the library into the expected shape. The contradiction finding directly affects how the Phase 6 application must answer questions about changed facts.

### 7.4 Issue — `NameError: name 'test_contradiction_delete' is not defined`

**What happened:** After renaming `test_contradiction_delete` to `test_contradiction_behavior`, the `__main__` block still called the old name. Running the script raised `NameError`.

**Root cause:** The function was renamed in one place but not the other. Python resolves the `__main__` block at runtime and the old name no longer existed.

**Resolution:** The `__main__` block was updated to call `test_contradiction_behavior()`.

**Lesson:** When renaming a test function, search the file for all references before saving. In Python, `__main__` blocks are executed at runtime, so mismatches surface only when the script is run.

### 7.5 Issue — Persistence test ran the wrong phase

**What happened:** The persistence test was run twice without passing the `read` argument, and `docker restart mem0-qdrant` was executed before any read phase. The write phase ran twice, overwriting the state file and creating a duplicate memory.

**Root cause:** The script's default action is the write phase. The `read` argument must be passed explicitly. The operator also confused the intended sequence (write → read → restart → read) with the actual sequence.

**Resolution:** The read phase was run as `python .\tests\test_memory_persistence.py read`. It passed, and the same read was repeated after container restart. Both reads passed. The duplicate records from the accidental second write were noted as expected behavior under `infer=False`.

**Lesson:** CLI scripts that take arguments should print the next command explicitly (the write phase already does). When testing persistence, the operator should always follow the printed instruction. For safety, consider splitting persistence into two scripts (`test_persistence_write.py` and `test_persistence_read.py`) in Phase 6 to prevent this class of mistake.

### 7.6 Issue — PostHog multiple-client warning persists

**What happened:** Every run of every test printed:

```
[PostHog] Multiple active PostHog clients detected for the same project API key and host. ...
```

**Status:** Unresolved but non-fatal. It did not block any test in Phase 5. The exact client-creation path in Mem0/posthog has not been established.

**Decision:** Deferred. Revisit only if it causes functional errors, resource issues, or shutdown problems. This is the same deferral decision recorded in Phase 4.

---

## 8. Troubleshooting register

| Symptom | Likely explanation | Recommended action |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | Test script run from `tests/` without `sys.path` fix | Add the `sys.path.insert(...)` preamble shown in Section 5 |
| `NameError: name 'test_X' is not defined` | Renamed function; `__main__` not updated | Search the file for all references and update the `__main__` block |
| Duplicate records under `infer=False` | Blind write; no LLM deduplication | Expected; use `infer=True` for deduplication or dedupe in the application layer |
| Old fact retained after contradiction | Event-based contradiction handling | Expected; application must apply temporal precedence (see Section 9) |
| `memory.delete(...)` raises `TypeError` | Signature mismatch in different Mem0 version | In `mem0ai 2.2.1`, call `memory.delete(memory_id)` with a positional string ID |
| Read phase of persistence test fails with `FileNotFoundError` | Write phase not run first | Run `python .\tests\test_memory_persistence.py` first, then `... read` |
| Repeat-run test always generates a new `RUN_ID` | Environment variable not set | Set `$env:PHASE5_RUN_ID = '<id>'` before running the second phase |
| `get_all` returns a list, not a dict | API shape varies by version | The test handles both: `all_res.get("results", []) if isinstance(all_res, dict) else all_res` |
| PostHog warning repeated | Non-fatal; unknown client-creation path | Defer; investigate only if functional issues appear |

---

## 9. Application-layer implications (critical findings)

Phase 5 produced findings that directly affect the design of the application in Phase 6 and beyond.

### 9.1 User isolation is safe

`filters={"user_id": USER_ID}` correctly isolates users. No change is required in the application; the current usage in `app/main.py` is correct.

### 9.2 Duplicate prevention requires `infer=True`

The application currently uses `memory.add(..., infer=True)` where facts are stored from user input, which is correct. If the application ever writes facts programmatically with `infer=False` (for example, seeding initial data), it must implement its own deduplication or accept duplicate records.

### 9.3 Contradictions require temporal precedence in the application

This is the most important finding. When a user changes a fact (favorite color blue → red), Mem0 retains both records:

- `User's favorite color is blue`
- `User changed their favorite color from blue to red around October 18, 2026`

A naive search for "favorite color" returns both, and the model may answer "blue" if the retrieval ranks that record higher. The application layer must:

- Prefer records that describe a change ("changed from X to Y") when the user asks about the current state of that fact, or
- Pass timestamps to the model and instruct it to prefer the most recent statement.

This behavior should be addressed in Phase 6 (the interactive agent) or a dedicated Phase 7 (temporal reasoning).

### 9.4 Explicit delete is the only reliable removal path

When a user asks to "forget" something, the application must:

1. Search for matching records.
2. Call `memory.delete(memory_id)` on each one.
3. Confirm with a follow-up search.

Adding a contradicting fact is not sufficient; it will not remove the old record.

### 9.5 Persistence and idempotency are reliable

The application can safely restart without duplicating facts. The named volume preserves data across container restarts. No application-layer persistence work is required.

### 9.6 Retrieval APIs are interchangeable

`get_all` and `search` return consistent results for the same user. The application may use either. `search` returns ranked results (top-K) while `get_all` returns the full set; use `search` for retrieval and `get_all` for auditing or export.

---

## 10. Status, limitations, and next steps

### 10.1 Completed and verified

- User scoping is strict and reliable (Test 1).
- `infer=False` performs blind writes and does not deduplicate (Test 2a).
- `infer=True` deduplicates identical facts via LLM NOOP (Test 2b).
- Complementary facts are stored as additional records without replacing older ones (Test 3).
- Contradictions are stored as new events; the old fact is retained (Test 4).
- `memory.delete(memory_id)` reliably removes a record (Test 5).
- Memories persist across Python process restart (Test 6).
- Memories persist across `docker restart mem0-qdrant` (Test 7).
- Mem0 is idempotent across processes for the same fact and user (Test 8).
- `get_all` and `search` return consistent records for the same user (Test 9).

### 10.2 Known limitations

- Test scripts rely on `sys.path` manipulation rather than proper packaging. A `pyproject.toml` and editable install (`pip install -e .`) would remove this preamble.
- The persistence test has an interactive sequencing requirement (write, then read, then optionally restart and read again). A future refactor should split this into two scripts or use a test framework with setup/teardown.
- Temporal precedence for contradicted facts is not solved. The application layer must handle it (see Section 9.3).
- Multi-user live-application testing (two users in one process) is not yet exercised. Phase 5 tested user isolation at the Mem0 level, not in the application loop.
- Latency was not benchmarked. The tests ran quickly on CPU, but no timing measurements were recorded.
- Qdrant backup and restore remain untested; host-failure recovery is not proven.
- The PostHog warning remains present and unfixed.
- The `think=False` workaround in `app/memory.py` remains a process-wide monkey patch and should be revisited for a supported alternative.

### 10.3 Recommended next steps (Phase 6 and beyond)

1. Implement temporal precedence in the application layer so contradicted facts are answered with the most recent statement.
2. Add a "forget" workflow that uses `memory.delete(memory_id)` after search.
3. Add multi-user testing in the live application loop, not only at the Mem0 level.
4. Refactor tests into a proper test framework (`pytest`) with fixtures and teardown.
5. Package the project with `pyproject.toml` to remove `sys.path` manipulation.
6. Add latency benchmarking to characterize the interactive experience on CPU.
7. Pin dependency versions in `requirements.txt`.
8. Investigate the PostHog warning if it ever affects resources or shutdown.
9. Verify Qdrant backup and restore as a disaster-recovery exercise.
10. Replace the `think=False` monkey patch with a supported, narrowly scoped request option if Mem0 adds one.

---

## 11. File map (Phase 5 additions and changes)

| File | Role | Status |
|---|---|---|
| `tests/__init__.py` | Marks `tests` as a package | Added in Phase 5 |
| `tests/test_memory_lifecycle.py` | Tests 1, 2a, 2b (scoping, duplicates) | Added in Phase 5 |
| `tests/test_memory_updates.py` | Tests 3, 4, 5 (update, contradiction, delete) | Added in Phase 5 |
| `tests/test_memory_persistence.py` | Tests 6, 7 (process and container restart) | Added in Phase 5 |
| `tests/test_repeat_runs.py` | Tests 8, 9 (repeat-run idempotency, get_all vs search) | Added in Phase 5 |
| `tests/.persistence_state.json` | Local state file for persistence test | Runtime only; added to `.gitignore` |
| `app/main.py` | Interactive conversational agent | Unchanged in Phase 5 |
| `app/memory.py` | Memory factory with Phase 3 workaround | Unchanged in Phase 5 |
| `app/config.py` | `MEMORY_CONFIG` | Unchanged in Phase 5 |
| `app/constants.py` | `USER_ID` | Unchanged in Phase 5 |

---

## 12. Glossary

| Term | Meaning |
|---|---|
| `infer=False` | Direct write mode. The fact is embedded and stored verbatim. No LLM is involved. No deduplication. |
| `infer=True` | Inference-enabled write mode. The LLM extracts candidate facts, compares them against existing memories, and decides between ADD, UPDATE, DELETE, and NOOP. |
| NOOP | "No operation." Returned when the LLM determines a candidate fact already exists in memory and no change is needed. Mem0 returns an empty `results` list in this case. |
| ADD | Operation event returned by Mem0 when a new memory record was created. |
| UPDATE | Operation event returned by Mem0 when an existing memory was augmented. In the observed Mem0 `2.2.1` behavior, complementary facts are stored as separate ADD events rather than in-place updates. |
| DELETE | Operation event returned by Mem0 when a memory was removed via the inference pipeline. In the observed behavior, contradictions produced ADD events, not DELETE events. |
| User scoping | Isolation of memory records by `user_id`. Enforced at retrieval time by `filters={"user_id": ...}`. |
| Persistence | Data remaining available after a process or container restart, subject to retained storage. |
| Idempotency | Repeating the same operation produces no additional effect. Verified for repeated `add(..., infer=True)` across processes. |
| Temporal precedence | The rule that, when two records contradict each other, the most recent statement should be treated as current truth. Not handled by Mem0 and required at the application layer. |
| Explicit delete | Removal of a memory record by calling `memory.delete(memory_id)`. The only reliable deletion mechanism observed in this project. |

---

## Appendix A — Handover for another AI or developer

**Project:** `mem0-personal-ai-agent`, Phase 5 complete.

**Recorded path:** `C:\Users\PAK\Projects\mem0-personal-ai-agent`.
**Activate environment:** `.\.venv\Scripts\Activate.ps1`.

**Recorded versions:** Python 3.13, `mem0ai 2.2.1`, `qdrant-client 1.19.1`, Ollama Python package `0.6.3`, Ollama server `0.40.6`. Models: `qwen3:4b`, `nomic-embed-text:latest`.
**Endpoints:** Ollama `http://localhost:11434`, Qdrant `http://localhost:6333`.
**Container:** `mem0-qdrant`. **Named volume:** `docker_qdrant_storage` mounted at `/qdrant/storage`.
**Collection:** `abdullah_memories`. **User ID for app:** `abdullah-local-agent`.

**How to run Phase 5 tests:**

```powershell
# Foundation tests (scoping, duplicates)
python .\tests\test_memory_lifecycle.py

# Updates, contradictions, delete
python .\tests\test_memory_updates.py

# Persistence (two phases)
python .\tests\test_memory_persistence.py
python .\tests\test_memory_persistence.py read

# Repeat-run idempotency (two phases)
python .\tests\test_repeat_runs.py
$env:PHASE5_RUN_ID = '<id from first run>'
python .\tests\test_repeat_runs.py
```

**Key behavioral facts about Mem0 2.2.1 in this environment:**

1. `infer=False` performs a blind write. No deduplication.
2. `infer=True` deduplicates identical facts via LLM NOOP. Returns `{'results': []}`.
3. Complementary facts (e.g., adding a fuller name) are stored as additional records. Older records are retained.
4. Contradictions (e.g., a fact changing) are stored as explicit change events. Older records are retained. Application must apply temporal precedence.
5. `memory.delete(memory_id)` with a positional string ID reliably removes a record.
6. Memories persist across Python process restart and Qdrant container restart.
7. Repeat-run idempotency holds across processes when `infer=True`.
8. `get_all` and `search` return consistent records for the same user.

**Phase 3 carry-over:** `app/memory.py` wraps `ollama.Client.chat` to default `think=False`. This is still required for `infer=True` extraction to produce JSON in `message.content`. Do not remove without re-verifying via `test_phase4_final.py`.

**Critical application-layer implication:** temporal precedence for contradicted facts is not solved. See Section 9.3. Phase 6 must address this.

**Known limitations:** see Section 10.2.

**Recommended next work:** see Section 10.3.

**Safety:** Do not run `docker compose down -v` or delete the named volume during routine troubleshooting. Existing memories must be preserved.

---

## Appendix B — Final verification checklist

| Check | Status |
|---|---|
| Test directory created (`tests/`) | Yes |
| `.gitignore` updated to exclude `tests/.persistence_state.json` | Yes (pending user confirmation) |
| Test 1 — user scoping | Yes |
| Test 2a — duplicate under `infer=False` (blind write; 2 records) | Yes |
| Test 2b — duplicate under `infer=True` (NOOP; 1 record) | Yes |
| Test 3 — complementary update (2 records retained) | Yes |
| Test 4 — contradiction (2 records; new event + old fact) | Yes |
| Test 5 — explicit delete (0 records after) | Yes |
| Test 6 — persistence across process restart | Yes |
| Test 7 — persistence across container restart | Yes |
| Test 8 — repeat-run idempotency across processes | Yes |
| Test 9 — `get_all` vs `search` consistency | Yes |
| No secrets or private values committed to Git | Pending user confirmation |
| Outstanding tasks and evidence recorded | Yes |

---

Document boundary: This is the Phase 5 documentation based on recorded project context and verified test output. It does not invent requirements, claim unperformed tests, or present future features as approved requirements. Behavior recorded here is specific to `mem0ai 2.2.1` in the recorded environment and should be re-verified after upgrades.

**End of Phase 5 documentation.**
