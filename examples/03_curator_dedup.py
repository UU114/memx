"""Demo 03: Curator Deduplication — Insert/Merge/Skip decisions."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memorus.config import CuratorConfig
from memorus.engines.curator.engine import CuratorEngine, ExistingBullet
from memorus.types import BulletSection, CandidateBullet, KnowledgeType


def main() -> None:
    curator = CuratorEngine(config=CuratorConfig(similarity_threshold=0.8))

    existing = [
        ExistingBullet(
            bullet_id="ex-001",
            content="Use pytest -x to stop on first failure",
            scope="global",
        ),
        ExistingBullet(
            bullet_id="ex-002",
            content="Docker build cache is invalidated by COPY order",
            scope="global",
        ),
    ]

    candidates = [
        # Should INSERT: completely new topic
        CandidateBullet(
            content="Use cargo clippy for Rust linting before building",
            section=BulletSection.TOOLS,
            knowledge_type=KnowledgeType.METHOD,
            instructivity_score=70.0,
        ),
        # Should SKIP or MERGE: very similar to existing ex-001
        CandidateBullet(
            content="Use pytest -x to stop on first failure for faster debugging",
            section=BulletSection.DEBUGGING,
            knowledge_type=KnowledgeType.METHOD,
            instructivity_score=65.0,
        ),
        # Should INSERT: different scope
        CandidateBullet(
            content="Use black for auto-formatting Python code",
            section=BulletSection.TOOLS,
            knowledge_type=KnowledgeType.TRICK,
            instructivity_score=60.0,
        ),
    ]

    result = curator.curate(candidates, existing)

    print(f"[1/3] Candidates submitted:  {len(candidates)}")
    print(f"[2/3] Decision breakdown:")
    print(f"       INSERT: {len(result.to_add)} candidate(s)")
    for b in result.to_add:
        print(f"         -> {b.content[:60]}")
    print(f"       MERGE:  {len(result.to_merge)} candidate(s)")
    for mc in result.to_merge:
        print(f"         -> candidate: {mc.candidate.content[:40]}...")
        print(f"            existing:  {mc.existing.content[:40]}... (sim={mc.similarity:.2f})")
    print(f"       SKIP:   {len(result.to_skip)} candidate(s)")
    for b in result.to_skip:
        print(f"         -> {b.content[:60]}")

    # Verify totals
    total = len(result.to_add) + len(result.to_merge) + len(result.to_skip)
    assert total == len(candidates), f"Expected {len(candidates)}, got {total}"
    print(f"\n[3/3] Total accounted: {total} == {len(candidates)} candidates")

    print("\nPASS: 03_curator_dedup")


if __name__ == "__main__":
    main()
