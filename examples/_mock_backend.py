"""Shared mock utilities for Memorus demos.

Reuses the Memory.__new__ pattern from tests/unit/test_memory.py to create
Memory instances without requiring a real mem0 backend or API keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import MagicMock

from memorus.config import MemorusConfig
from memorus.memory import Memory


def create_mock_memory(
    ace_enabled: bool = False,
    config_overrides: Optional[dict[str, Any]] = None,
) -> Memory:
    """Create a Memory instance with mocked mem0 backend.

    Args:
        ace_enabled: Whether to enable ACE engines.
        config_overrides: Extra keys merged into the config dict.
    """
    config_dict: dict[str, Any] = {"ace_enabled": ace_enabled}
    if config_overrides:
        config_dict.update(config_overrides)

    m = Memory.__new__(Memory)
    m._config = MemorusConfig.from_dict(config_dict)
    m._mem0 = MagicMock()
    m._mem0_init_error = None

    # In-memory store for realistic CRUD behaviour
    _store: dict[str, dict[str, Any]] = {}
    _history: dict[str, list[dict[str, Any]]] = {}

    def _add(content: Any, user_id: str | None = None, **kw: Any) -> dict[str, Any]:
        mid = str(uuid.uuid4())[:8]
        memory_text = content if isinstance(content, str) else str(content)
        entry = {
            "id": mid,
            "memory": memory_text,
            "metadata": kw.get("metadata", {}),
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _store[mid] = entry
        _history.setdefault(mid, []).append({"event": "add", **entry})
        return {"results": [entry]}

    def _search(query: str, **kw: Any) -> dict[str, Any]:
        results = []
        query_lower = query.lower()
        for entry in _store.values():
            mem_text = entry.get("memory", "").lower()
            if any(w in mem_text for w in query_lower.split()):
                results.append({**entry, "score": 0.9})
        return {"results": results}

    def _get_all(**kw: Any) -> dict[str, Any]:
        uid = kw.get("user_id")
        mems = list(_store.values())
        if uid:
            mems = [m for m in mems if m.get("user_id") == uid]
        return {"results": mems, "memories": mems}

    def _get(memory_id: str) -> dict[str, Any]:
        if memory_id in _store:
            return _store[memory_id]
        raise KeyError(f"Memory {memory_id} not found")

    def _update(memory_id: str, data: str) -> dict[str, Any]:
        if memory_id not in _store:
            raise KeyError(f"Memory {memory_id} not found")
        _store[memory_id]["memory"] = data
        _history.setdefault(memory_id, []).append(
            {"event": "update", "memory": data}
        )
        return _store[memory_id]

    def _delete(memory_id: str) -> None:
        _store.pop(memory_id, None)

    def _delete_all(**kw: Any) -> None:
        _store.clear()

    def _history_fn(memory_id: str) -> dict[str, Any]:
        return {"changes": _history.get(memory_id, [])}

    def _reset() -> None:
        _store.clear()
        _history.clear()

    m._mem0.add.side_effect = _add
    m._mem0.search.side_effect = _search
    m._mem0.get_all.side_effect = _get_all
    m._mem0.get.side_effect = _get
    m._mem0.update.side_effect = _update
    m._mem0.delete.side_effect = _delete
    m._mem0.delete_all.side_effect = _delete_all
    m._mem0.history.side_effect = _history_fn
    m._mem0.reset.side_effect = _reset

    m._ingest_pipeline = None
    m._retrieval_pipeline = None
    m._sanitizer = None
    m._daemon_fallback = None

    return m


def populate_mock_memories(
    memory: Memory,
    count: int = 5,
    scopes: Optional[list[str]] = None,
) -> list[str]:
    """Populate a mock Memory with sample entries. Returns list of memory IDs."""
    scopes = scopes or ["global"]
    samples = [
        "Use git rebase -i for cleaning up commit history",
        "pytest -x stops on first failure, useful for debugging",
        "Always run ruff check before committing Python code",
        "Docker build cache can be invalidated by changing COPY order",
        "Use cargo clippy for Rust linting before cargo build",
        "nginx proxy_pass needs trailing slash for path stripping",
        "Python virtualenv should be created with python -m venv",
        "Redis SCAN is preferred over KEYS in production",
        "Use ssh-agent to avoid repeated passphrase entry",
        "kubectl get pods -w watches for changes in real-time",
    ]

    ids: list[str] = []
    for i in range(count):
        scope = scopes[i % len(scopes)]
        result = memory.add(
            samples[i % len(samples)],
            user_id="demo_user",
            metadata={"memorus_scope": scope},
        )
        mid = result["results"][0]["id"]
        ids.append(mid)
    return ids
