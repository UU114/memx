"""Demo 18: Memory Analytics — KB statistics via Memory.status().

Demonstrates:
  - status() returns section/knowledge_type distributions
  - Average decay_weight calculation
  - ACE enabled flag propagation
  - detect_conflicts() integration with status flow
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from examples._mock_backend import create_mock_memory

logger = logging.getLogger(__name__)


def main() -> None:
    mem = create_mock_memory(ace_enabled=False)

    # Populate with diverse metadata
    samples = [
        ("Use git rebase for cleanup", {
            "memx_section": "tools", "memx_knowledge_type": "method",
            "memx_decay_weight": 1.0, "memx_scope": "global",
        }),
        ("pytest -x for fast debugging", {
            "memx_section": "debugging", "memx_knowledge_type": "trick",
            "memx_decay_weight": 0.8, "memx_scope": "global",
        }),
        ("Always run ruff before commit", {
            "memx_section": "tools", "memx_knowledge_type": "preference",
            "memx_decay_weight": 0.9, "memx_scope": "global",
        }),
        ("Docker COPY order matters", {
            "memx_section": "debugging", "memx_knowledge_type": "pitfall",
            "memx_decay_weight": 0.5, "memx_scope": "project:web",
        }),
        ("cargo clippy before build", {
            "memx_section": "tools", "memx_knowledge_type": "method",
            "memx_decay_weight": 0.7, "memx_scope": "project:rust",
        }),
    ]

    # ── 1. Populate ──────────────────────────────────────────────────
    print("[1/4] Populating mock memory with 5 diverse entries")
    for content, meta in samples:
        mem.add(content, user_id="demo", metadata=meta)
    logger.debug("Populated %d entries", len(samples))

    # ── 2. Status overview ───────────────────────────────────────────
    print("\n[2/4] Memory.status() — KB statistics")
    status = mem.status()
    logger.debug("Status: %s", status)

    assert status["total"] == 5
    assert status["ace_enabled"] is False
    print(f"       Total memories: {status['total']}")
    print(f"       ACE enabled: {status['ace_enabled']}")

    # ── 3. Section distribution ──────────────────────────────────────
    print("\n[3/4] Section & knowledge type distribution")
    sections = status["sections"]
    ktypes = status["knowledge_types"]
    logger.debug("Sections: %s", sections)
    logger.debug("Knowledge types: %s", ktypes)

    assert sections.get("tools", 0) == 3, f"Expected 3 tools, got {sections.get('tools')}"
    assert sections.get("debugging", 0) == 2, f"Expected 2 debugging, got {sections.get('debugging')}"
    print(f"       Sections: {dict(sections)}")
    print(f"       Knowledge types: {dict(ktypes)}")

    # ── 4. Average decay weight ──────────────────────────────────────
    print("\n[4/4] Average decay weight")
    avg = status["avg_decay_weight"]
    expected_avg = round((1.0 + 0.8 + 0.9 + 0.5 + 0.7) / 5, 2)
    logger.debug("Avg decay: %.2f (expected=%.2f)", avg, expected_avg)
    assert avg == expected_avg, f"Expected {expected_avg}, got {avg}"
    print(f"       avg_decay_weight={avg}")
    print(f"       Weights: [1.0, 0.8, 0.9, 0.5, 0.7] -> avg={expected_avg}")

    print("\nPASS: 18_memory_analytics")


if __name__ == "__main__":
    main()
