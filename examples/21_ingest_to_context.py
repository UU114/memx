"""Demo 21: Ingest-to-Context Full Pipeline — end-to-end cross-module data flow.

Modules exercised (6 modules cooperating):
  - PrivacySanitizer: strip PII from raw input
  - ReflectorEngine: extract CandidateBullets from sanitized interaction
  - BulletFactory: serialize bullets to mem0 metadata format
  - Memory (mock): store and retrieve bullets
  - GeneratorEngine: hybrid L1-L3 search across stored bullets
  - TokenBudgetTrimmer: trim results within token budget
  - CLIPreInferenceHook._format: render results for LLM context injection

Data flow:
  Raw interaction (with PII) → Sanitize → Reflect → Serialize → Store
  → Load as BulletForSearch → Hybrid search → Trim → Format (XML/MD/Plain)
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone

from examples._mock_backend import create_mock_memory
from memx.config import ReflectorConfig, RetrievalConfig
from memx.engines.generator.engine import BulletForSearch, GeneratorEngine
from memx.engines.generator.metadata_matcher import MetadataInfo
from memx.engines.reflector.engine import ReflectorEngine
from memx.integration.cli_hooks import CLIPreInferenceHook
from memx.privacy.sanitizer import PrivacySanitizer
from memx.types import BulletMetadata, InteractionEvent
from memx.utils.bullet_factory import BulletFactory
from memx.utils.token_counter import TokenBudgetTrimmer

logger = logging.getLogger(__name__)

NOW = datetime.now(timezone.utc)


def main() -> None:
    mem = create_mock_memory(ace_enabled=False)

    # ═════ Stage 1: Sanitize raw input containing PII ══════════════════
    print("=" * 60)
    print("  Stage 1: SANITIZE — Strip PII from raw interaction")
    print("=" * 60)

    sanitizer = PrivacySanitizer()

    raw_user = (
        "Error: connection refused on postgres://admin:s3cret_p@ss@db.example.com:5432/mydb. "
        "My API key is sk-proj-ABCDEFGHIJKLMNOPQRST1234567890abcdef. "
        "The config file is at C:\\Users\\JohnDoe\\project\\.env"
    )
    raw_assistant = (
        "The connection error means the database isn't accepting connections. "
        "Check if PostgreSQL is running: systemctl status postgresql. "
        "Also verify your .env has the correct DB_HOST and DB_PORT. "
        "Never hardcode your API key sk-proj-ABCDEFGHIJKLMNOPQRST1234567890abcdef in source code."
    )

    user_result = sanitizer.sanitize(raw_user)
    asst_result = sanitizer.sanitize(raw_assistant)

    logger.debug("Sanitize user: modified=%s, filtered=%d items",
                 user_result.was_modified, len(user_result.filtered_items))
    logger.debug("Sanitize asst: modified=%s, filtered=%d items",
                 asst_result.was_modified, len(asst_result.filtered_items))

    assert user_result.was_modified, "User message should have PII redacted"
    assert asst_result.was_modified, "Assistant message should have PII redacted"
    assert "s3cret_p@ss" not in user_result.clean_content
    assert "JohnDoe" not in user_result.clean_content

    print(f"\n  User PII redacted: {len(user_result.filtered_items)} item(s)")
    for fi in user_result.filtered_items:
        print(f"    pattern={fi.pattern_name}, snippet={fi.snippet}")
    print(f"  Assistant PII redacted: {len(asst_result.filtered_items)} item(s)")

    # ═════ Stage 2: Reflect — Extract bullets from sanitized interaction ═
    print(f"\n{'=' * 60}")
    print("  Stage 2: REFLECT — Extract knowledge bullets")
    print("=" * 60)

    reflector = ReflectorEngine(
        config=ReflectorConfig(mode="rules", min_score=20.0),
        sanitizer=None,  # Already sanitized
    )

    event = InteractionEvent(
        user_message=user_result.clean_content,
        assistant_message=asst_result.clean_content,
    )
    candidates = reflector.reflect(event)

    logger.debug("Reflector produced %d candidates from sanitized input", len(candidates))
    assert len(candidates) >= 1, f"Expected >=1 bullet, got {len(candidates)}"

    print(f"\n  Extracted {len(candidates)} bullet(s):")
    for c in candidates:
        print(f"    section={c.section.value}, type={c.knowledge_type.value}, "
              f"score={c.instructivity_score:.1f}")
        print(f"    content: {c.content[:80]}...")
        # Verify no PII leaked into bullets
        assert "s3cret" not in c.content, "PII leaked into bullet content!"
        assert "JohnDoe" not in c.content, "PII leaked into bullet content!"

    print("  PII leak check: CLEAN (no secrets in extracted bullets)")

    # ═════ Stage 3: Serialize & Store — BulletFactory → mem0 ════════════
    print(f"\n{'=' * 60}")
    print("  Stage 3: SERIALIZE & STORE — BulletFactory → mem0")
    print("=" * 60)

    stored_ids = []
    for i, c in enumerate(candidates):
        bullet_meta = BulletMetadata(
            section=c.section,
            knowledge_type=c.knowledge_type,
            instructivity_score=c.instructivity_score,
            related_tools=c.related_tools,
            key_entities=c.key_entities,
            tags=c.tags,
            scope="project:demo21",
        )
        mem0_meta = BulletFactory.to_mem0_metadata(bullet_meta)
        logger.debug("BulletFactory.to_mem0_metadata[%d]: keys=%s", i, list(mem0_meta.keys()))

        result = mem.add(c.content, user_id="dev1", metadata=mem0_meta)
        stored_id = result.get("id", f"bullet-{i}")
        stored_ids.append(stored_id)
        logger.debug("Stored bullet %s -> id=%s", i, stored_id)

    print(f"\n  Stored {len(stored_ids)} bullet(s) in mock mem0")

    # ═════ Stage 4: Load & Search — GeneratorEngine hybrid retrieval ════
    print(f"\n{'=' * 60}")
    print("  Stage 4: LOAD & SEARCH — Hybrid retrieval (L1-L3)")
    print("=" * 60)

    # Load bullets back from mem0 and convert to BulletForSearch
    raw = mem.get_all(user_id="dev1")
    search_bullets: list[BulletForSearch] = []
    for entry in raw.get("results", []):
        meta = entry.get("metadata", {})
        # Round-trip: from_mem0_payload to verify serialization
        reconstructed = BulletFactory.from_mem0_payload(entry)
        logger.debug("Reconstructed metadata: section=%s, tools=%s",
                     reconstructed.section, reconstructed.related_tools)

        search_bullets.append(BulletForSearch(
            bullet_id=entry["id"],
            content=entry["memory"],
            metadata=MetadataInfo(
                related_tools=reconstructed.related_tools,
                key_entities=reconstructed.key_entities,
                tags=reconstructed.tags,
            ),
            created_at=NOW,
            decay_weight=1.0,
            scope=reconstructed.scope,
        ))

    logger.debug("Loaded %d bullets for search", len(search_bullets))

    gen = GeneratorEngine(config=RetrievalConfig(keyword_weight=0.8, semantic_weight=0.2))
    results = gen.search("postgresql connection refused", search_bullets, limit=5)
    logger.debug("GeneratorEngine search -> %d results", len(results))

    assert len(results) > 0, "Should find relevant results"
    print(f"\n  Query: 'postgresql connection refused'")
    print(f"  Found {len(results)} result(s):")
    for r in results:
        print(f"    [{r.final_score:.4f}] {r.content[:70]}...")

    # ═════ Stage 5: Trim — TokenBudgetTrimmer ═══════════════════════════
    print(f"\n{'=' * 60}")
    print("  Stage 5: TRIM — Token budget enforcement")
    print("=" * 60)

    trimmer = TokenBudgetTrimmer(token_budget=100, max_results=3)
    trimmed = trimmer.trim(results)
    logger.debug("Trimmer: %d -> %d results (budget=100)", len(results), len(trimmed))

    print(f"\n  Before trim: {len(results)} results")
    print(f"  After trim:  {len(trimmed)} results (budget=100 tokens)")
    assert len(trimmed) >= 1, "At least 1 result guaranteed"

    # ═════ Stage 6: Format — Context injection for LLM ══════════════════
    print(f"\n{'=' * 60}")
    print("  Stage 6: FORMAT — Context injection (XML, Markdown, Plain)")
    print("=" * 60)

    # Convert ScoredBullet to the dict format CLIPreInferenceHook expects
    format_input = [
        {
            "id": r.bullet_id,
            "memory": r.content,
            "score": r.final_score,
            "metadata": r.metadata,
        }
        for r in trimmed
    ]

    for template in ("xml", "markdown", "plain"):
        rendered = CLIPreInferenceHook._format(format_input, template)
        logger.debug("Format '%s': %d chars", template, len(rendered))
        print(f"\n  [{template.upper()}] ({len(rendered)} chars):")
        # Show first 3 lines
        for line in rendered.split("\n")[:3]:
            print(f"    {line}")
        if len(rendered.split("\n")) > 3:
            print(f"    ...")

    # ═════ Final validation ═════════════════════════════════════════════
    print(f"\n{'=' * 60}")
    print("  VALIDATION — Cross-module integrity checks")
    print("=" * 60)

    # Check: no PII anywhere in the final output
    for r in trimmed:
        assert "s3cret" not in r.content, "PII in final output!"
        assert "JohnDoe" not in r.content, "PII in final output!"
    print("\n  PII check:       CLEAN (no PII in final context)")

    # Check: data survived full round-trip (sanitize→reflect→serialize→store→load→search)
    print(f"  Round-trip:      {len(candidates)} bullets → {len(stored_ids)} stored → {len(results)} found")
    print(f"  Token trimming:  {len(results)} → {len(trimmed)} within budget")
    print(f"  Format outputs:  XML, Markdown, Plain all generated")

    print("\nPASS: 21_ingest_to_context")


if __name__ == "__main__":
    main()
