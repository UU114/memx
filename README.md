# MemX — Intelligent Memory for AI Agents

> mem0 fork + ACE intelligent layer: auto-learn, auto-forget, auto-recall

MemX extends [mem0](https://github.com/mem0ai/mem0) with the **Adaptive Context Engine (ACE)** — a pipeline that automatically distills, deduplicates, decays, and retrieves knowledge so your AI agent remembers what matters and forgets what doesn't.

---

## MemX vs mem0: Key Differences

MemX is a **drop-in replacement** for mem0. All mem0 methods work identically when ACE is disabled. The table below highlights what MemX adds:

| Capability | mem0 | MemX (ACE enabled) |
|---|---|---|
| **Knowledge Extraction** | LLM-based fact extraction on every `add()` (~2–5K tokens/call) | Rules-based Reflector (0 LLM calls, zero cost) |
| **Deduplication** | LLM decides UPDATE/DELETE per record | Cosine similarity ≥ 0.8 → auto-merge (no LLM) |
| **Forgetting** | None — memories persist forever | Exponential decay with half-life + recall boost |
| **Search** | Pure vector similarity | 4-layer hybrid: exact + fuzzy + metadata + vector |
| **Privacy** | No built-in PII sanitization | 12 hardcoded patterns (API keys, tokens, paths) + custom regex |
| **Scope** | Flat (user_id / agent_id / run_id) | Hierarchical: `global`, `project:name`, `workspace:id` |
| **Token Budget** | Caller manages result size | Built-in trimmer with CJK-aware token estimation |
| **Local Embedding** | Requires external API | ONNX Runtime (all-MiniLM-L6-v2, fully offline) |
| **CLI** | None | 10 commands: status, search, learn, list, forget, sweep, conflicts, export, import |

### Migration from mem0

```python
# BEFORE (mem0)
from mem0 import Memory
m = Memory.from_config({"vector_store": {"provider": "qdrant", ...}})
m.add("fact", user_id="u1")
results = m.search("query", user_id="u1")

# AFTER (MemX, ACE off — identical behavior, zero overhead)
from memx import Memory
m = Memory(config={"vector_store": {"provider": "qdrant", ...}})
m.add("fact", user_id="u1")
results = m.search("query", user_id="u1")

# AFTER (MemX, ACE on — full intelligent pipeline)
from memx import Memory
m = Memory(config={
    "ace_enabled": True,
    "vector_store": {"provider": "qdrant", ...},
})
m.add(
    [{"role": "user", "content": "Always run pytest with -v flag"}],
    user_id="u1",
)
results = m.search("pytest verbose", user_id="u1")
```

**Breaking changes when ACE is enabled:**
- `add()` returns an `ace_ingest` envelope with `bullets_added`, `bullets_merged`, `bullets_skipped` counts
- `search()` returns an `ace_search` envelope with `mode` ("full" / "degraded" / "fallback") and `total_candidates`
- ACE config keys (`reflector`, `curator`, `decay`, `retrieval`, `privacy`) are reserved — do not use them as custom mem0 metadata keys

**Fully backward-compatible:**
- All mem0 vector store providers (Qdrant, Chroma, Pinecone, PGVector, etc.) work unchanged
- All mem0 embedding providers (OpenAI, Ollama, HuggingFace, etc.) work unchanged
- All mem0 LLM providers work unchanged
- `add()` / `search()` / `get()` / `delete()` / `update()` / `get_all()` / `history()` / `reset()` all work identically when ACE is off

---

## Features

- **Reflector** — auto-distill conversational noise into structured knowledge bullets (0 LLM calls)
- **Curator** — semantic deduplication and conflict detection
- **Decay** — time-based forgetting with configurable half-life curves
- **Generator** — hybrid search combining vector, exact, fuzzy, and metadata matching
- **Privacy** — PII sanitization with 12 built-in patterns + pluggable custom rules
- **ONNX** — optional local embedding via ONNX Runtime (no API calls)
- **CLI** — full command-line interface for inspecting and managing the knowledge base
- **Daemon** — optional background process for multi-agent shared memory

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Python** | >= 3.9, <= 3.14 |
| **mem0 backend** | At least one vector store configured (e.g., Qdrant, Chroma) |
| **API keys** | Depends on backend — e.g., `OPENAI_API_KEY` for OpenAI embeddings, not needed for ONNX |

## Installation

```bash
# Core (requires mem0 backend)
pip install memx

# With ONNX local embeddings (no API key needed)
pip install memx[onnx]

# With Neo4j graph support
pip install memx[graph]

# Everything
pip install memx[all]

# Development
pip install memx[dev]
```

### Core dependencies

```
mem0ai >= 1.0.0
pydantic >= 2.0
click >= 8.0
```

### Optional dependencies

| Extra | Packages | Purpose |
|---|---|---|
| `onnx` | onnxruntime >= 1.16, tokenizers >= 0.15 | Local embedding (no API calls) |
| `graph` | neo4j >= 5.0 | Graph-based memory relations |
| `dev` | pytest, mypy, ruff, etc. | Testing and linting |

---

## Quick Start

```python
from memx import Memory

# Initialize with ACE enabled
m = Memory(config={"ace_enabled": True})

# Add knowledge from a conversation
result = m.add(
    [{"role": "user", "content": "Always run pytest with -v flag for verbose output"}],
    user_id="dev1",
)
# result includes: bullets_added, bullets_merged, bullets_skipped

# Search the knowledge base
results = m.search("pytest verbose", user_id="dev1")
for r in results.get("results", []):
    print(f"[{r['score']:.2f}] {r['memory']}")
```

### ACE Off (Zero Overhead Proxy)

```python
# Without ACE, MemX is a transparent proxy to mem0
m = Memory()
m.add("Some fact", user_id="u1")
```

---

## API Reference

### Constructor

```python
Memory(config: dict | None = None)
```

`config` is a single dict that contains both mem0 keys and ACE keys. MemX automatically separates them — ACE keys (`ace_enabled`, `reflector`, `curator`, `decay`, `retrieval`, `privacy`, `integration`, `daemon`) are consumed by the ACE engine; everything else is forwarded to the mem0 backend.

### Methods (mem0-compatible)

| Method | Signature | Description |
|---|---|---|
| `add()` | `add(messages, user_id, agent_id, run_id, metadata, filters, prompt, scope, **kwargs)` | Add memories. With ACE: distill → dedup → persist. Without ACE: passthrough to mem0. |
| `search()` | `search(query, user_id, agent_id, run_id, limit=100, filters, scope, **kwargs)` | Search. With ACE: 4-layer hybrid search + decay scoring. Without ACE: vector-only. |
| `get()` | `get(memory_id)` | Get a single memory by ID. |
| `get_all()` | `get_all(user_id, agent_id, **kwargs)` | Get all memories for a user/agent. |
| `update()` | `update(memory_id, data)` | Update a memory's content. |
| `delete()` | `delete(memory_id)` | Delete a single memory. |
| `delete_all()` | `delete_all(user_id, agent_id, **kwargs)` | Delete all memories matching the filter. |
| `history()` | `history(memory_id)` | Get modification history for a memory. |
| `reset()` | `reset()` | Delete all memories in the store. |

### Methods (ACE-only)

These methods are only available on MemX and have no mem0 equivalent:

| Method | Signature | Description |
|---|---|---|
| `status()` | `status(user_id=None)` | KB statistics: total count, sections, knowledge types, avg decay weight. |
| `detect_conflicts()` | `detect_conflicts(user_id=None)` | Find contradictory memories (requires `curator.conflict_detection=True`). |
| `export()` | `export(format="json", scope=None)` | Export KB as JSON dict or Markdown string. |
| `import_data()` | `import_data(data, format="json")` | Import with Curator dedup. Returns `{imported, skipped, merged}`. |
| `run_decay_sweep()` | `run_decay_sweep()` | Manually trigger decay sweep across all memories. |
| `from_config()` | `Memory.from_config(config_dict)` | Factory method (class method). |

### Properties

| Property | Type | Description |
|---|---|---|
| `config` | `MemXConfig` | Access the parsed configuration object. |
| `daemon_available` | `bool` | Whether the background daemon is running. |

---

## Configuration Reference

MemX uses the same config dict as mem0, with additional ACE-specific keys. All ACE keys are optional — defaults are tuned for general use.

```python
config = {
    # --- ACE master switch ---
    "ace_enabled": True,

    # --- Reflector: distills conversations into knowledge bullets ---
    "reflector": {
        "mode": "rules",             # "rules" (default, 0 LLM calls) | "llm" | "hybrid"
        "min_score": 30.0,           # [0–100] minimum instructivity score to keep a bullet
        "max_content_length": 500,   # max chars per distilled bullet
        "max_code_lines": 3,         # max code block lines tolerated in a bullet
    },

    # --- Curator: deduplication and conflict detection ---
    "curator": {
        "similarity_threshold": 0.8,       # [0–1] cosine similarity threshold for merge
        "merge_strategy": "keep_best",     # "keep_best" | "merge_content"
        "conflict_detection": False,       # enable contradiction detection
        "conflict_min_similarity": 0.5,    # [0–1] lower bound for conflict window
        "conflict_max_similarity": 0.8,    # [0–1] upper bound for conflict window
    },

    # --- Decay: time-based forgetting ---
    "decay": {
        "half_life_days": 30.0,        # exponential decay half-life in days
        "boost_factor": 0.1,           # recall boost: weight *= (1 + boost × recall_count)
        "protection_days": 7,          # new memories immune to decay for N days
        "permanent_threshold": 15,     # recall_count >= this → permanent (weight=1.0)
        "archive_threshold": 0.02,     # weight below this → archive candidate
        "sweep_on_session_end": True,  # auto-sweep when session ends
    },

    # --- Retrieval: hybrid search tuning ---
    "retrieval": {
        "keyword_weight": 0.6,         # weight for exact + fuzzy + metadata layers
        "semantic_weight": 0.4,        # weight for vector search layer
        "recency_boost_days": 7,       # memories newer than N days get boosted
        "recency_boost_factor": 1.2,   # multiplier for recent memories
        "scope_boost": 1.3,            # multiplier for memories matching target scope
        "max_results": 5,              # max results returned after trimming
        "token_budget": 2000,          # max total tokens for LLM context
    },

    # --- Privacy: PII/secret sanitization ---
    "privacy": {
        "always_sanitize": False,      # sanitize even when ACE is off
        "sanitize_paths": True,        # redact OS user paths
        "custom_patterns": [           # additional regex patterns for redaction
            r"INTERNAL-\d{6}",
        ],
    },

    # --- Integration: agent behavior ---
    "integration": {
        "auto_recall": True,           # auto-recall during inference
        "auto_reflect": True,          # auto-reflect on tool results
        "sweep_on_exit": True,         # auto-decay on session exit
        "context_template": "xml",     # "xml" | "markdown" | "plain"
    },

    # --- Daemon: multi-process shared memory ---
    "daemon": {
        "enabled": False,              # enable background daemon
        "idle_timeout_seconds": 300,   # daemon shuts down after idle (5 min)
        "socket_path": None,           # IPC socket path (auto-resolved if None)
    },

    # --- mem0 backend config (passed through as-is) ---
    "vector_store": {
        "provider": "qdrant",
        "config": {"host": "localhost", "port": 6333},
    },
    "llm": {
        "provider": "openai",
        "config": {"model": "gpt-4o-mini"},
    },
    "embedder": {
        "provider": "openai",
        "config": {"model": "text-embedding-3-small"},
    },
}
```

---

## Architecture

### Ingest Pipeline (`add()`)

```
Raw Input (messages / string)
    │
    ▼
┌─────────────────────┐
│  Privacy Sanitizer   │  Strip PII, API keys, tokens, paths
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Reflector (4-stage) │  1. PatternDetector → detect learnable patterns
│                      │  2. KnowledgeScorer → classify & score (0–100)
│                      │  3. PrivacySanitizer → redact in context
│                      │  4. BulletDistiller → compact into CandidateBullets
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Curator             │  Compare against existing KB:
│                      │  - similarity ≥ 0.8 → merge
│                      │  - similarity 0.5–0.8 → conflict warning
│                      │  - otherwise → insert
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  mem0 Backend        │  Persist to vector store (Qdrant, Chroma, etc.)
└─────────────────────┘
```

### Retrieval Pipeline (`search()`)

```
Query string
    │
    ▼
┌─────────────────────┐
│  Generator (4-layer) │  L1: ExactMatcher   — word-level exact match
│                      │  L2: FuzzyMatcher   — token-based fuzzy (SequenceMatcher)
│                      │  L3: MetadataMatcher — tools, entities, tags (Jaccard)
│                      │  L4: VectorSearcher  — embedding cosine similarity
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Score Merger        │  final = (kw × 0.6 + semantic × 0.4)
│                      │        × decay_weight
│                      │        × recency_boost
│                      │        × scope_boost
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Token Trimmer       │  Cap to max_results (5) and token_budget (2000)
│                      │  CJK-aware: 1.5 chars/token vs 4.0 for Latin
│                      │  Guarantee: always returns ≥ 1 result
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Recall Reinforcer   │  Async: increment recall_count on recalled bullets
│  (background)        │  → feeds back into Decay for adaptive retention
└─────────────────────┘
```

### Decay Formula

```
base_weight = 2^(-age_days / half_life)
boosted     = base_weight × (1 + boost_factor × recall_count)
final       = clamp(boosted, 0.0, 1.0)
```

Special rules:
- `recall_count >= 15` → **permanent** (weight = 1.0, never decays)
- `age <= 7 days` → **protected** (weight = 1.0, not yet decayed)
- `weight < 0.02` → **archive candidate** (may be swept)

---

## ONNX Local Embedding

Run embeddings entirely offline — no API keys, no network calls.

```bash
pip install memx[onnx]
```

```python
m = Memory(config={
    "ace_enabled": True,
    "embedder": {
        "provider": "onnx",            # Use ONNX instead of OpenAI/etc.
        "config": {
            "model": "all-MiniLM-L6-v2",  # 384 dimensions (default)
        },
    },
})
```

| Setting | Default |
|---|---|
| Model | all-MiniLM-L6-v2 |
| Dimensions | 384 |
| Max tokens | 256 |
| Cache dir | `~/.memx/models/` |
| Auto-download | Yes (HuggingFace Hub, first run only) |

After the first download, the model is cached locally and works fully offline. If ONNX dependencies are missing, the search pipeline degrades gracefully (vector layer skipped, keyword layers still work).

---

## Privacy Sanitizer

The sanitizer runs **before** any processing and cannot be disabled. It catches:

| # | Pattern | Example |
|---|---|---|
| 1 | Private key blocks (PEM) | `-----BEGIN RSA PRIVATE KEY-----` |
| 2 | Bearer / JWT tokens | `Bearer eyJhbG...` |
| 3 | Anthropic API keys | `sk-ant-api03-...` |
| 4 | OpenAI API keys | `sk-proj-...` |
| 5 | GitHub tokens | `ghp_xxxx`, `github_pat_...` |
| 6 | AWS Access Key IDs | `AKIA...` |
| 7 | AWS Secret Access Keys | 40-char base64 strings |
| 8 | Database URLs with credentials | `postgres://user:pass@host/db` |
| 9 | Generic API key parameters | `api_key=...` in URLs |
| 10 | Password / secret fields | `password: "..."` |
| 11 | Windows user paths | `C:\Users\john\...` |
| 12 | Unix user paths | `/home/john/...` |

Add custom patterns:

```python
config = {
    "privacy": {
        "custom_patterns": [
            r"INTERNAL-\d{6}",          # Company-specific IDs
            r"customer_[a-f0-9]{32}",   # Customer tokens
        ],
    },
}
```

---

## Multi-User & Multi-Agent

### Scope hierarchy

```python
# Global knowledge (shared across all users)
m.add("Always use UTC timestamps", scope="global", user_id="alice")

# Project-level knowledge
m.add("Use FastAPI for this project", scope="project:myapp", user_id="alice")

# User-specific (via mem0 parameter)
m.add("I prefer dark mode", user_id="alice")

# Agent-specific (via mem0 parameter)
m.add("Tool X requires --force flag", agent_id="tool_resolver")
```

### Cross-agent recall

```python
# Search includes scope-matching boost (default +30%)
results = m.search("API patterns", user_id="alice", scope="project:myapp")
# Returns: project:myapp memories (boosted) + global memories
```

### Daemon mode (shared memory across processes)

```python
m = Memory(config={
    "ace_enabled": True,
    "daemon": {
        "enabled": True,
        "idle_timeout_seconds": 300,
    },
})
# All agents sharing this config use the same in-memory KB via IPC
# Falls back to direct mode if daemon is unavailable
```

---

## CLI

MemX ships with a Click-based CLI. After installation, the `memx` command is available:

```bash
# Show knowledge base statistics
memx status

# Search memories
memx search "pytest" --limit 10 --scope "project:myapp"

# Teach new knowledge (goes through Reflector)
memx learn "Always use -v flag"

# Teach raw (skip Reflector, store as-is)
memx learn "raw fact" --raw

# List all memories with filters
memx list --type method --scope "project:myapp" --limit 20

# Export knowledge base
memx export --format json
memx export --format markdown -o knowledge.md

# Import knowledge base (with Curator dedup)
memx import --file backup.json

# Detect contradictory memories
memx conflicts

# Delete a specific memory
memx forget <memory-id>
memx forget <memory-id> --yes   # skip confirmation

# Run decay sweep
memx sweep
```

All commands support `--json` for machine-readable output and `--user-id` for multi-user filtering.

---

## Knowledge Types & Sections

MemX classifies each knowledge bullet with a **type** and **section** for structured organization.

### Knowledge Types

| Type | Description | Example |
|---|---|---|
| `method` | A how-to approach | "Use `git rebase -i` for squashing" |
| `trick` | A shortcut or optimization | "Ctrl+Shift+P opens command palette" |
| `pitfall` | A common mistake to avoid | "Don't use `==` for None comparison" |
| `preference` | A user/team preference | "Always use single quotes in Python" |
| `knowledge` | A general fact | "PostgreSQL supports JSONB indexing" |

### Sections

`commands` · `debugging` · `architecture` · `workflow` · `tools` · `patterns` · `preferences` · `general`

---

## Troubleshooting

### Search returns no results with ACE on

The Reflector filters low-quality content. Check `reflector.min_score` (default 30.0) — lower it if valid knowledge is being filtered out.

### Vector search layer skipped ("degraded" mode)

Embedding provider unavailable (API down or ONNX not installed). Keyword layers (L1–L3) still work. Install ONNX for offline resilience:

```bash
pip install memx[onnx]
```

### Memories disappearing over time

This is the Decay engine working as intended. Frequently recalled memories are retained; unused ones fade. To keep a memory permanently, recall it 15+ times or increase `decay.half_life_days`.

### PII sanitizer too aggressive

Built-in patterns cannot be disabled (by design). If they catch false positives, the sanitized content will contain `[REDACTED]` markers. Check `privacy.sanitize_paths` if file paths are being redacted unnecessarily.

### `add()` returns `raw_fallback: true`

The Reflector failed to extract structured bullets and fell back to raw mem0 `add()`. Your data was still saved — just not distilled. Check input format (list of role/content dicts works best).

---

## License

Apache-2.0
