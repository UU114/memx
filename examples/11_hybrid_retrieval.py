"""Demo 11: Hybrid Retrieval — L1-L4 matcher layers + GeneratorEngine search.

Demonstrates the 4-layer retrieval architecture:
  L1 ExactMatcher:    word-boundary keyword matching (EN + CJK)
  L2 FuzzyMatcher:    2-gram/stem overlap ratio
  L3 MetadataMatcher: tool/entity/tag prefix/exact matching
  L4 VectorSearcher:  semantic search (degraded mode when unavailable)
  GeneratorEngine:    orchestrates all layers into ranked ScoredBullet results.
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone

from memx.config import RetrievalConfig
from memx.engines.generator.engine import BulletForSearch, GeneratorEngine
from memx.engines.generator.exact_matcher import ExactMatcher
from memx.engines.generator.fuzzy_matcher import FuzzyMatcher
from memx.engines.generator.metadata_matcher import MetadataInfo, MetadataMatcher

logger = logging.getLogger(__name__)


def main() -> None:
    # ── L1: ExactMatcher ─────────────────────────────────────────────
    print("[1/5] L1 ExactMatcher — keyword matching")
    exact = ExactMatcher(hit_score=15.0)

    r1 = exact.match("git rebase", "Use git rebase -i for interactive rebase")
    logger.debug("L1 match: score=%.1f terms=%s", r1.score, r1.matched_terms)
    assert r1.score == 30.0, f"Expected 30.0, got {r1.score}"
    assert set(r1.matched_terms) == {"git", "rebase"}
    print(f"       EN: query='git rebase' -> score={r1.score}, terms={r1.matched_terms}")

    r1_zh = exact.match("数据库", "使用数据库管理系统进行存储")
    logger.debug("L1 CJK match: score=%.1f terms=%s", r1_zh.score, r1_zh.matched_terms)
    assert r1_zh.score > 0, "CJK match should find substring"
    print(f"       ZH: query='数据库' -> score={r1_zh.score}, terms={r1_zh.matched_terms}")

    # Batch matching
    contents = [
        "Use git rebase -i for interactive rebase",
        "Docker build cache invalidation",
        "cargo clippy for Rust linting",
    ]
    batch = exact.match_batch("git rebase", contents)
    logger.debug("L1 batch: scores=%s", [r.score for r in batch])
    assert batch[0].score > 0, "First content should match"
    assert batch[1].score == 0, "Second content should not match 'git rebase'"
    print(f"       Batch: scores={[r.score for r in batch]}")

    # ── L2: FuzzyMatcher ─────────────────────────────────────────────
    print("\n[2/5] L2 FuzzyMatcher — fuzzy token overlap")
    fuzzy = FuzzyMatcher(max_score=10.0)

    r2 = fuzzy.match("debugging Python errors", "debug Python error messages quickly")
    logger.debug("L2 match: score=%.2f ratio=%.2f terms=%s",
                 r2.score, r2.details.get("hit_ratio", 0), r2.matched_terms)
    assert r2.score > 0, "Fuzzy should find stemmed overlap"
    print(f"       query='debugging Python errors' -> score={r2.score:.2f}, "
          f"ratio={r2.details['hit_ratio']:.2f}, terms={r2.matched_terms}")

    r2_zh = fuzzy.match("数据库管理", "数据分析和数据库操作")
    logger.debug("L2 CJK match: score=%.2f terms=%s", r2_zh.score, r2_zh.matched_terms)
    print(f"       ZH: query='数据库管理' -> score={r2_zh.score:.2f}, "
          f"terms={r2_zh.matched_terms}")

    # ── L3: MetadataMatcher ──────────────────────────────────────────
    print("\n[3/5] L3 MetadataMatcher — structured metadata matching")
    meta_matcher = MetadataMatcher(tools_score=4.0, entities_score=3.0, tags_score=3.0)

    meta = MetadataInfo(
        related_tools=["git-rebase", "git-merge"],
        key_entities=["GitHub", "GitLab"],
        tags=["python", "devops"],
    )
    r3 = meta_matcher.match("git python tips", meta)
    logger.debug("L3 match: score=%.1f tools=%s entities=%s tags=%s",
                 r3.score, r3.matched_tools, r3.matched_entities, r3.matched_tags)
    assert r3.matched_tools, "Should match 'git' prefix against 'git-rebase'"
    assert r3.matched_tags, "Should match 'python' tag"
    print(f"       query='git python tips' -> score={r3.score}")
    print(f"       tools={r3.matched_tools}, entities={r3.matched_entities}, tags={r3.matched_tags}")

    # ── L4: VectorSearcher (degraded) ────────────────────────────────
    print("\n[4/5] GeneratorEngine mode detection")
    engine = GeneratorEngine(config=RetrievalConfig())
    logger.debug("GeneratorEngine mode=%s (no vector backend)", engine.mode)
    assert engine.mode == "degraded", f"Expected degraded, got {engine.mode}"
    print(f"       No vector backend -> mode='{engine.mode}' (L4 skipped)")

    # ── Full pipeline: GeneratorEngine.search() ──────────────────────
    print("\n[5/5] GeneratorEngine — full hybrid search (L1+L2+L3, degraded L4)")

    now = datetime.now(timezone.utc)
    bullets = [
        BulletForSearch(
            bullet_id="b1",
            content="Use git rebase -i for cleaning up commit history",
            metadata=MetadataInfo(
                related_tools=["git-rebase"],
                key_entities=["Git"],
                tags=["git", "workflow"],
            ),
            created_at=now,
            decay_weight=1.0,
            scope="global",
        ),
        BulletForSearch(
            bullet_id="b2",
            content="Docker build cache can be invalidated by COPY order",
            metadata=MetadataInfo(
                related_tools=["docker"],
                key_entities=["Docker", "Dockerfile"],
                tags=["docker", "devops"],
            ),
            created_at=now,
            decay_weight=0.8,
            scope="global",
        ),
        BulletForSearch(
            bullet_id="b3",
            content="pytest -x stops on first failure for fast debugging",
            metadata=MetadataInfo(
                related_tools=["pytest"],
                key_entities=["Python"],
                tags=["python", "testing"],
            ),
            created_at=now,
            decay_weight=0.9,
            scope="global",
        ),
        BulletForSearch(
            bullet_id="b4",
            content="Use cargo clippy for Rust linting before cargo build",
            metadata=MetadataInfo(
                related_tools=["cargo", "clippy"],
                key_entities=["Rust"],
                tags=["rust"],
            ),
            created_at=now,
            decay_weight=0.7,
            scope="project:rust-app",
        ),
    ]

    results = engine.search("git rebase commit history", bullets, limit=5)
    logger.debug("GeneratorEngine results: %d scored bullets", len(results))
    for sb in results:
        logger.debug("  %s: final=%.4f kw=%.1f sem=%.2f decay=%.2f",
                     sb.bullet_id, sb.final_score, sb.keyword_score,
                     sb.semantic_score, sb.decay_weight)

    assert len(results) > 0, "Should return at least 1 result"
    assert results[0].bullet_id == "b1", f"b1 should rank first, got {results[0].bullet_id}"
    print(f"       Query: 'git rebase commit history'")
    print(f"       Results ({len(results)}):")
    for sb in results:
        print(f"         {sb.bullet_id}: final={sb.final_score:.4f}, "
              f"kw={sb.keyword_score:.1f}, sem={sb.semantic_score:.2f}, "
              f"decay={sb.decay_weight:.2f}")

    print("\nPASS: 11_hybrid_retrieval")


if __name__ == "__main__":
    main()
