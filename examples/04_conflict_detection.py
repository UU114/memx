"""Demo 04: Conflict Detection — find contradictory memories (EN + ZH negation)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memorus.config import CuratorConfig
from memorus.engines.curator.conflict import ConflictDetector
from memorus.engines.curator.engine import ExistingBullet


def main() -> None:
    config = CuratorConfig(
        conflict_detection=True,
        conflict_min_similarity=0.3,
        conflict_max_similarity=0.85,
    )
    detector = ConflictDetector(config)

    memories = [
        # Pair 1: English contradiction (always vs never)
        ExistingBullet(
            bullet_id="m-001",
            content="Always use tabs for indentation in Python",
            scope="global",
        ),
        ExistingBullet(
            bullet_id="m-002",
            content="Never use tabs for indentation in Python, use spaces",
            scope="global",
        ),
        # Pair 2: Chinese negation (使用 vs 不要使用)
        ExistingBullet(
            bullet_id="m-003",
            content="Use print for debugging Python code",
            scope="global",
        ),
        ExistingBullet(
            bullet_id="m-004",
            content="不要使用 print for debugging, use logging instead",
            scope="global",
        ),
        # Non-conflicting memory
        ExistingBullet(
            bullet_id="m-005",
            content="Docker containers should have health checks configured",
            scope="global",
        ),
        # Pair 3: enable vs disable
        ExistingBullet(
            bullet_id="m-006",
            content="Enable strict mode in TypeScript tsconfig",
            scope="global",
        ),
        ExistingBullet(
            bullet_id="m-007",
            content="Disable strict mode in TypeScript for legacy projects",
            scope="global",
        ),
    ]

    result = detector.detect(memories)

    print(f"[1/3] Scanned {result.total_pairs_checked} pairs in {result.scan_time_ms:.1f}ms")
    print(f"[2/3] Found {len(result.conflicts)} conflict(s):")

    for i, c in enumerate(result.conflicts, 1):
        print(f"\n  Conflict #{i}:")
        print(f"    A ({c.memory_a_id}): {c.memory_a_content[:60]}")
        print(f"    B ({c.memory_b_id}): {c.memory_b_content[:60]}")
        print(f"    Similarity: {c.similarity:.2f}")
        print(f"    Reason: {c.reason}")

    # Should find at least the obvious always/never pair
    assert len(result.conflicts) >= 1, "Should detect at least 1 conflict"
    print(f"\n[3/3] Conflict detection verified ({len(result.conflicts)} found)")

    print("\nPASS: 04_conflict_detection")


if __name__ == "__main__":
    main()
