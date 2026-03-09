"""Smoke tests for memorus package structure."""

import memorus
from memorus.core.exceptions import ConfigurationError, EngineError, MemorusError, PipelineError


def test_version() -> None:
    assert memorus.__version__ == "0.2.1"


def test_exception_hierarchy() -> None:
    assert issubclass(ConfigurationError, MemorusError)
    assert issubclass(PipelineError, MemorusError)
    assert issubclass(EngineError, MemorusError)
    assert issubclass(MemorusError, Exception)
