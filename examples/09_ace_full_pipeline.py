"""Demo 09: ACE Full Pipeline — IngestPipeline end-to-end with privacy filtering."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock

from memorus.config import CuratorConfig, ReflectorConfig
from memorus.engines.curator.engine import CuratorEngine
from memorus.engines.reflector.engine import ReflectorEngine
from memorus.pipeline.ingest import IngestPipeline
from memorus.privacy.sanitizer import PrivacySanitizer


def main() -> None:
    # --- Setup pipeline with real engines, mocked storage ---
    sanitizer = PrivacySanitizer()
    reflector = ReflectorEngine(
        config=ReflectorConfig(min_score=15.0),
        sanitizer=sanitizer,
    )
    curator = CuratorEngine(config=CuratorConfig(similarity_threshold=0.8))

    # Mock mem0 storage functions
    store: list[dict] = []

    def mock_add(content, **kw):
        store.append({"memory": content, "metadata": kw.get("metadata", {}), **kw})
        return {"results": [{"id": f"id-{len(store)}", "memory": content}]}

    def mock_get_all(**kw):
        return {"memories": store}

    def mock_update(mid, data):
        return {"id": mid, "memory": data}

    pipeline = IngestPipeline(
        reflector=reflector,
        sanitizer=sanitizer,
        curator=curator,
        mem0_add_fn=mock_add,
        mem0_get_all_fn=mock_get_all,
        mem0_update_fn=mock_update,
    )

    # --- 1. Normal interaction with learnable content ---
    result1 = pipeline.process(
        messages=[
            {"role": "user", "content": "I keep getting connection refused error with Redis"},
            {"role": "assistant", "content": (
                "The connection refused error means Redis is not running. "
                "Run redis-server to start it, or use systemctl start redis. "
                "Also check if the default port 6379 is not blocked by firewall."
            )},
        ],
        user_id="alice",
        scope="project:backend",
    )
    print(f"[1/4] Error-fix interaction:")
    print(f"       added={result1.bullets_added}, merged={result1.bullets_merged}, "
          f"skipped={result1.bullets_skipped}")
    print(f"       raw_fallback={result1.raw_fallback}, errors={result1.errors}")

    # --- 2. Interaction containing secrets (should be sanitized) ---
    result2 = pipeline.process(
        messages=[
            {"role": "user", "content": "Set my API key: sk-ant-api03-mySecretKeyThatIsLongEnough123456"},
            {"role": "assistant", "content": (
                "I've noted your API key configuration. "
                "Remember to never commit API keys to git. "
                "Use environment variables or a .env file instead."
            )},
        ],
        user_id="alice",
    )
    print(f"\n[2/4] Secret-containing interaction:")
    print(f"       added={result2.bullets_added}, raw_fallback={result2.raw_fallback}")
    # Verify secrets were sanitized in stored data
    for entry in store:
        mem_text = entry.get("memory", "")
        assert "mySecretKey" not in mem_text, f"Secret leaked into storage: {mem_text[:60]}"
    print("       Secret sanitization: verified (no leaks in store)")

    # --- 3. Trivial input falls back to raw add ---
    result3 = pipeline.process(
        messages="hello",
        user_id="bob",
    )
    print(f"\n[3/4] Trivial input:")
    print(f"       raw_fallback={result3.raw_fallback} (expected True)")
    assert result3.raw_fallback, "Trivial input should trigger raw fallback"

    # --- 4. Empty input produces empty result ---
    result4 = pipeline.process(messages=None)
    assert result4.bullets_added == 0
    assert not result4.raw_fallback
    print(f"\n[4/4] Empty input: added=0, no errors")

    print(f"\n       Total stored entries: {len(store)}")
    print("\nPASS: 09_ace_full_pipeline")


if __name__ == "__main__":
    main()
