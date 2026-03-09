"""Demo 02: Reflector Pipeline — 4-stage knowledge distillation."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memorus.config import ReflectorConfig
from memorus.engines.reflector.engine import ReflectorEngine
from memorus.types import InteractionEvent


def main() -> None:
    engine = ReflectorEngine(config=ReflectorConfig(min_score=20.0))

    # Stage demo: error-fix pattern (triggers ErrorFixRule)
    event = InteractionEvent(
        user_message="I keep getting 'ModuleNotFoundError: No module named foo' when running pytest",
        assistant_message=(
            "The error is caused by a missing install. "
            "Run pip install foo to fix the ModuleNotFoundError. "
            "Also make sure your virtualenv is activated before running pytest."
        ),
    )

    bullets = engine.reflect(event)
    print(f"[1/4] Reflector produced {len(bullets)} bullet(s) from error-fix interaction")
    for b in bullets:
        print(f"       section={b.section.value}, type={b.knowledge_type.value}, "
              f"score={b.instructivity_score:.1f}")
        print(f"       content: {b.content[:80]}...")

    # Stage demo: config-change pattern
    event2 = InteractionEvent(
        user_message="How do I configure prettier to use single quotes?",
        assistant_message=(
            "Add singleQuote: true to your .prettierrc config file. "
            "This is a common preference setting for prettier."
        ),
    )
    bullets2 = engine.reflect(event2)
    print(f"\n[2/4] Config-change: {len(bullets2)} bullet(s)")
    for b in bullets2:
        print(f"       section={b.section.value}, type={b.knowledge_type.value}")

    # Stage demo: new tool discovery
    event3 = InteractionEvent(
        user_message="Is there a faster alternative to pip?",
        assistant_message=(
            "Try using uv, it's a drop-in replacement for pip written in Rust. "
            "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh. "
            "Then use uv pip install instead of pip install."
        ),
    )
    bullets3 = engine.reflect(event3)
    print(f"\n[3/4] New tool: {len(bullets3)} bullet(s)")
    for b in bullets3:
        print(f"       tools={b.related_tools}, entities={b.key_entities[:3]}")

    # Empty/trivial input produces no bullets
    trivial = InteractionEvent(
        user_message="Hi",
        assistant_message="Hello! How can I help?",
    )
    bullets_trivial = engine.reflect(trivial)
    assert len(bullets_trivial) == 0, "Trivial conversation should produce 0 bullets"
    print(f"\n[4/4] Trivial input: {len(bullets_trivial)} bullets (expected 0)")

    print("\nPASS: 02_reflector_pipeline")


if __name__ == "__main__":
    main()
