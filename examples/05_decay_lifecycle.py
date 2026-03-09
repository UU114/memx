"""Demo 05: Decay Lifecycle — weight computation, protection, permanence, sweep."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta, timezone

from memorus.config import DecayConfig
from memorus.engines.decay.engine import BulletDecayInfo, DecayEngine


def main() -> None:
    config = DecayConfig(
        half_life_days=30.0,
        boost_factor=0.1,
        protection_days=7,
        permanent_threshold=15,
        archive_threshold=0.02,
    )
    engine = DecayEngine(config=config)
    now = datetime.now(timezone.utc)

    # --- 1. Fresh memory (within protection window) ---
    r1 = engine.compute_weight(
        created_at=now - timedelta(days=2),
        recall_count=0,
        now=now,
    )
    assert r1.is_protected, "2-day-old memory should be protected"
    assert r1.weight == 1.0
    print(f"[1/5] Fresh (2 days): weight={r1.weight:.2f}, protected={r1.is_protected}")

    # --- 2. Aged memory (past protection, no recalls) ---
    r2 = engine.compute_weight(
        created_at=now - timedelta(days=60),
        recall_count=0,
        now=now,
    )
    assert not r2.is_protected
    assert r2.weight < 1.0, "60-day-old memory without recalls should decay"
    print(f"[2/5] Aged (60 days, 0 recalls): weight={r2.weight:.4f}, "
          f"archive={r2.should_archive}")

    # --- 3. Frequently recalled memory (permanent) ---
    r3 = engine.compute_weight(
        created_at=now - timedelta(days=90),
        recall_count=20,
        now=now,
    )
    assert r3.is_permanent, "20 recalls >= permanent_threshold(15)"
    assert r3.weight == 1.0
    print(f"[3/5] Permanent (20 recalls): weight={r3.weight:.2f}, "
          f"permanent={r3.is_permanent}")

    # --- 4. Moderate recall boosts weight ---
    r4 = engine.compute_weight(
        created_at=now - timedelta(days=45),
        recall_count=5,
        last_recall=now - timedelta(days=3),
        now=now,
    )
    assert r4.weight > r2.weight, "Recalls should boost weight vs zero-recall"
    print(f"[4/5] Moderate (45 days, 5 recalls): weight={r4.weight:.4f}")

    # --- 5. Batch sweep ---
    bullets = [
        BulletDecayInfo(
            bullet_id="b-fresh",
            created_at=now - timedelta(days=1),
            recall_count=0,
        ),
        BulletDecayInfo(
            bullet_id="b-aging",
            created_at=now - timedelta(days=100),
            recall_count=2,
        ),
        BulletDecayInfo(
            bullet_id="b-permanent",
            created_at=now - timedelta(days=200),
            recall_count=20,
        ),
        BulletDecayInfo(
            bullet_id="b-archive",
            created_at=now - timedelta(days=365),
            recall_count=0,
        ),
    ]

    sweep = engine.sweep(bullets, now=now)
    print(f"\n[5/5] Sweep results:")
    print(f"       Updated:   {sweep.updated}")
    print(f"       Archived:  {sweep.archived}")
    print(f"       Permanent: {sweep.permanent}")
    print(f"       Unchanged: {sweep.unchanged}")
    print(f"       Errors:    {len(sweep.errors)}")

    for bid, dr in sweep.details.items():
        print(f"       {bid}: weight={dr.weight:.4f}, "
              f"perm={dr.is_permanent}, archive={dr.should_archive}")

    total = sweep.updated + sweep.archived + sweep.permanent + sweep.unchanged
    assert total == len(bullets), f"Expected {len(bullets)}, got {total}"

    print("\nPASS: 05_decay_lifecycle")


if __name__ == "__main__":
    main()
