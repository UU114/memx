"""Demo 17: Context Formatting — XML / Markdown / Plain templates.

Demonstrates the three context injection formats used by CLIPreInferenceHook
to render recalled memories into LLM prompts.
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memx.integration.cli_hooks import CLIPreInferenceHook

logger = logging.getLogger(__name__)


def main() -> None:
    # Sample search results (same format as Memory.search() output)
    results = [
        {
            "id": "mem-001",
            "memory": "Use git rebase -i for interactive commit cleanup",
            "score": 0.92,
            "metadata": {"memx_knowledge_type": "method"},
        },
        {
            "id": "mem-002",
            "memory": "Always run ruff check before committing Python code",
            "score": 0.78,
            "metadata": {"memx_knowledge_type": "preference"},
        },
        {
            "id": "mem-003",
            "memory": "Docker COPY order affects build cache invalidation",
            "score": 0.65,
            "metadata": {"memx_knowledge_type": "pitfall"},
        },
    ]

    # ── 1. XML format (default) ──────────────────────────────────────
    print("[1/4] XML format (default for Claude Code integration)")
    xml_output = CLIPreInferenceHook._format(results, "xml")
    logger.debug("XML output:\n%s", xml_output)

    assert "<memx-context>" in xml_output
    assert "</memx-context>" in xml_output
    assert 'id="mem-001"' in xml_output
    assert 'score="0.92"' in xml_output
    assert 'type="method"' in xml_output

    print(xml_output)

    # ── 2. Markdown format ───────────────────────────────────────────
    print("\n[2/4] Markdown format")
    md_output = CLIPreInferenceHook._format(results, "markdown")
    logger.debug("Markdown output:\n%s", md_output)

    assert "## MemX Context" in md_output
    assert "**[0.92]**" in md_output
    assert "git rebase" in md_output

    print(md_output)

    # ── 3. Plain text format ─────────────────────────────────────────
    print("\n[3/4] Plain text format")
    plain_output = CLIPreInferenceHook._format(results, "plain")
    logger.debug("Plain output:\n%s", plain_output)

    assert "[MemX]" in plain_output
    lines = plain_output.strip().split("\n")
    assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}"

    print(plain_output)

    # ── 4. Unknown format falls back to XML ──────────────────────────
    print("\n[4/4] Unknown format -> fallback to XML")
    fallback = CLIPreInferenceHook._format(results, "unknown_format")
    logger.debug("Fallback format: starts_with_xml=%s", fallback.startswith("<memx-context>"))

    assert "<memx-context>" in fallback, "Unknown format should fall back to XML"
    print(f"       format='unknown_format' -> produced XML ({len(fallback)} chars)")
    print(f"       Fallback behavior: OK")

    print("\nPASS: 17_context_formatting")


if __name__ == "__main__":
    main()
