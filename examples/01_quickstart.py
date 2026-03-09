"""Demo 01: Quickstart — mem0-compatible CRUD operations via Memorus."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from examples._mock_backend import create_mock_memory


def main() -> None:
    # --- from_config factory ---
    from memorus.memory import Memory

    m = Memory.__new__(Memory)
    from memorus.config import MemorusConfig

    m._config = MemorusConfig.from_dict({})
    print("[1/7] from_config: MemorusConfig created OK")

    # --- Use mock memory for CRUD ---
    mem = create_mock_memory(ace_enabled=False)

    # add
    result = mem.add("Use ruff for Python linting", user_id="alice")
    assert "results" in result
    mid = result["results"][0]["id"]
    print(f"[2/7] add: created memory {mid}")

    # search
    found = mem.search("ruff linting")
    assert "results" in found
    print(f"[3/7] search: found {len(found['results'])} result(s)")

    # get_all
    all_mems = mem.get_all(user_id="alice")
    assert "results" in all_mems or "memories" in all_mems
    print(f"[4/7] get_all: {len(all_mems.get('results', all_mems.get('memories', [])))} memories")

    # update
    updated = mem.update(mid, "Use ruff check --fix for auto-fixing")
    assert updated["memory"] == "Use ruff check --fix for auto-fixing"
    print(f"[5/7] update: memory {mid} updated")

    # history
    hist = mem.history(mid)
    assert "changes" in hist
    assert len(hist["changes"]) >= 2  # add + update
    print(f"[6/7] history: {len(hist['changes'])} change(s)")

    # delete
    mem.delete(mid)
    try:
        mem.get(mid)
        assert False, "Should have raised KeyError"
    except KeyError:
        pass
    print("[7/7] delete: memory removed OK")

    # reset
    mem.add("temp data", user_id="bob")
    mem.reset()
    after_reset = mem.get_all()
    assert len(after_reset.get("results", after_reset.get("memories", []))) == 0
    print("      reset: all memories cleared")

    print("\nPASS: 01_quickstart")


if __name__ == "__main__":
    main()
