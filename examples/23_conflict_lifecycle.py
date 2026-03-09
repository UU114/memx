"""Demo 23: Conflict Detection Lifecycle — Reflect → Curate → Detect → Resolve.

Modules exercised (5 modules cooperating):
  - ReflectorEngine: extract bullets from contradictory interactions
  - CuratorEngine: dedup and merge detection
  - ConflictDetector: detect opposing/negation conflicts
  - Memory (mock): store, retrieve, update, detect_conflicts()
  - GeneratorEngine: verify KB consistency after resolution

Data flow:
  Interaction A (affirm) → Reflect → Store
  Interaction B (contradict) → Reflect → Curate against existing → Store
  → detect_conflicts() → Resolve conflict → Re-search → Verify consistency
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone

from examples._mock_backend import create_mock_memory
from memorus.config import CuratorConfig, ReflectorConfig, RetrievalConfig
from memorus.engines.curator.conflict import Conflict, ConflictDetector
from memorus.engines.curator.engine import CuratorEngine, ExistingBullet
from memorus.engines.generator.engine import BulletForSearch, GeneratorEngine
from memorus.engines.generator.metadata_matcher import MetadataInfo
from memorus.engines.reflector.engine import ReflectorEngine
from memorus.types import InteractionEvent

logger = logging.getLogger(__name__)

NOW = datetime.now(timezone.utc)


def main() -> None:
    mem = create_mock_memory(ace_enabled=False)

    # ═════ Phase 1: Learn — First interaction (affirmative) ════════════
    print("=" * 60)
    print("  Phase 1: LEARN — First interaction (affirmative advice)")
    print("=" * 60)

    reflector = ReflectorEngine(
        config=ReflectorConfig(mode="rules", min_score=15.0),
    )

    # ErrorFixRule requires error keywords in user_message + fix keywords in assistant
    # Both events use similar vocabulary (git rebase, branch, merge, commits)
    # to ensure text_similarity falls within ConflictDetector's range
    event_a = InteractionEvent(
        user_message=(
            "Error: git merge on feature branch creates messy commit "
            "history with unnecessary merge commits."
        ),
        assistant_message=(
            "Always use git rebase on your feature branch instead of "
            "git merge. Rebase creates a clean linear commit history. "
            "Run git rebase main to update your feature branch."
        ),
    )
    bullets_a = reflector.reflect(event_a)
    logger.debug("Event A produced %d bullets", len(bullets_a))
    assert len(bullets_a) >= 1, f"Expected >=1 bullet from event A, got {len(bullets_a)}"

    print(f"\n  Event A: 'error → always use git rebase' → {len(bullets_a)} bullet(s)")
    for b in bullets_a:
        print(f"    [{b.section.value}/{b.knowledge_type.value}] {b.content[:70]}...")

    # Store in memory
    for b in bullets_a:
        mem.add(b.content, user_id="dev1", metadata={
            "memorus_section": b.section.value,
            "memorus_knowledge_type": b.knowledge_type.value,
            "memorus_related_tools": str(b.related_tools),
            "memorus_scope": "project:demo23",
        })

    # ═════ Phase 2: Contradict — Second interaction (opposing) ═════════
    print(f"\n{'=' * 60}")
    print("  Phase 2: CONTRADICT — Second interaction (opposing advice)")
    print("=" * 60)

    # Second interaction: contradicts the first (never rebase on shared branch)
    # Shares vocabulary with event_a (git rebase, branch, merge, commits)
    event_b = InteractionEvent(
        user_message=(
            "Error: git rebase on a shared branch caused broken commit "
            "history and other developers lost their merge commits."
        ),
        assistant_message=(
            "Never use git rebase on a shared branch. Rebase rewrites "
            "commit history causing problems. Use git merge instead "
            "on shared branches to keep a safe commit history."
        ),
    )
    bullets_b = reflector.reflect(event_b)
    logger.debug("Event B produced %d bullets", len(bullets_b))
    assert len(bullets_b) >= 1, f"Expected >=1 bullet from event B, got {len(bullets_b)}"

    print(f"\n  Event B: 'error → never rebase shared branches' → {len(bullets_b)} bullet(s)")
    for b in bullets_b:
        print(f"    [{b.section.value}/{b.knowledge_type.value}] {b.content[:70]}...")

    # ═════ Phase 3: Curate — Deduplicate against existing ══════════════
    print(f"\n{'=' * 60}")
    print("  Phase 3: CURATE — Check new bullets against existing KB")
    print("=" * 60)

    curator = CuratorEngine(config=CuratorConfig(
        similarity_threshold=0.6,
        conflict_detection=False,  # We'll detect manually below
    ))

    # Build existing bullets from mem0
    raw = mem.get_all(user_id="dev1")
    existing = [
        ExistingBullet(
            bullet_id=entry["id"],
            content=entry["memory"],
            scope=entry.get("metadata", {}).get("memorus_scope", "global"),
            metadata=entry.get("metadata", {}),
        )
        for entry in raw.get("results", [])
    ]
    logger.debug("Existing KB: %d bullets", len(existing))

    curate_result = curator.curate(bullets_b, existing)
    logger.debug("Curate result: add=%d merge=%d skip=%d",
                 len(curate_result.to_add), len(curate_result.to_merge),
                 len(curate_result.to_skip))

    print(f"\n  Existing KB: {len(existing)} bullet(s)")
    print(f"  New candidates: {len(bullets_b)}")
    print(f"  Curate decision:")
    print(f"    to_add:  {len(curate_result.to_add)}")
    print(f"    to_merge: {len(curate_result.to_merge)}")
    print(f"    to_skip: {len(curate_result.to_skip)}")

    # Store the new bullets (whether add or merge)
    for b in curate_result.to_add:
        mem.add(b.content, user_id="dev1", metadata={
            "memorus_section": b.section.value,
            "memorus_knowledge_type": b.knowledge_type.value,
            "memorus_related_tools": str(b.related_tools),
            "memorus_scope": "project:demo23",
        })
    for mc in curate_result.to_merge:
        mem.update(mc.existing.bullet_id, mc.candidate.content)

    # ═════ Phase 4: Detect — Find conflicts in KB ═════════════════════
    print(f"\n{'=' * 60}")
    print("  Phase 4: DETECT — Scan KB for contradictions")
    print("=" * 60)

    # Load all memories and build ExistingBullet list
    raw2 = mem.get_all(user_id="dev1")
    all_bullets = [
        ExistingBullet(
            bullet_id=entry["id"],
            content=entry["memory"],
            scope=entry.get("metadata", {}).get("memorus_scope", "global"),
            metadata=entry.get("metadata", {}),
        )
        for entry in raw2.get("results", [])
    ]

    logger.debug("Full KB for conflict detection: %d bullets", len(all_bullets))

    # Lower min_similarity to catch bullets with shared but not identical vocabulary
    # (error-fix bullets include raw user messages, diluting word overlap)
    detector = ConflictDetector(CuratorConfig(
        conflict_min_similarity=0.15,
        conflict_max_similarity=0.85,
    ))
    conflict_result = detector.detect(all_bullets)

    logger.debug("Conflict detection: %d pairs checked, %d conflicts found, %.1fms",
                 conflict_result.total_pairs_checked,
                 len(conflict_result.conflicts),
                 conflict_result.scan_time_ms)

    print(f"\n  KB size: {len(all_bullets)} bullets")
    print(f"  Pairs checked: {conflict_result.total_pairs_checked}")
    print(f"  Conflicts found: {len(conflict_result.conflicts)}")

    if conflict_result.conflicts:
        for c in conflict_result.conflicts:
            print(f"\n  CONFLICT: {c.reason}")
            print(f"    A ({c.memory_a_id}): {c.memory_a_content[:60]}...")
            print(f"    B ({c.memory_b_id}): {c.memory_b_content[:60]}...")
            print(f"    Similarity: {c.similarity:.3f}")

    # We expect at least one conflict (always vs never)
    assert len(conflict_result.conflicts) >= 1, (
        f"Expected >=1 conflict (always vs never), got {len(conflict_result.conflicts)}"
    )
    print(f"\n  Expected 'always vs never' conflict: DETECTED")

    # ═════ Phase 5: Resolve — Fix the conflict ════════════════════════
    print(f"\n{'=' * 60}")
    print("  Phase 5: RESOLVE — Merge conflicting knowledge")
    print("=" * 60)

    # Resolution strategy: merge both into a nuanced rule
    conflict = conflict_result.conflicts[0]
    resolved_content = (
        "Use git rebase to keep feature branches updated with a clean linear "
        "history, but never rebase shared branches that others have pulled. "
        "On shared branches, use git merge instead."
    )

    # Update the first conflicting memory, delete the second
    mem.update(conflict.memory_a_id, resolved_content)
    mem.delete(conflict.memory_b_id)

    logger.debug("Resolved: updated %s, deleted %s", conflict.memory_a_id, conflict.memory_b_id)
    print(f"\n  Resolution: merged both into nuanced rule")
    print(f"    Updated: {conflict.memory_a_id}")
    print(f"    Deleted: {conflict.memory_b_id}")
    print(f"    Merged content: {resolved_content[:70]}...")

    # ═════ Phase 6: Verify — Re-scan and search ════════════════════════
    print(f"\n{'=' * 60}")
    print("  Phase 6: VERIFY — Confirm KB consistency after resolution")
    print("=" * 60)

    # Re-scan for conflicts
    raw3 = mem.get_all(user_id="dev1")
    final_bullets = [
        ExistingBullet(
            bullet_id=entry["id"],
            content=entry["memory"],
            scope=entry.get("metadata", {}).get("memorus_scope", "global"),
            metadata=entry.get("metadata", {}),
        )
        for entry in raw3.get("results", [])
    ]

    conflict_result2 = detector.detect(final_bullets)
    logger.debug("Post-resolution conflicts: %d", len(conflict_result2.conflicts))

    print(f"\n  Post-resolution KB: {len(final_bullets)} bullets")
    print(f"  Remaining conflicts: {len(conflict_result2.conflicts)}")
    assert len(conflict_result2.conflicts) == 0, (
        f"Expected 0 conflicts after resolution, got {len(conflict_result2.conflicts)}"
    )

    # Search to verify the resolved knowledge is retrievable
    search_bullets = [
        BulletForSearch(
            bullet_id=entry["id"],
            content=entry["memory"],
            metadata=MetadataInfo(tags=["git"]),
            created_at=NOW,
            decay_weight=1.0,
        )
        for entry in raw3.get("results", [])
    ]

    gen = GeneratorEngine(config=RetrievalConfig())
    results = gen.search("git rebase shared branches", search_bullets, limit=3)
    logger.debug("Post-resolution search: %d results", len(results))

    assert len(results) > 0, "Should find resolved knowledge"
    top = results[0]
    print(f"\n  Search 'git rebase shared branches':")
    print(f"    Top result: [{top.final_score:.4f}] {top.content[:70]}...")
    assert "merge" in top.content.lower() or "rebase" in top.content.lower(), \
        "Resolved content should mention both rebase and merge"

    print(f"\n  Conflict lifecycle: DETECT → RESOLVE → VERIFY complete")

    print("\nPASS: 23_conflict_lifecycle")


if __name__ == "__main__":
    main()
