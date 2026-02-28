"""Demo 14: Recall Reinforcement — boost decay weight through search recall.

Demonstrates:
  - RecallReinforcer fires on search hits (sync mode for testability)
  - DecayEngine.reinforce() increments recall_count via update_fn callback
  - Recall count boost effect on decay weight over time
  - RetrievalPipeline integration with reinforcement
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta, timezone

from memx.config import DecayConfig
from memx.engines.decay.engine import DecayEngine
from memx.pipeline.retrieval import RecallReinforcer

logger = logging.getLogger(__name__)

NOW = datetime.now(timezone.utc)


def main() -> None:
    config = DecayConfig(
        half_life_days=30.0,
        boost_factor=0.1,
        protection_days=7,
        permanent_threshold=15,
        archive_threshold=0.02,
    )
    engine = DecayEngine(config=config)

    # ── 1. Baseline: 60-day-old memory with 0 recalls ────────────────
    print("[1/4] Baseline: 60-day-old memory, 0 recalls")
    created = NOW - timedelta(days=60)
    r0 = engine.compute_weight(created_at=created, recall_count=0, now=NOW)
    logger.debug("Baseline: weight=%.4f archive=%s", r0.weight, r0.should_archive)
    print(f"       weight={r0.weight:.4f}, should_archive={r0.should_archive}")

    # ── 2. Same memory with 5 recalls (boost) ────────────────────────
    print("\n[2/4] Same memory with 5 recalls (boost_factor=0.1)")
    r5 = engine.compute_weight(created_at=created, recall_count=5, now=NOW)
    logger.debug("5 recalls: weight=%.4f (improvement=%.4f)", r5.weight, r5.weight - r0.weight)
    assert r5.weight > r0.weight, "Recall boost should increase weight"
    print(f"       weight={r5.weight:.4f} (boost: +{r5.weight - r0.weight:.4f})")

    # ── 3. RecallReinforcer with update callback ─────────────────────
    print("\n[3/4] RecallReinforcer — sync reinforcement via callback")

    # Track update calls
    updates: dict[str, list[dict]] = {}

    def mock_update(bullet_id: str, payload: dict) -> None:
        updates.setdefault(bullet_id, []).append(payload)
        logger.debug("update_fn called: bid=%s payload=%s", bullet_id, payload)

    reinforcer = RecallReinforcer(decay_engine=engine, update_fn=mock_update)

    hit_ids = ["mem-001", "mem-002", "mem-003"]
    count = reinforcer.reinforce_sync(hit_ids)
    logger.debug("Reinforced %d/%d bullets", count, len(hit_ids))

    assert count == 3, f"Expected 3 reinforced, got {count}"
    assert len(updates) == 3, f"Expected 3 updates, got {len(updates)}"
    for bid in hit_ids:
        assert bid in updates, f"Missing update for {bid}"
        assert updates[bid][0]["recall_count_delta"] == 1
        assert "last_recall" in updates[bid][0]

    print(f"       Reinforced: {count}/{len(hit_ids)} bullets")
    print(f"       Callbacks received: {len(updates)}")
    for bid, payloads in updates.items():
        print(f"         {bid}: delta={payloads[0]['recall_count_delta']}, "
              f"last_recall={payloads[0]['last_recall'].isoformat()[:19]}")

    # ── 4. Reinforcement with partial failure ────────────────────────
    print("\n[4/4] Reinforcement with partial failure (1 bad callback)")

    fail_updates: dict[str, list[dict]] = {}
    call_count = [0]

    def partial_fail_update(bullet_id: str, payload: dict) -> None:
        call_count[0] += 1
        if call_count[0] == 2:
            logger.debug("update_fn simulated failure for bid=%s", bullet_id)
            raise RuntimeError("Simulated storage failure")
        fail_updates.setdefault(bullet_id, []).append(payload)

    reinforcer2 = RecallReinforcer(decay_engine=engine, update_fn=partial_fail_update)
    count2 = reinforcer2.reinforce_sync(["a", "b", "c"])
    logger.debug("Partial fail: reinforced=%d/3", count2)
    assert count2 == 2, f"Expected 2 (1 failed), got {count2}"
    print(f"       Attempted: 3, Succeeded: {count2}, Failed: 1")
    print(f"       Error isolation: pipeline continues despite callback failure")

    print("\nPASS: 14_recall_reinforcement")


if __name__ == "__main__":
    main()
