"""Demo 20: End-to-End Scenario — project onboarding lifecycle.

Simulates a real-world developer lifecycle through the ACE pipeline:
  Phase 1: Onboarding — learn from error-fix interactions
  Phase 2: Retrieve  — search using hybrid retrieval (L1-L3 degraded)
  Phase 3: Decay     — time passes, decay weights drop
  Phase 4: Reinforce — frequent recall preserves important memories
  Phase 5: Status    — view KB analytics after the lifecycle
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta, timezone

from examples._mock_backend import create_mock_memory
from memorus.config import DecayConfig, RetrievalConfig
from memorus.engines.decay.engine import BulletDecayInfo, DecayEngine
from memorus.engines.generator.engine import BulletForSearch, GeneratorEngine
from memorus.engines.generator.metadata_matcher import MetadataInfo
from memorus.engines.reflector.engine import ReflectorEngine
from memorus.types import InteractionEvent

logger = logging.getLogger(__name__)

NOW = datetime.now(timezone.utc)


def main() -> None:
    mem = create_mock_memory(ace_enabled=False)
    reflector = ReflectorEngine()

    # ═════ Phase 1: Onboarding — Extract knowledge from interactions ═
    print("=" * 60)
    print("  Phase 1: ONBOARDING — Extract knowledge")
    print("=" * 60)

    interactions = [
        InteractionEvent(
            user_message=(
                "Error: 'fatal: refusing to merge unrelated histories' when I run "
                "git pull origin main."
            ),
            assistant_message=(
                "This happens when local and remote have no common ancestor. "
                "Use git pull origin main --allow-unrelated-histories to fix it."
            ),
        ),
        InteractionEvent(
            user_message=(
                "Error: pytest keeps saying 'ModuleNotFoundError: No module named myapp' "
                "even though my code is in the right directory."
            ),
            assistant_message=(
                "You need to install your package in development mode. Run "
                "pip install -e . from the project root. This adds your package "
                "to sys.path correctly."
            ),
        ),
        InteractionEvent(
            user_message="I found that cargo clippy is great for Rust linting.",
            assistant_message=(
                "Yes, cargo clippy catches common mistakes. Run cargo clippy -- -D warnings "
                "to treat all warnings as errors in CI."
            ),
        ),
    ]

    all_bullets = []
    for i, event in enumerate(interactions, 1):
        bullets = reflector.reflect(event)
        all_bullets.extend(bullets)
        logger.debug("Interaction %d -> %d bullet(s)", i, len(bullets))
        print(f"\n[{i}/3] Interaction -> {len(bullets)} bullet(s)")
        for b in bullets:
            print(f"       {b.section.value}/{b.knowledge_type.value}: "
                  f"{b.content[:60]}...")

    total_extracted = len(all_bullets)
    assert total_extracted >= 3, f"Expected >=3 bullets, got {total_extracted}"
    print(f"\n       Total extracted: {total_extracted} bullets")

    # Store in mock memory
    for b in all_bullets:
        mem.add(b.content, user_id="dev1", metadata={
            "memorus_section": b.section.value,
            "memorus_knowledge_type": b.knowledge_type.value,
            "memorus_instructivity_score": b.instructivity_score,
            "memorus_related_tools": str(b.related_tools),
            "memorus_scope": "project:onboarding",
            "memorus_decay_weight": 1.0,
        })

    # ═════ Phase 2: Retrieve — Hybrid search ═════════════════════════
    print(f"\n{'=' * 60}")
    print("  Phase 2: RETRIEVE — Hybrid search")
    print("=" * 60)

    search_bullets = []
    raw = mem.get_all(user_id="dev1")
    for entry in raw.get("results", []):
        meta = entry.get("metadata", {})
        tools_str = meta.get("memorus_related_tools", "[]")
        tools = []
        if isinstance(tools_str, str) and tools_str.startswith("["):
            try:
                import ast
                tools = ast.literal_eval(tools_str)
            except Exception:
                pass

        search_bullets.append(BulletForSearch(
            bullet_id=entry["id"],
            content=entry["memory"],
            metadata=MetadataInfo(
                related_tools=tools,
                tags=[meta.get("memorus_section", "general")],
            ),
            created_at=NOW,
            decay_weight=float(meta.get("memorus_decay_weight", 1.0)),
            scope=meta.get("memorus_scope", "global"),
        ))

    gen_engine = GeneratorEngine(config=RetrievalConfig(keyword_weight=0.8, semantic_weight=0.2))

    queries = [
        "git merge unrelated histories",
        "pytest module not found",
        "rust linting cargo",
    ]

    for query in queries:
        results = gen_engine.search(query, search_bullets, limit=3)
        logger.debug("Search '%s' -> %d results", query, len(results))
        print(f"\n  Query: '{query}'")
        if results:
            top = results[0]
            print(f"  Top result: [{top.final_score:.4f}] {top.content[:60]}...")
        else:
            print(f"  No results found")

    # ═════ Phase 3: Decay — Time passes ══════════════════════════════
    print(f"\n{'=' * 60}")
    print("  Phase 3: DECAY — Simulate time passing")
    print("=" * 60)

    decay_engine = DecayEngine(config=DecayConfig(
        half_life_days=30.0, boost_factor=0.1, protection_days=7,
        permanent_threshold=15, archive_threshold=0.02,
    ))

    future = NOW + timedelta(days=45)
    decay_bullets = [
        BulletDecayInfo(bullet_id=f"mem-{i}", created_at=NOW, recall_count=0)
        for i in range(total_extracted)
    ]
    sweep_result = decay_engine.sweep(decay_bullets, now=future)
    logger.debug("Decay sweep at +45d: updated=%d archived=%d",
                 sweep_result.updated, sweep_result.archived)
    print(f"\n  +45 days later (0 recalls):")
    print(f"  Updated: {sweep_result.updated}, Archived: {sweep_result.archived}")
    for bid, detail in sweep_result.details.items():
        print(f"    {bid}: weight={detail.weight:.4f}, archive={detail.should_archive}")

    # ═════ Phase 4: Reinforce — Frequent recall saves memories ═══════
    print(f"\n{'=' * 60}")
    print("  Phase 4: REINFORCE — Recall boosts preserve memories")
    print("=" * 60)

    r_no_recall = decay_engine.compute_weight(created_at=NOW, recall_count=0, now=future)
    r_5_recall = decay_engine.compute_weight(created_at=NOW, recall_count=5, now=future)
    r_15_recall = decay_engine.compute_weight(created_at=NOW, recall_count=15, now=future)

    logger.debug("Reinforce comparison: 0=%s, 5=%s, 15=%s",
                 r_no_recall.weight, r_5_recall.weight, r_15_recall.weight)

    print(f"\n  At +45 days:")
    print(f"    0 recalls:  weight={r_no_recall.weight:.4f}, archive={r_no_recall.should_archive}")
    print(f"    5 recalls:  weight={r_5_recall.weight:.4f}, archive={r_5_recall.should_archive}")
    print(f"    15 recalls: weight={r_15_recall.weight:.4f}, permanent={r_15_recall.is_permanent}")

    assert r_5_recall.weight > r_no_recall.weight, "5 recalls should boost weight"
    assert r_15_recall.is_permanent, "15 recalls should grant permanent status"

    # ═════ Phase 5: Status — KB analytics ════════════════════════════
    print(f"\n{'=' * 60}")
    print("  Phase 5: STATUS — KB analytics")
    print("=" * 60)

    status = mem.status(user_id="dev1")
    logger.debug("KB status: %s", status)
    print(f"\n  Total memories: {status['total']}")
    print(f"  Sections: {status['sections']}")
    print(f"  Knowledge types: {status['knowledge_types']}")
    print(f"  Avg decay weight: {status['avg_decay_weight']}")

    assert status["total"] == total_extracted

    print("\nPASS: 20_e2e_scenario")


if __name__ == "__main__":
    main()
