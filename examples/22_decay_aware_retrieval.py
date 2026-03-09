"""Demo 22: Decay-Aware Retrieval — decay weights dynamically affect search ranking.

Modules exercised (4 modules cooperating):
  - DecayEngine: compute_weight() to simulate time-based decay
  - GeneratorEngine: search() with decay_weight affecting final_score
  - RecallReinforcer: reinforce_sync() to boost recalled bullets
  - RetrievalPipeline: full pipeline with all three stages integrated

Data flow:
  Create bullets with different ages → Compute decay weights per bullet
  → Search (decay affects ranking) → Reinforce top results
  → Re-search (reinforced bullets rank higher)
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta, timezone

from memorus.config import DecayConfig, RetrievalConfig
from memorus.engines.decay.engine import DecayEngine
from memorus.engines.generator.engine import BulletForSearch, GeneratorEngine
from memorus.engines.generator.metadata_matcher import MetadataInfo
from memorus.pipeline.retrieval import RecallReinforcer, RetrievalPipeline, SearchResult
from memorus.utils.token_counter import TokenBudgetTrimmer

logger = logging.getLogger(__name__)

NOW = datetime.now(timezone.utc)


def main() -> None:
    # ═════ Setup: Create bullets with different ages ═══════════════════
    print("=" * 60)
    print("  Setup: Bullets with different ages and recall counts")
    print("=" * 60)

    decay_config = DecayConfig(
        half_life_days=30.0, boost_factor=0.1,
        protection_days=7, permanent_threshold=15,
        archive_threshold=0.02,
    )
    decay_engine = DecayEngine(config=decay_config)

    # Bullet A: fresh (1 day old), 0 recalls
    # Bullet B: medium (30 days old), 3 recalls
    # Bullet C: old (60 days old), 0 recalls
    # Bullet D: old (60 days old), 10 recalls (heavily recalled)
    # All bullets have same content relevance to "git rebase" query
    bullet_specs = [
        ("fresh", 1, 0, "Use git rebase -i for interactive commit cleanup"),
        ("medium", 30, 3, "Run git rebase --onto for branch transplant operations"),
        ("old_no_recall", 60, 0, "Apply git rebase to squash commits before merge"),
        ("old_recalled", 60, 10, "Use git rebase -i HEAD~3 to edit last 3 commits"),
    ]

    bullets: list[BulletForSearch] = []
    for label, age_days, recall_count, content in bullet_specs:
        created = NOW - timedelta(days=age_days)
        decay_result = decay_engine.compute_weight(
            created_at=created, recall_count=recall_count, now=NOW,
        )
        logger.debug(
            "Bullet '%s': age=%dd, recalls=%d -> weight=%.4f, protected=%s, permanent=%s",
            label, age_days, recall_count, decay_result.weight,
            decay_result.is_protected, decay_result.is_permanent,
        )

        bullets.append(BulletForSearch(
            bullet_id=label,
            content=content,
            metadata=MetadataInfo(related_tools=["git"], tags=["git", "rebase"]),
            created_at=created,
            decay_weight=decay_result.weight,
            scope="global",
        ))

        print(f"\n  [{label}] age={age_days}d, recalls={recall_count}")
        print(f"    decay_weight={decay_result.weight:.4f}, "
              f"protected={decay_result.is_protected}, permanent={decay_result.is_permanent}")

    # ═════ Phase 1: Search — Decay weights affect ranking ══════════════
    print(f"\n{'=' * 60}")
    print("  Phase 1: SEARCH — Decay weights affect ranking order")
    print("=" * 60)

    gen = GeneratorEngine(config=RetrievalConfig(keyword_weight=0.8, semantic_weight=0.2))
    results = gen.search("git rebase interactive", bullets, limit=4)

    logger.debug("Search results (decay-aware):")
    for r in results:
        logger.debug("  %s: final=%.4f, keyword=%.4f, decay=%.4f, recency=%.4f",
                     r.bullet_id, r.final_score, r.keyword_score,
                     r.decay_weight, r.recency_boost)

    print(f"\n  Query: 'git rebase interactive'")
    print(f"  Ranking (decay × keyword × recency):")
    for i, r in enumerate(results):
        print(f"    #{i+1} [{r.bullet_id:15s}] final={r.final_score:.4f} "
              f"(kw={r.keyword_score:.2f} × decay={r.decay_weight:.4f} × recency={r.recency_boost:.2f})")

    # Fresh bullet should rank highly (protected, recency boost)
    # Old unreinforced bullet should rank low
    fresh_rank = next(i for i, r in enumerate(results) if r.bullet_id == "fresh")
    old_norec_rank = next(i for i, r in enumerate(results) if r.bullet_id == "old_no_recall")
    logger.debug("Rank check: fresh=%d, old_no_recall=%d", fresh_rank, old_norec_rank)
    assert fresh_rank < old_norec_rank, (
        f"Fresh bullet (rank {fresh_rank}) should rank above "
        f"old unreinforced bullet (rank {old_norec_rank})"
    )
    print(f"\n  Assertion: 'fresh' (rank #{fresh_rank+1}) > 'old_no_recall' (rank #{old_norec_rank+1})")

    # ═════ Phase 2: Reinforce — Simulate recall boosting ═══════════════
    print(f"\n{'=' * 60}")
    print("  Phase 2: REINFORCE — Recall boost changes future ranking")
    print("=" * 60)

    # Simulate reinforcing the old_no_recall bullet 12 times
    # 12 recalls → weight = 0.25 * (1 + 0.1*12) = 0.55, surpasses old_recalled (0.50)
    reinforced_recalls = 12
    old_bullet = bullets[2]  # old_no_recall
    new_decay = decay_engine.compute_weight(
        created_at=old_bullet.created_at,
        recall_count=reinforced_recalls,
        now=NOW,
    )
    logger.debug(
        "After reinforcement: old_no_recall weight %.4f -> %.4f (recalls 0 -> %d)",
        old_bullet.decay_weight, new_decay.weight, reinforced_recalls,
    )

    print(f"\n  Reinforcing 'old_no_recall': recalls 0 → {reinforced_recalls}")
    print(f"  Decay weight: {old_bullet.decay_weight:.4f} → {new_decay.weight:.4f}")
    assert new_decay.weight > old_bullet.decay_weight, "Reinforcement should increase weight"

    # Update bullet and re-search
    bullets[2] = BulletForSearch(
        bullet_id="old_no_recall",
        content=old_bullet.content,
        metadata=MetadataInfo(related_tools=["git"], tags=["git", "rebase"]),
        created_at=old_bullet.created_at,
        decay_weight=new_decay.weight,
        scope="global",
    )

    results2 = gen.search("git rebase interactive", bullets, limit=4)

    print(f"\n  Re-search after reinforcement:")
    for i, r in enumerate(results2):
        print(f"    #{i+1} [{r.bullet_id:15s}] final={r.final_score:.4f} "
              f"(decay={r.decay_weight:.4f})")

    # old_no_recall should now rank higher
    old_norec_rank2 = next(i for i, r in enumerate(results2) if r.bullet_id == "old_no_recall")
    logger.debug("After reinforce: old_no_recall rank %d -> %d", old_norec_rank, old_norec_rank2)
    assert old_norec_rank2 < old_norec_rank, (
        f"Reinforced bullet should rank higher: {old_norec_rank2} < {old_norec_rank}"
    )
    print(f"\n  Assertion: 'old_no_recall' improved rank #{old_norec_rank+1} → #{old_norec_rank2+1}")

    # ═════ Phase 3: Full RetrievalPipeline with RecallReinforcer ═══════
    print(f"\n{'=' * 60}")
    print("  Phase 3: FULL PIPELINE — Generator + Trimmer + Reinforcer")
    print("=" * 60)

    # Track reinforcement calls
    reinforce_log: list[tuple[str, dict]] = []

    def mock_update_fn(bullet_id: str, update: dict) -> None:
        logger.debug("mock_update_fn called: %s %s", bullet_id, update)
        reinforce_log.append((bullet_id, update))

    pipeline = RetrievalPipeline(
        generator=gen,
        trimmer=TokenBudgetTrimmer(token_budget=500, max_results=3),
        decay_engine=decay_engine,
        update_fn=mock_update_fn,
    )

    search_result: SearchResult = pipeline.search(
        "git rebase squash commits", bullets=bullets, limit=3,
    )

    logger.debug("Pipeline result: mode=%s, total_candidates=%d, results=%d",
                 search_result.mode, search_result.total_candidates, len(search_result.results))

    print(f"\n  Query: 'git rebase squash commits'")
    print(f"  Mode: {search_result.mode}")
    print(f"  Candidates: {search_result.total_candidates} → Trimmed: {len(search_result.results)}")
    for r in search_result.results:
        print(f"    [{r.final_score:.4f}] {r.content[:60]}...")

    assert search_result.mode in ("full", "degraded")
    assert len(search_result.results) > 0

    # Verify reinforcer was triggered (sync mode for testing)
    reinforcer = RecallReinforcer(decay_engine, update_fn=mock_update_fn)
    hit_ids = [r.bullet_id for r in search_result.results]
    count = reinforcer.reinforce_sync(hit_ids)

    logger.debug("Reinforcer sync: reinforced %d/%d", count, len(hit_ids))
    print(f"\n  RecallReinforcer: {count}/{len(hit_ids)} bullets reinforced")
    assert count == len(hit_ids), f"Expected {len(hit_ids)} reinforced, got {count}"
    assert len(reinforce_log) >= len(hit_ids), "Update fn should be called for each bullet"
    print(f"  Update callbacks: {len(reinforce_log)} calls logged")

    print("\nPASS: 22_decay_aware_retrieval")


if __name__ == "__main__":
    main()
