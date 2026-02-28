"""Demo 15: Graceful Degradation — pipeline resilience to failures.

Demonstrates:
  - GeneratorEngine: L1/L2/L3 error isolation (one layer fails, others work)
  - GeneratorEngine: degraded mode when VectorSearcher unavailable
  - RetrievalPipeline: fallback to mem0 when Generator fails entirely
  - RetrievalPipeline: trimmer failure -> untrimmed results returned
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from memx.config import RetrievalConfig
from memx.engines.generator.engine import BulletForSearch, GeneratorEngine
from memx.engines.generator.metadata_matcher import MetadataInfo
from memx.engines.generator.vector_searcher import VectorSearcher
from memx.pipeline.retrieval import RetrievalPipeline, SearchResult
from memx.utils.token_counter import TokenBudgetTrimmer

logger = logging.getLogger(__name__)

NOW = datetime.now(timezone.utc)


def _make_bullets() -> list[BulletForSearch]:
    return [
        BulletForSearch(
            bullet_id="b1",
            content="Use git rebase -i for commit cleanup",
            metadata=MetadataInfo(related_tools=["git"], tags=["git"]),
            created_at=NOW, decay_weight=1.0,
        ),
        BulletForSearch(
            bullet_id="b2",
            content="pytest -x for fast test debugging",
            metadata=MetadataInfo(related_tools=["pytest"], tags=["testing"]),
            created_at=NOW, decay_weight=0.9,
        ),
    ]


def main() -> None:
    # ── 1. L1 error isolation ────────────────────────────────────────
    print("[1/4] L1 error isolation — ExactMatcher fails, L2+L3 continue")
    engine = GeneratorEngine(config=RetrievalConfig())
    bullets = _make_bullets()

    # Inject failure into the underlying ExactMatcher (inside _run_l1's try/except)
    original_match_batch = engine._exact_matcher.match_batch
    def broken_match_batch(query, contents):
        logger.debug("Injected ExactMatcher.match_batch failure for testing")
        raise RuntimeError("L1 ExactMatcher simulated failure")

    engine._exact_matcher.match_batch = broken_match_batch
    results = engine.search("git rebase", bullets, limit=5)
    engine._exact_matcher.match_batch = original_match_batch  # Restore

    logger.debug("L1 failure: got %d results (L2+L3 carried)", len(results))
    assert len(results) > 0, "Should still get results from L2+L3"
    print(f"       L1 raised RuntimeError -> still got {len(results)} results")
    print(f"       (L2 FuzzyMatcher + L3 MetadataMatcher carried the search)")

    # ── 2. Degraded mode (no L4) ─────────────────────────────────────
    print("\n[2/4] Degraded mode — VectorSearcher unavailable")
    engine_degraded = GeneratorEngine(
        config=RetrievalConfig(),
        vector_searcher=VectorSearcher(search_fn=None),
    )
    logger.debug("Engine mode=%s", engine_degraded.mode)
    assert engine_degraded.mode == "degraded"

    results_deg = engine_degraded.search("git rebase", bullets, limit=5)
    logger.debug("Degraded results: %d bullets, all semantic=0", len(results_deg))
    for sb in results_deg:
        assert sb.semantic_score == 0.0, "No semantic score in degraded mode"

    print(f"       mode='{engine_degraded.mode}', results={len(results_deg)}")
    print(f"       All semantic_score=0.0 (L4 skipped)")

    # ── 3. RetrievalPipeline: Generator failure -> fallback ──────────
    print("\n[3/4] RetrievalPipeline — Generator fails, fallback to mem0")

    broken_gen = MagicMock()
    broken_gen.search.side_effect = RuntimeError("Generator exploded")
    broken_gen.mode = "degraded"

    def mock_mem0_search(query, **kw):
        logger.debug("Fallback mem0_search called with query=%r", query)
        return {
            "results": [
                {"id": "fb1", "memory": "Fallback result from mem0", "score": 0.5}
            ]
        }

    pipeline = RetrievalPipeline(
        generator=broken_gen,
        trimmer=None,
        mem0_search_fn=mock_mem0_search,
    )
    result: SearchResult = pipeline.search("git rebase", bullets=bullets, limit=5)
    logger.debug("Fallback result: mode=%s results=%d", result.mode, len(result.results))

    assert result.mode == "fallback", f"Expected fallback, got {result.mode}"
    assert len(result.results) == 1
    assert result.results[0].content == "Fallback result from mem0"
    print(f"       Generator raised RuntimeError")
    print(f"       mode='{result.mode}', results={len(result.results)}")
    print(f"       content='{result.results[0].content}'")

    # ── 4. Trimmer failure -> untrimmed returned ─────────────────────
    print("\n[4/4] Trimmer failure — returns untrimmed results")

    good_gen = GeneratorEngine(config=RetrievalConfig())

    broken_trimmer = MagicMock(spec=TokenBudgetTrimmer)
    broken_trimmer.trim.side_effect = RuntimeError("Trimmer exploded")
    broken_trimmer._token_budget = 2000

    pipeline2 = RetrievalPipeline(
        generator=good_gen,
        trimmer=broken_trimmer,
    )
    result2: SearchResult = pipeline2.search("git rebase", bullets=bullets, limit=5)
    logger.debug("Trimmer failure: mode=%s results=%d", result2.mode, len(result2.results))

    assert result2.mode == "degraded"  # Still degraded (no L4)
    assert len(result2.results) > 0, "Should return untrimmed results"
    print(f"       Trimmer raised RuntimeError")
    print(f"       mode='{result2.mode}', results={len(result2.results)} (untrimmed)")
    print(f"       Graceful degradation: no data loss despite trimmer failure")

    print("\nPASS: 15_graceful_degradation")


if __name__ == "__main__":
    main()
