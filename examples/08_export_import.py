"""Demo 08: Export/Import — JSON + Markdown roundtrip verification."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

from examples._mock_backend import create_mock_memory, populate_mock_memories


def main() -> None:
    mem = create_mock_memory(ace_enabled=False)

    # Populate with sample data including metadata
    for i, content in enumerate([
        "Use pytest -x for fast failure detection",
        "Docker multi-stage builds reduce image size",
        "Always pin dependency versions in requirements.txt",
    ]):
        mem.add(
            content,
            user_id="demo_user",
            metadata={
                "memx_section": ["debugging", "tools", "workflow"][i],
                "memx_knowledge_type": ["method", "trick", "preference"][i],
                "memx_instructivity_score": [70.0, 65.0, 80.0][i],
                "memx_scope": "global",
            },
        )

    # --- 1. JSON export ---
    exported = mem.export(format="json")
    assert isinstance(exported, dict)
    assert "version" in exported
    assert "memories" in exported
    assert exported["total"] == 3
    print(f"[1/4] JSON export: {exported['total']} memories, version={exported['version']}")

    # --- 2. Markdown export ---
    md = mem.export(format="markdown")
    assert isinstance(md, str)
    assert "# MemX Knowledge Export" in md
    print(f"[2/4] Markdown export: {len(md)} chars")
    # Print first few lines
    for line in md.splitlines()[:6]:
        print(f"       {line}")

    # --- 3. JSON roundtrip import ---
    mem2 = create_mock_memory(ace_enabled=False)
    import_result = mem2.import_data(exported, format="json")
    assert import_result["imported"] == 3
    assert import_result["skipped"] == 0
    print(f"[3/4] Import: imported={import_result['imported']}, "
          f"skipped={import_result['skipped']}, merged={import_result['merged']}")

    # Verify data survived roundtrip
    all_after = mem2.get_all()
    mems_after = all_after.get("results", all_after.get("memories", []))
    assert len(mems_after) == 3
    print(f"       Verified: {len(mems_after)} memories after import")

    # --- 4. String JSON import ---
    json_str = json.dumps(exported)
    mem3 = create_mock_memory(ace_enabled=False)
    import_result2 = mem3.import_data(json_str, format="json")
    assert import_result2["imported"] == 3
    print(f"[4/4] String import: imported={import_result2['imported']}")

    print("\nPASS: 08_export_import")


if __name__ == "__main__":
    main()
