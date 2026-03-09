"""Memorus custom exception hierarchy."""


class MemorusError(Exception):
    """Base exception for all Memorus errors."""


class ConfigurationError(MemorusError):
    """Invalid configuration."""


class PipelineError(MemorusError):
    """Error in ingest/retrieval pipeline."""


class EngineError(MemorusError):
    """Error in engine execution."""


class DaemonError(MemorusError):
    """Error in daemon lifecycle or IPC."""


class DaemonUnavailableError(DaemonError, ConnectionError):
    """Raised when the daemon is not running or unreachable."""
