"""Demo 19: Multi-Pattern Extraction — complex interactions yield multiple bullets.

Demonstrates:
  - Single interaction containing error-fix + new-tool + config-change patterns
  - Reflector extracts multiple CandidateBullets from one conversation
  - Each bullet gets different section, knowledge_type, and score
  - Distiller truncation and entity extraction
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memx.config import ReflectorConfig
from memx.engines.reflector.engine import ReflectorEngine
from memx.types import InteractionEvent

logger = logging.getLogger(__name__)


def main() -> None:
    config = ReflectorConfig(mode="rules", min_score=20.0, max_content_length=500)
    engine = ReflectorEngine(config=config, sanitizer=None)

    # ── 1. Rich interaction: error + fix + new tool + config ─────────
    print("[1/3] Rich interaction: error-fix + new-tool in one exchange")
    event1 = InteractionEvent(
        user_message=(
            "Error: I keep getting 'ModuleNotFoundError: No module named uv' when running "
            "my Python project. Also, I just discovered ruff for linting and it's way "
            "faster than flake8."
        ),
        assistant_message=(
            "The ModuleNotFoundError means uv isn't installed in your current environment. "
            "Run `pip install uv` to fix it. For ruff, you can configure it in pyproject.toml "
            "with [tool.ruff] section. Set line-length = 88 and select = ['E', 'F', 'I']."
        ),
    )

    bullets1 = engine.reflect(event1)
    logger.debug("Rich interaction produced %d bullets", len(bullets1))
    for i, b in enumerate(bullets1):
        logger.debug("  [%d] section=%s type=%s score=%.1f tools=%s",
                     i, b.section, b.knowledge_type, b.instructivity_score,
                     b.related_tools)

    assert len(bullets1) >= 2, f"Expected >=2 bullets, got {len(bullets1)}"
    print(f"       Extracted {len(bullets1)} bullet(s):")
    for b in bullets1:
        print(f"         section={b.section.value}, type={b.knowledge_type.value}, "
              f"score={b.instructivity_score:.1f}")
        print(f"         content: {b.content[:80]}...")
        if b.related_tools:
            print(f"         tools: {b.related_tools}")

    # ── 2. Config-only interaction ───────────────────────────────────
    print(f"\n[2/3] Config-change interaction")
    event2 = InteractionEvent(
        user_message="I switched from using 2-space indent to 4-space indent in my editor config.",
        assistant_message=(
            "Good choice. Python's PEP 8 recommends 4-space indentation. "
            "Update your .editorconfig with indent_size = 4."
        ),
    )
    bullets2 = engine.reflect(event2)
    logger.debug("Config interaction produced %d bullets", len(bullets2))
    for i, b in enumerate(bullets2):
        logger.debug("  [%d] section=%s type=%s score=%.1f", i, b.section, b.knowledge_type,
                     b.instructivity_score)

    assert len(bullets2) >= 1, f"Expected >=1 bullet, got {len(bullets2)}"
    print(f"       Extracted {len(bullets2)} bullet(s):")
    for b in bullets2:
        print(f"         section={b.section.value}, type={b.knowledge_type.value}, "
              f"score={b.instructivity_score:.1f}")
        print(f"         content: {b.content[:80]}...")

    # ── 3. Trivial interaction (should produce 0 bullets) ────────────
    print(f"\n[3/3] Trivial interaction (noise filtering)")
    event3 = InteractionEvent(
        user_message="Thanks!",
        assistant_message="You're welcome!",
    )
    bullets3 = engine.reflect(event3)
    logger.debug("Trivial interaction produced %d bullets (expected 0)", len(bullets3))
    assert len(bullets3) == 0, f"Expected 0 bullets from trivial input, got {len(bullets3)}"
    print(f"       Extracted {len(bullets3)} bullet(s) (correctly filtered as noise)")

    print("\nPASS: 19_multi_pattern_extract")


if __name__ == "__main__":
    main()
