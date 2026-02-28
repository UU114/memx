"""Demo 12: Score Ranking — how weight configs change result ordering.

Demonstrates ScoreMerger behavior with different RetrievalConfig weight
settings, showing how keyword_weight vs semantic_weight, decay_weight,
recency_boost, and scope_boost all affect the final ranking.
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta, timezone

from memx.config import RetrievalConfig
from memx.engines.generator.score_merger import BulletInfo, ScoreMerger

logger = logging.getLogger(__name__)

NOW = datetime.now(timezone.utc)


def main() -> None:
    # ── Shared data ──────────────────────────────────────────────────
    keyword_results = {
        "b1": 30.0,   # Strong keyword match
        "b2": 5.0,    # Weak keyword match
        "b3": 20.0,   # Medium keyword match
    }
    semantic_results = {
        "b1": 0.3,    # Weak semantic
        "b2": 0.95,   # Strong semantic
        "b3": 0.6,    # Medium semantic
    }
    bullet_infos = {
        "b1": BulletInfo(bullet_id="b1", content="git rebase tip",
                         created_at=NOW, decay_weight=1.0, scope="global"),
        "b2": BulletInfo(bullet_id="b2", content="react hooks pattern",
                         created_at=NOW, decay_weight=1.0, scope="global"),
        "b3": BulletInfo(bullet_id="b3", content="docker cache tip",
                         created_at=NOW, decay_weight=1.0, scope="global"),
    }

    # ── 1. Keyword-heavy config (0.8 / 0.2) ─────────────────────────
    print("[1/5] Keyword-heavy config (kw=0.8, sem=0.2)")
    cfg_kw = RetrievalConfig(keyword_weight=0.8, semantic_weight=0.2)
    merger_kw = ScoreMerger(config=cfg_kw)
    ranked_kw = merger_kw.merge(keyword_results, semantic_results, bullet_infos)

    logger.debug("Keyword-heavy ranking:")
    for sb in ranked_kw:
        logger.debug("  %s: final=%.4f kw=%.1f sem=%.2f", sb.bullet_id,
                     sb.final_score, sb.keyword_score, sb.semantic_score)

    print(f"       Ranking: {[s.bullet_id for s in ranked_kw]}")
    for sb in ranked_kw:
        print(f"         {sb.bullet_id}: final={sb.final_score:.4f}")
    assert ranked_kw[0].bullet_id == "b1", "b1 (high kw) should be first"

    # ── 2. Semantic-heavy config (0.2 / 0.8) ────────────────────────
    print("\n[2/5] Semantic-heavy config (kw=0.2, sem=0.8)")
    cfg_sem = RetrievalConfig(keyword_weight=0.2, semantic_weight=0.8)
    merger_sem = ScoreMerger(config=cfg_sem)
    ranked_sem = merger_sem.merge(keyword_results, semantic_results, bullet_infos)

    logger.debug("Semantic-heavy ranking:")
    for sb in ranked_sem:
        logger.debug("  %s: final=%.4f kw=%.1f sem=%.2f", sb.bullet_id,
                     sb.final_score, sb.keyword_score, sb.semantic_score)

    print(f"       Ranking: {[s.bullet_id for s in ranked_sem]}")
    for sb in ranked_sem:
        print(f"         {sb.bullet_id}: final={sb.final_score:.4f}")
    assert ranked_sem[0].bullet_id == "b2", "b2 (high sem) should be first"

    # ── 3. Decay weight impact ───────────────────────────────────────
    print("\n[3/5] Decay weight impact on ranking")
    infos_decay = {
        "b1": BulletInfo(bullet_id="b1", content="high kw, low decay",
                         created_at=NOW, decay_weight=0.3, scope="global"),
        "b2": BulletInfo(bullet_id="b2", content="low kw, full decay",
                         created_at=NOW, decay_weight=1.0, scope="global"),
        "b3": BulletInfo(bullet_id="b3", content="med kw, med decay",
                         created_at=NOW, decay_weight=0.7, scope="global"),
    }
    balanced = ScoreMerger(config=RetrievalConfig(keyword_weight=0.5, semantic_weight=0.5))
    ranked_decay = balanced.merge(keyword_results, semantic_results, infos_decay)

    logger.debug("Decay impact ranking:")
    for sb in ranked_decay:
        logger.debug("  %s: final=%.4f decay=%.2f", sb.bullet_id,
                     sb.final_score, sb.decay_weight)

    print(f"       Ranking: {[s.bullet_id for s in ranked_decay]}")
    for sb in ranked_decay:
        print(f"         {sb.bullet_id}: final={sb.final_score:.4f}, decay={sb.decay_weight:.2f}")

    # ── 4. Recency boost ─────────────────────────────────────────────
    print("\n[4/5] Recency boost impact (recent vs old)")
    infos_recency = {
        "b1": BulletInfo(bullet_id="b1", content="old bullet",
                         created_at=NOW - timedelta(days=30), decay_weight=1.0),
        "b2": BulletInfo(bullet_id="b2", content="new bullet",
                         created_at=NOW - timedelta(hours=1), decay_weight=1.0),
    }
    kw_only = {"b1": 25.0, "b2": 25.0}  # Same keyword score

    cfg_recency = RetrievalConfig(
        keyword_weight=1.0, semantic_weight=0.0,
        recency_boost_days=7, recency_boost_factor=1.5,
    )
    merger_recency = ScoreMerger(config=cfg_recency)
    ranked_recency = merger_recency.merge(kw_only, None, infos_recency)

    logger.debug("Recency boost ranking:")
    for sb in ranked_recency:
        logger.debug("  %s: final=%.4f recency=%.2f", sb.bullet_id,
                     sb.final_score, sb.recency_boost)

    assert ranked_recency[0].bullet_id == "b2", "Recent bullet should rank first"
    print(f"       Ranking: {[s.bullet_id for s in ranked_recency]}")
    for sb in ranked_recency:
        print(f"         {sb.bullet_id}: final={sb.final_score:.4f}, "
              f"recency_boost={sb.recency_boost:.2f}")

    # ── 5. Scope boost ───────────────────────────────────────────────
    print("\n[5/5] Scope boost impact (target scope vs global)")
    infos_scope = {
        "b1": BulletInfo(bullet_id="b1", content="global tip",
                         created_at=NOW, decay_weight=1.0, scope="global"),
        "b2": BulletInfo(bullet_id="b2", content="project-specific tip",
                         created_at=NOW, decay_weight=1.0, scope="project:myapp"),
    }
    kw_scope = {"b1": 25.0, "b2": 25.0}

    cfg_scope = RetrievalConfig(keyword_weight=1.0, semantic_weight=0.0, scope_boost=1.5)
    merger_scope = ScoreMerger(config=cfg_scope)
    ranked_scope = merger_scope.merge(kw_scope, None, infos_scope,
                                      target_scope="project:myapp")

    logger.debug("Scope boost ranking:")
    for sb in ranked_scope:
        logger.debug("  %s: final=%.4f scope=%s", sb.bullet_id,
                     sb.final_score, infos_scope[sb.bullet_id].scope)

    assert ranked_scope[0].bullet_id == "b2", "Scoped bullet should rank first"
    print(f"       Ranking: {[s.bullet_id for s in ranked_scope]}")
    for sb in ranked_scope:
        scope = infos_scope[sb.bullet_id].scope
        print(f"         {sb.bullet_id}: final={sb.final_score:.4f}, scope='{scope}'")

    print("\nPASS: 12_score_ranking")


if __name__ == "__main__":
    main()
