"""Demo 16: BulletFactory — metadata serialization/deserialization round-trip.

Demonstrates:
  - BulletFactory.create() -> BulletMetadata construction
  - to_mem0_metadata() -> memorus_-prefixed dict (enum->str, list->JSON, datetime->ISO)
  - from_mem0_payload() -> BulletMetadata reconstruction from mem0 dict
  - Round-trip preservation: original == deserialized
  - merge_metadata() -> partial update merging
  - from_export_payload() -> import reconstruction
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memorus.types import BulletMetadata, BulletSection, KnowledgeType, SourceType
from memorus.utils.bullet_factory import BulletFactory

logger = logging.getLogger(__name__)


def main() -> None:
    # ── 1. Create a bullet with metadata ─────────────────────────────
    print("[1/5] BulletFactory.create() — construct Bullet with metadata")
    bullet = BulletFactory.create(
        "Use pytest -x for fast failure detection",
        section=BulletSection.DEBUGGING,
        knowledge_type=KnowledgeType.METHOD,
        instructivity_score=85.0,
        related_tools=["pytest"],
        key_entities=["Python"],
        tags=["testing", "workflow"],
        scope="project:backend",
        source_type=SourceType.INTERACTION,
    )
    meta: BulletMetadata = bullet["metadata"]
    logger.debug("Created bullet: content=%r section=%s type=%s score=%.1f",
                 bullet["content"], meta.section, meta.knowledge_type,
                 meta.instructivity_score)

    assert bullet["content"] == "Use pytest -x for fast failure detection"
    assert meta.section == BulletSection.DEBUGGING
    assert meta.related_tools == ["pytest"]
    print(f"       content='{bullet['content']}'")
    print(f"       section={meta.section.value}, type={meta.knowledge_type.value}")
    print(f"       tools={meta.related_tools}, entities={meta.key_entities}")

    # ── 2. Serialize to mem0 payload ─────────────────────────────────
    print("\n[2/5] to_mem0_metadata() — serialize to memorus_-prefixed dict")
    mem0_meta = BulletFactory.to_mem0_metadata(meta)
    logger.debug("Serialized keys: %s", list(mem0_meta.keys()))

    assert all(k.startswith("memorus_") for k in mem0_meta), "All keys must have memorus_ prefix"
    assert mem0_meta["memorus_section"] == "debugging"
    assert mem0_meta["memorus_knowledge_type"] == "method"
    assert isinstance(mem0_meta["memorus_related_tools"], str), "Lists should be JSON strings"

    print(f"       Keys: {list(mem0_meta.keys())[:6]}...")
    print(f"       memorus_section='{mem0_meta['memorus_section']}'")
    print(f"       memorus_related_tools='{mem0_meta['memorus_related_tools']}' (JSON string)")

    # ── 3. Deserialize from mem0 payload ─────────────────────────────
    print("\n[3/5] from_mem0_payload() — deserialize back to BulletMetadata")
    payload = {"metadata": mem0_meta}
    restored: BulletMetadata = BulletFactory.from_mem0_payload(payload)
    logger.debug("Restored: section=%s type=%s tools=%s",
                 restored.section, restored.knowledge_type, restored.related_tools)

    assert restored.section == meta.section
    assert restored.knowledge_type == meta.knowledge_type
    assert restored.instructivity_score == meta.instructivity_score
    assert restored.related_tools == meta.related_tools
    assert restored.key_entities == meta.key_entities
    assert restored.tags == meta.tags
    assert restored.scope == meta.scope
    print(f"       section={restored.section.value} (match={restored.section == meta.section})")
    print(f"       tools={restored.related_tools} (match={restored.related_tools == meta.related_tools})")
    print(f"       Round-trip: OK")

    # ── 4. merge_metadata() — partial update ─────────────────────────
    print("\n[4/5] merge_metadata() — partial update")
    updated = BulletFactory.merge_metadata(meta, {
        "instructivity_score": 95.0,
        "recall_count": 5,
        "tags": ["testing", "workflow", "ci"],
    })
    logger.debug("Merged: score=%.1f->%.1f, recall=%d, tags=%s",
                 meta.instructivity_score, updated.instructivity_score,
                 updated.recall_count, updated.tags)

    assert updated.instructivity_score == 95.0, "Score should be updated"
    assert updated.recall_count == 5, "Recall count should be updated"
    assert updated.tags == ["testing", "workflow", "ci"], "Tags should be updated"
    assert updated.section == meta.section, "Section should be preserved"
    print(f"       score: {meta.instructivity_score} -> {updated.instructivity_score}")
    print(f"       recall_count: {meta.recall_count} -> {updated.recall_count}")
    print(f"       tags: {meta.tags} -> {updated.tags}")
    print(f"       section: unchanged ({updated.section.value})")

    # ── 5. from_export_payload() — import reconstruction ─────────────
    print("\n[5/5] from_export_payload() — reconstruct from export")
    export_entry = {
        "id": "abc123",
        "memory": "Use ruff check for linting",
        "metadata": {
            "memorus_section": "tools",
            "memorus_knowledge_type": "method",
            "memorus_instructivity_score": 70.0,
            "memorus_related_tools": '["ruff"]',
            "memorus_scope": "global",
        },
    }
    reconstructed = BulletFactory.from_export_payload(export_entry)
    r_meta: BulletMetadata = reconstructed["metadata"]
    logger.debug("Reconstructed: content=%r section=%s tools=%s",
                 reconstructed["content"], r_meta.section, r_meta.related_tools)

    assert reconstructed["content"] == "Use ruff check for linting"
    assert r_meta.section == BulletSection.TOOLS
    assert r_meta.related_tools == ["ruff"]
    print(f"       content='{reconstructed['content']}'")
    print(f"       section={r_meta.section.value}, tools={r_meta.related_tools}")

    print("\nPASS: 16_bullet_factory")


if __name__ == "__main__":
    main()
