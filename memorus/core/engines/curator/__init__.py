"""Curator engine — semantic deduplication for Memorus memories."""

from memorus.core.engines.curator.conflict import (
    Conflict,
    ConflictDetector,
    ConflictResult,
)
from memorus.core.engines.curator.engine import (
    CurateResult,
    CuratorEngine,
    ExistingBullet,
    MergeCandidate,
)
from memorus.core.engines.curator.merger import (
    KeepBestStrategy,
    MergeContentStrategy,
    MergeResult,
    MergeStrategy,
    get_merge_strategy,
)

__all__ = [
    "Conflict",
    "ConflictDetector",
    "ConflictResult",
    "CurateResult",
    "CuratorEngine",
    "ExistingBullet",
    "KeepBestStrategy",
    "MergeCandidate",
    "MergeContentStrategy",
    "MergeResult",
    "MergeStrategy",
    "get_merge_strategy",
]
