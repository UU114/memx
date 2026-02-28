"""Demo 24: Privacy-Preserving Knowledge Flow — PII never reaches the KB or context.

Modules exercised (5 modules cooperating):
  - PrivacySanitizer: strip multiple PII categories (API keys, DB creds, paths)
  - ReflectorEngine: extract with sanitizer integrated (constructor injection)
  - BulletFactory: serialize sanitized bullets
  - GeneratorEngine: search across sanitized KB
  - CLIPreInferenceHook._format: final context output verified PII-free

Data flow:
  Raw interaction with PII → Reflector(sanitizer=PrivacySanitizer)
  → Sanitized CandidateBullets → Serialize → Store → Search → Format
  → Verify: no PII at any stage
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
from memx.types import InteractionEvent
from memx.utils.bullet_factory import BulletFactory, BulletMetadata

logger = logging.getLogger(__name__)

NOW = datetime.now(timezone.utc)

# Sensitive strings that MUST NOT appear in any output
PII_MARKERS = [
    "sk-proj-TESTKEY12345678901234567890abcdef",  # OpenAI key
    "ghp_TestGitHubToken12345678901234",           # GitHub token
    "admin:supersecret123",                         # DB password
    "JaneDoe",                                      # Username in path
    "AKIAIOSFODNN7EXAMPLE",                         # AWS key
]


def _assert_no_pii(text: str, context: str) -> None:
    """Assert no PII markers appear in text."""
    for marker in PII_MARKERS:
        assert marker not in text, f"PII leak in {context}: found '{marker[:20]}...'"


def main() -> None:
    mem = create_mock_memory(ace_enabled=False)

    # ═════ Phase 1: Build PII-rich interactions ═══════════════════════
    print("=" * 60)
    print("  Phase 1: PII-RICH INTERACTIONS — Multiple secret types")
    print("=" * 60)

    interactions = [
        InteractionEvent(
            user_message=(
                "Error: authentication failed when calling OpenAI API. "
                "My key is sk-proj-TESTKEY12345678901234567890abcdef and I set it in "
                "C:\\Users\\JaneDoe\\projects\\myapp\\.env file."
            ),
            assistant_message=(
                "The authentication error means your API key is invalid or expired. "
                "Generate a new key at platform.openai.com. Store it in .env as "
                "OPENAI_API_KEY=sk-proj-TESTKEY12345678901234567890abcdef and load with dotenv."
            ),
        ),
        InteractionEvent(
            user_message=(
                "I can't push to GitHub. My token ghp_TestGitHubToken12345678901234 "
                "gives 403 Forbidden. The repo is at /home/JaneDoe/work/project."
            ),
            assistant_message=(
                "403 means your token doesn't have push permissions. "
                "Create a new fine-grained token at github.com/settings/tokens "
                "with 'Contents: Read and write' permission. "
                "Set as: git remote set-url origin https://ghp_TestGitHubToken12345678901234@github.com/user/repo"
            ),
        ),
        InteractionEvent(
            user_message=(
                "Error: connection refused to postgres://admin:supersecret123@db.prod.example.com:5432/app. "
                "AWS access key AKIAIOSFODNN7EXAMPLE is configured."
            ),
            assistant_message=(
                "The connection refused error means PostgreSQL isn't accepting connections. "
                "Check security group settings in AWS console. Verify the DB endpoint "
                "postgres://admin:supersecret123@db.prod.example.com matches your RDS instance."
            ),
        ),
    ]

    print(f"\n  Prepared {len(interactions)} interactions with:")
    print(f"    - OpenAI API key")
    print(f"    - GitHub PAT token")
    print(f"    - DB credentials")
    print(f"    - AWS access key")
    print(f"    - User paths (Windows + Unix)")

    # ═════ Phase 2: Reflect with integrated sanitizer ═════════════════
    print(f"\n{'=' * 60}")
    print("  Phase 2: REFLECT — Sanitizer integrated in ReflectorEngine")
    print("=" * 60)

    sanitizer = PrivacySanitizer()
    reflector = ReflectorEngine(
        config=ReflectorConfig(mode="rules", min_score=15.0),
        sanitizer=sanitizer,  # Sanitizer runs inside reflect()
    )

    all_bullets = []
    for i, event in enumerate(interactions, 1):
        bullets = reflector.reflect(event)
        logger.debug("Interaction %d: %d bullets extracted", i, len(bullets))

        print(f"\n  [{i}/{len(interactions)}] → {len(bullets)} bullet(s)")
        for b in bullets:
            # Verify PII was stripped BEFORE bullet creation
            _assert_no_pii(b.content, f"bullet from interaction {i}")
            logger.debug("  Bullet PII check OK: %s", b.content[:60])
            print(f"    [{b.knowledge_type.value}] {b.content[:70]}...")
            if b.related_tools:
                print(f"    tools: {b.related_tools}")
        all_bullets.extend(bullets)

    total = len(all_bullets)
    assert total >= 3, f"Expected >=3 bullets from {len(interactions)} interactions, got {total}"
    print(f"\n  Total bullets: {total} (all PII-clean)")

    # ═════ Phase 3: Serialize & Store ═════════════════════════════════
    print(f"\n{'=' * 60}")
    print("  Phase 3: SERIALIZE & STORE — BulletFactory round-trip")
    print("=" * 60)

    for i, b in enumerate(all_bullets):
        meta = BulletMetadata(
            section=b.section,
            knowledge_type=b.knowledge_type,
            instructivity_score=b.instructivity_score,
            related_tools=b.related_tools,
            key_entities=b.key_entities,
            tags=b.tags,
            scope="project:demo24",
        )
        mem0_meta = BulletFactory.to_mem0_metadata(meta)

        # Verify: serialized metadata contains no PII
        meta_str = str(mem0_meta)
        _assert_no_pii(meta_str, f"mem0_metadata[{i}]")
        logger.debug("Serialized metadata PII check OK for bullet %d", i)

        mem.add(b.content, user_id="dev1", metadata=mem0_meta)

    print(f"\n  Stored {total} bullets (all metadata PII-clean)")

    # ═════ Phase 4: Search — Verify no PII in search results ═════════
    print(f"\n{'=' * 60}")
    print("  Phase 4: SEARCH — Verify results are PII-free")
    print("=" * 60)

    raw = mem.get_all(user_id="dev1")
    search_bullets = []
    for entry in raw.get("results", []):
        reconstructed = BulletFactory.from_mem0_payload(entry)
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

    gen = GeneratorEngine(config=RetrievalConfig(keyword_weight=0.8, semantic_weight=0.2))

    queries = [
        "openai api key authentication failed",
        "github push 403 forbidden token",
        "postgres connection refused aws",
    ]

    all_results = []
    for query in queries:
        results = gen.search(query, search_bullets, limit=3)
        logger.debug("Query '%s' -> %d results", query, len(results))
        print(f"\n  Query: '{query}' → {len(results)} result(s)")
        for r in results:
            _assert_no_pii(r.content, f"search result for '{query}'")
            print(f"    [{r.final_score:.4f}] {r.content[:65]}...")
        all_results.extend(results)

    print(f"\n  All search results: PII-FREE")

    # ═════ Phase 5: Format — Final context injection check ════════════
    print(f"\n{'=' * 60}")
    print("  Phase 5: FORMAT — Context injection PII verification")
    print("=" * 60)

    # Use top results for formatting
    format_input = [
        {"id": r.bullet_id, "memory": r.content, "score": r.final_score, "metadata": r.metadata}
        for r in all_results[:5]
    ]

    for template in ("xml", "markdown", "plain"):
        rendered = CLIPreInferenceHook._format(format_input, template)
        _assert_no_pii(rendered, f"formatted output ({template})")
        logger.debug("Format '%s' PII check OK (%d chars)", template, len(rendered))
        print(f"\n  [{template.upper()}] ({len(rendered)} chars) PII check: CLEAN")
        # Show first 2 lines as sample
        for line in rendered.split("\n")[:2]:
            print(f"    {line}")

    # ═════ Summary ═════════════════════════════════════════════════════
    print(f"\n{'=' * 60}")
    print("  SUMMARY — Privacy pipeline integrity")
    print("=" * 60)

    print(f"\n  PII types tested: {len(PII_MARKERS)}")
    print(f"    OpenAI key, GitHub PAT, DB creds, AWS key, User paths")
    print(f"  Pipeline stages verified: 5")
    print(f"    Reflect → Serialize → Store → Search → Format")
    print(f"  Total PII checks passed: {total * 3 + len(all_results) + 3}")
    print(f"  Leak detections: 0")

    print("\nPASS: 24_privacy_pipeline")


if __name__ == "__main__":
    main()
