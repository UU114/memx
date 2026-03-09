"""BulletFactory — create, serialize, and deserialize Bullet records."""

from __future__ import annotations

import json
from typing import Any

from memorus.core.types import BulletMetadata

MEMORUS_PREFIX = "memorus_"

# Fields that are stored as JSON strings in mem0 payload
_LIST_FIELDS = frozenset({"related_tools", "related_files", "key_entities", "tags", "incompatible_tags"})


class BulletFactory:
    """Standardised factory for Bullet creation and mem0 payload conversion."""

    @staticmethod
    def create(content: str, **kwargs: Any) -> dict[str, Any]:
        """Create a new Bullet dict with content and BulletMetadata.

        Returns ``{"content": content, "metadata": BulletMetadata(...)}``.
        """
        meta = BulletMetadata(**kwargs)
        return {"content": content, "metadata": meta}

    @staticmethod
    def to_mem0_metadata(bullet_meta: BulletMetadata) -> dict[str, Any]:
        """Convert BulletMetadata to a ``memorus_``-prefixed dict for mem0 payload.

        * Enum fields are serialised as their string value.
        * datetime fields are serialised as ISO-format strings.
        * list fields are serialised as JSON strings.
        """
        data = bullet_meta.model_dump(mode="json")
        result: dict[str, Any] = {}
        for key, value in data.items():
            prefixed = f"{MEMORUS_PREFIX}{key}"
            if key in _LIST_FIELDS and isinstance(value, list):
                result[prefixed] = json.dumps(value)
            else:
                result[prefixed] = value
        return result

    @staticmethod
    def from_mem0_payload(payload: dict[str, Any]) -> BulletMetadata:
        """Extract BulletMetadata from a mem0 payload dict.

        Reads ``metadata`` sub-dict, picks keys with ``memorus_`` prefix, strips
        the prefix and feeds them to ``BulletMetadata.model_validate``.  Missing
        fields fall back to defaults — legacy payloads without any ``memorus_``
        keys produce a valid default ``BulletMetadata`` without errors.
        """
        metadata = payload.get("metadata", {})
        bullet_fields: dict[str, Any] = {}
        prefix_len = len(MEMORUS_PREFIX)
        for key, value in metadata.items():
            if key.startswith(MEMORUS_PREFIX):
                field_name = key[prefix_len:]
                # Deserialise list fields stored as JSON strings
                if field_name in _LIST_FIELDS and isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = []
                bullet_fields[field_name] = value
        return BulletMetadata.model_validate(bullet_fields)

    @staticmethod
    def from_export_payload(mem: dict[str, Any]) -> dict[str, Any]:
        """Reconstruct a memory record from an export payload dict.

        Accepts a single memory entry from an export JSON (which preserves
        the raw mem0 structure including ``metadata`` with ``memorus_`` keys).
        Returns ``{"content": str, "metadata": BulletMetadata}`` suitable
        for re-ingestion.  Falls back to defaults for missing fields.
        """
        content: str = mem.get("memory", "")
        bullet_meta = BulletFactory.from_mem0_payload(mem)
        return {"content": content, "metadata": bullet_meta}

    @staticmethod
    def merge_metadata(
        existing: BulletMetadata, update: dict[str, Any]
    ) -> BulletMetadata:
        """Merge partial updates into existing metadata, returning a new instance."""
        data = existing.model_dump()
        data.update(update)
        return BulletMetadata.model_validate(data)
