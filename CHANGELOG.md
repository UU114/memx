# Changelog

All notable changes to Memorus will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-27

### Added

- **ACE Pipeline** — Adaptive Context Engine with full ingest and retrieval pipelines
- **Reflector Engine** — pattern detection, instructivity scoring, and knowledge distillation
- **Curator Engine** — semantic deduplication, merge suggestions, and conflict detection
- **Decay Engine** — time-based forgetting with configurable exponential/linear curves
- **Generator Engine** — hybrid search combining vector, exact match, fuzzy match, and metadata matching
- **Privacy Sanitizer** — PII detection and scrubbing with pluggable regex patterns
- **ONNX Embeddings** — optional local embedding via ONNX Runtime (no API calls needed)
- **CLI** — full Click-based command-line interface (`memorus status`, `search`, `learn`, `list`, `forget`, `sweep`, `conflicts`, `export`, `import`)
- **Async Support** — `AsyncMemory` class for async/await usage
- **Daemon Mode** — optional background daemon with IPC for shared memory across tools
- **Scoped Memories** — hierarchical scope support (global, project-level)
- **Token Budget Trimmer** — budget-aware result trimming for LLM context windows
- **Import/Export** — JSON and Markdown export, JSON import with Curator dedup
- **GitHub Actions** — automated PyPI publishing on tag push
- **PyPI Packaging** — `pip install memorus` with optional dependency groups (`onnx`, `graph`, `all`, `dev`)

### Notes

- Initial public release
- Requires Python 3.9+
- Built on top of [mem0](https://github.com/mem0ai/mem0) as the storage backend
