本项目停止更新，请移步 https://github.com/UU114/memorus
Upgrade stopped for this repository, please visit https://github.com/UU114/memorus
# Memorus — Intelligent Memory for AI Agents

> mem0 fork + ACE intelligent layer: auto-learn, auto-forget, auto-recall

Memorus extends [mem0](https://github.com/mem0ai/mem0) with the **Adaptive Context Engine (ACE)** — a pipeline that automatically distills, deduplicates, decays, and retrieves knowledge so your AI agent remembers what matters and forgets what doesn't.

---

## Why Memorus: Local-First Intelligent Memory

mem0 是优秀的记忆框架，但它的核心流程**强依赖远程 LLM API**：每次 `add()` 都需要调用 LLM 提取事实、判断去重、决策更新。这意味着：

- 每次写入消耗 **2–5K tokens**（约 $0.001–0.01/次），大量交互下成本快速累积
- 离线环境（内网、本地开发、飞行模式）**完全无法工作**
- 知识提取质量完全取决于远端 LLM，**无本地可控性**
- 用户数据必须发送到云端 LLM，**隐私合规存在风险**

Memorus 的设计原则是 **Local-First**——所有核心能力（知识提炼、去重、衰退、检索）默认在本地完成，零外部依赖：

| 能力 | mem0 | Memorus (rules 模式) | Memorus (llm/hybrid 模式) |
|---|---|---|---|
| **知识提取** | 每次 add() 调 LLM (~2–5K tokens) | 规则引擎，**0 API 调用** | LLM 语义评估 + 结构化蒸馏 |
| **去重** | LLM 判断 UPDATE/DELETE | 余弦相似度 ≥ 0.8 自动合并 | 同左 |
| **遗忘** | 无——记忆永久留存 | 指数衰退 + 召回强化 | 同左 |
| **检索** | 纯向量相似度 | 4 层混合：精确 + 模糊 + 元数据 + 向量 | 同左 |
| **隐私** | 无内置 PII 脱敏 | 12 种内置规则 + 自定义正则 | 同左 |
| **离线能力** | 不可用 | **完全离线运行**（ONNX 嵌入） | 需 LLM API（失败自动降级到 rules） |
| **每次写入成本** | ~$0.001–0.01 | **$0** | ~$0.0005（仅有价值的交互触发） |
| **嵌入** | 需外部 API | ONNX Runtime 本地推理 | 同左 |
| **作用域** | 扁平 (user_id / agent_id) | 层级：`global` / `project:name` / `workspace:id` | 同左 |
| **Token 预算** | 调用方自行管理 | 内置裁剪器（CJK 感知） | 同左 |
| **CLI** | 无 | 10 条命令 | 同左 |

### Three Reflector Modes

- **`hybrid`** (default): Rule pre-screening (filters 70%+ trivial content at 0 cost) → LLM refines matched candidates + catches implicit knowledge missed by rules. **Best quality/cost balance**
- **`rules`**: Pure rule engine, 0 LLM calls, zero cost, fully offline. Best for high-frequency writes, cost-sensitive, or offline environments
- **`llm`**: Calls LLM for semantic evaluation + knowledge distillation on every interaction, producing "When [condition], [action], because [reason]" structured rules. Best for low-frequency, high-value scenarios

```
hybrid mode:   InteractionEvent → Rule pre-screen → LLM refine/fallback → Sanitize → LLM distill  (0-2 API calls)
rules mode:    InteractionEvent → Rule detect → Rule score → Sanitize → Rule distill               (0 API calls)
llm mode:      InteractionEvent → LLM evaluate → Sanitize → LLM distill                           (1-2 API calls)
```

> **Key advantage: Even in hybrid/llm mode, if the LLM call fails it automatically degrades to rules mode — data is never lost due to API failures.**

### Migration from mem0

```python
# BEFORE (mem0)
from mem0 import Memory
m = Memory.from_config({"vector_store": {"provider": "qdrant", ...}})
m.add("fact", user_id="u1")
results = m.search("query", user_id="u1")

# AFTER (Memorus, ACE off — identical behavior, zero overhead)
from memorus import Memory
m = Memory(config={"vector_store": {"provider": "qdrant", ...}})
m.add("fact", user_id="u1")
results = m.search("query", user_id="u1")

# AFTER (Memorus, ACE on — full intelligent pipeline)
from memorus import Memory
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

- **Reflector** — 3 模式知识蒸馏引擎（rules / llm / hybrid），自动将对话噪声提炼为结构化知识规则
- **Curator** — 语义去重 + 冲突检测（Semantic / Negation）
- **Decay** — 艾宾浩斯指数衰退 + 召回强化，模拟人类"用进废退"
- **Generator** — 4 层混合检索（精确 + 模糊 + 元数据 + 向量）
- **Privacy** — 12 种内置 PII 脱敏规则 + 可插拔自定义正则
- **ONNX** — 本地嵌入推理（all-MiniLM-L6-v2），完全离线
- **CLI** — 10 条命令管理知识库
- **Daemon** — 可选后台进程，支持多 Agent 共享记忆

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Python** | >= 3.9, <= 3.14 |
| **mem0 backend** | At least one vector store configured (e.g., Qdrant, Chroma) |
| **API keys** | Depends on backend — e.g., `OPENAI_API_KEY` for OpenAI embeddings, not needed for ONNX |

## Installation

```bash
# Core — install memorus (default: hybrid mode)
pip install memorus

# With LLM reflector (llm/hybrid modes via litellm)
pip install memorus[llm]

# With ONNX local embeddings (no API key needed)
pip install memorus[onnx]

# With Neo4j graph support
pip install memorus[graph]

# Everything (ONNX + LLM + graph)
pip install memorus[all]

# Development
pip install memorus[dev]
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
| `llm` | litellm >= 1.40 | LLM/hybrid Reflector mode (supports OpenAI, Anthropic, Deepseek, Ollama, etc.) |
| `onnx` | onnxruntime >= 1.16, tokenizers >= 0.15 | Local embedding (no API calls) |
| `graph` | neo4j >= 5.0 | Graph-based memory relations |
| `dev` | pytest, mypy, ruff, etc. | Testing and linting |

> **推荐组合**：`pip install memorus[onnx,llm]` — 嵌入完全本地 + Reflector 可选 LLM 增强

---

## Quick Start

```python
from memorus import Memory

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
# Without ACE, Memorus is a transparent proxy to mem0
m = Memory()
m.add("Some fact", user_id="u1")
```

---

## API Reference

### Constructor

```python
Memory(config: dict | None = None)
```

`config` is a single dict that contains both mem0 keys and ACE keys. Memorus automatically separates them — ACE keys (`ace_enabled`, `reflector`, `curator`, `decay`, `retrieval`, `privacy`, `integration`, `daemon`) are consumed by the ACE engine; everything else is forwarded to the mem0 backend.

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

These methods are only available on Memorus and have no mem0 equivalent:

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
| `config` | `MemorusConfig` | Access the parsed configuration object. |
| `daemon_available` | `bool` | Whether the background daemon is running. |

---

## Configuration Reference

Memorus uses the same config dict as mem0, with additional ACE-specific keys. All ACE keys are optional — defaults are tuned for general use.

```python
config = {
    # --- ACE master switch ---
    "ace_enabled": True,

    # --- Reflector: distills conversations into knowledge bullets ---
    "reflector": {
        "mode": "hybrid",            # "hybrid" (default) | "rules" (0 LLM) | "llm"
        "min_score": 30.0,           # [0–100] minimum instructivity score to keep a bullet
        "max_content_length": 500,   # max chars per distilled bullet
        "max_code_lines": 3,         # max code block lines tolerated in a bullet
        # LLM settings (only used when mode = "llm" or "hybrid")
        "llm_model": "openai/gpt-4o-mini",  # any litellm-compatible model identifier
        "llm_api_base": None,        # custom API base URL (e.g. "https://api.deepseek.com")
        "llm_api_key": None,         # API key (falls back to env vars if None)
        "max_eval_tokens": 512,      # max tokens for LLM evaluation response
        "max_distill_tokens": 256,   # max tokens for LLM distillation response
        "llm_temperature": 0.1,      # low temperature for deterministic extraction
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
│  Reflector (4-stage) │  rules: PatternDetector → KnowledgeScorer → Sanitizer → BulletDistiller
│                      │  llm:   LLMEvaluator → Sanitizer → LLMDistiller
│                      │  hybrid: PatternDetector → LLMEvaluator refine → Sanitizer → LLMDistiller
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
pip install memorus[onnx]
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
| Cache dir | `~/.memorus/models/` |
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

Memorus ships with a Click-based CLI. After installation, the `memorus` command is available:

```bash
# Show knowledge base statistics
memorus status

# Search memories
memorus search "pytest" --limit 10 --scope "project:myapp"

# Teach new knowledge (goes through Reflector)
memorus learn "Always use -v flag"

# Teach raw (skip Reflector, store as-is)
memorus learn "raw fact" --raw

# List all memories with filters
memorus list --type method --scope "project:myapp" --limit 20

# Export knowledge base
memorus export --format json
memorus export --format markdown -o knowledge.md

# Import knowledge base (with Curator dedup)
memorus import --file backup.json

# Detect contradictory memories
memorus conflicts

# Delete a specific memory
memorus forget <memory-id>
memorus forget <memory-id> --yes   # skip confirmation

# Run decay sweep
memorus sweep
```

All commands support `--json` for machine-readable output and `--user-id` for multi-user filtering.

---

## Knowledge Types & Sections

Memorus classifies each knowledge bullet with a **type** and **section** for structured organization.

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
pip install memorus[onnx]
```

### Memories disappearing over time

This is the Decay engine working as intended. Frequently recalled memories are retained; unused ones fade. To keep a memory permanently, recall it 15+ times or increase `decay.half_life_days`.

### PII sanitizer too aggressive

Built-in patterns cannot be disabled (by design). If they catch false positives, the sanitized content will contain `[REDACTED]` markers. Check `privacy.sanitize_paths` if file paths are being redacted unnecessarily.

### `add()` returns `raw_fallback: true`

The Reflector failed to extract structured bullets and fell back to raw mem0 `add()`. Your data was still saved — just not distilled. Check input format (list of role/content dicts works best).

### LLM/hybrid mode falls back to rules

If you set `reflector.mode` to `"llm"` or `"hybrid"` but bullets lack `distilled_rule`, the LLM call may have failed and auto-degraded to rules mode. Check:
1. `litellm` is installed (`pip install memorus[llm]`)
2. API key is set (env var or `reflector.llm_api_key`)
3. Model identifier is valid for your provider (e.g. `"openai/gpt-4o-mini"`, `"deepseek/deepseek-chat"`)

---

## License

Apache-2.0
