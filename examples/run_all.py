"""Run all MemX demo scripts and report results."""

import importlib
import logging
import sys
import os
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Enable DEBUG logging for all memx modules so demos expose internal state
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-5s [%(name)s] %(message)s",
    stream=sys.stderr,
)

DEMOS = [
    "01_quickstart",
    "02_reflector_pipeline",
    "03_curator_dedup",
    "04_conflict_detection",
    "05_decay_lifecycle",
    "06_privacy_sanitizer",
    "07_scoped_memory",
    "08_export_import",
    "09_ace_full_pipeline",
    "10_config_showcase",
    "11_hybrid_retrieval",
    "12_score_ranking",
    "13_token_budget",
    "14_recall_reinforcement",
    "15_graceful_degradation",
    "16_bullet_factory",
    "17_context_formatting",
    "18_memory_analytics",
    "19_multi_pattern_extract",
    "20_e2e_scenario",
    "21_ingest_to_context",
    "22_decay_aware_retrieval",
    "23_conflict_lifecycle",
    "24_privacy_pipeline",
    "25_scoped_knowledge_system",
]


def main() -> None:
    results: list[tuple[str, bool, float, str]] = []
    total_start = time.perf_counter()

    print("=" * 60)
    print("  MemX Demo Suite")
    print("=" * 60)

    for name in DEMOS:
        print(f"\n{'─' * 60}")
        print(f"  Running: {name}")
        print(f"{'─' * 60}")
        start = time.perf_counter()
        try:
            mod = importlib.import_module(f"examples.{name}")
            mod.main()
            elapsed = time.perf_counter() - start
            results.append((name, True, elapsed, ""))
        except Exception as e:
            elapsed = time.perf_counter() - start
            err = traceback.format_exc()
            results.append((name, False, elapsed, err))
            print(f"\nFAIL: {name}")
            print(err)

    total_elapsed = time.perf_counter() - total_start

    # Summary
    print(f"\n{'=' * 60}")
    print("  Summary")
    print(f"{'=' * 60}")

    passed = 0
    failed = 0
    for name, ok, elapsed, err in results:
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] {name} ({elapsed:.2f}s)")

    print(f"\n  Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
    print(f"  Time:  {total_elapsed:.2f}s")
    print(f"{'=' * 60}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
