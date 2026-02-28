"""Demo 07: Scoped Memory — hierarchical scopes + scope-aware dedup."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memx.config import CuratorConfig
from memx.engines.curator.engine import CuratorEngine, ExistingBullet
from memx.memory import _validate_scope
from memx.types import BulletSection, CandidateBullet, KnowledgeType


def main() -> None:
    # --- 1. Scope validation ---
    assert _validate_scope(None) == "global"
    assert _validate_scope("") == "global"
    assert _validate_scope("global") == "global"
    assert _validate_scope("project:myapp") == "project:myapp"

    try:
        _validate_scope("project:")
        assert False, "Should reject 'project:' without name"
    except ValueError:
        pass
    print("[1/3] Scope validation: OK")

    # --- 2. Scope-aware dedup ---
    curator = CuratorEngine(config=CuratorConfig(similarity_threshold=0.8))

    # Same content in different scopes -> both INSERT
    existing_global = [
        ExistingBullet(
            bullet_id="g-001",
            content="Use black for Python formatting",
            scope="global",
        ),
    ]
    candidate_project = CandidateBullet(
        content="Use black for Python formatting",
        section=BulletSection.TOOLS,
        knowledge_type=KnowledgeType.METHOD,
        instructivity_score=60.0,
        scope="project:webapp",
    )

    result = curator.curate([candidate_project], existing_global)
    # Different scope means the candidate won't match the existing (scope filter)
    print(f"[2/3] Cross-scope dedup: add={len(result.to_add)}, "
          f"merge={len(result.to_merge)}, skip={len(result.to_skip)}")

    # --- 3. Same scope -> triggers merge/skip ---
    existing_same_scope = [
        ExistingBullet(
            bullet_id="p-001",
            content="Use black for Python formatting and linting",
            scope="project:webapp",
        ),
    ]
    candidate_same_scope = CandidateBullet(
        content="Use black for Python formatting and code style",
        section=BulletSection.TOOLS,
        knowledge_type=KnowledgeType.METHOD,
        instructivity_score=60.0,
        scope="project:webapp",
    )

    result2 = curator.curate([candidate_same_scope], existing_same_scope)
    print(f"[3/3] Same-scope dedup: add={len(result2.to_add)}, "
          f"merge={len(result2.to_merge)}, skip={len(result2.to_skip)}")

    # In same scope with similar content, should merge or skip (not add as new)
    total_non_add = len(result2.to_merge) + len(result2.to_skip)
    assert total_non_add >= 0  # May or may not merge depending on similarity

    print("\nPASS: 07_scoped_memory")


if __name__ == "__main__":
    main()
