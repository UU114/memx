"""Demo 13: Token Budget Trimmer — estimating tokens and trimming search results.

Demonstrates:
  - EN vs CJK token estimation (4.0 vs 1.5 chars/token)
  - Budget-aware trimming of ScoredBullet lists
  - Guarantee: at least 1 result always returned (even if over budget)
  - max_results cap behavior
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memx.engines.generator.score_merger import ScoredBullet
from memx.utils.token_counter import TokenBudgetTrimmer

logger = logging.getLogger(__name__)


def _make_bullet(bid: str, content: str, score: float) -> ScoredBullet:
    return ScoredBullet(
        bullet_id=bid, content=content, final_score=score,
        keyword_score=0.0, semantic_score=0.0, decay_weight=1.0,
        recency_boost=1.0,
    )


def main() -> None:
    trimmer = TokenBudgetTrimmer(token_budget=100, max_results=5, chars_per_token=4.0)

    # ── 1. EN token estimation ───────────────────────────────────────
    print("[1/5] English token estimation (4.0 chars/token)")
    en_text = "Use git rebase -i for interactive rebase"  # 41 chars
    en_tokens = trimmer.estimate_tokens(en_text)
    logger.debug("EN estimate: text=%r len=%d tokens=%d", en_text, len(en_text), en_tokens)
    expected_en = int(len(en_text) / 4.0)
    assert en_tokens == expected_en, f"Expected {expected_en}, got {en_tokens}"
    print(f"       text='{en_text}'")
    print(f"       chars={len(en_text)}, estimated_tokens={en_tokens}")

    # ── 2. CJK token estimation (denser) ─────────────────────────────
    print("\n[2/5] CJK token estimation (1.5 chars/token)")
    zh_text = "使用数据库管理系统进行存储"  # 12 CJK chars
    zh_tokens = trimmer.estimate_tokens(zh_text)
    logger.debug("CJK estimate: text=%r len=%d tokens=%d", zh_text, len(zh_text), zh_tokens)
    expected_zh = int(len(zh_text) / 1.5)
    assert zh_tokens == expected_zh, f"Expected {expected_zh}, got {zh_tokens}"
    print(f"       text='{zh_text}'")
    print(f"       chars={len(zh_text)}, estimated_tokens={zh_tokens}")

    # ── 3. Mixed EN+CJK ─────────────────────────────────────────────
    print("\n[3/5] Mixed EN+CJK token estimation")
    mixed_text = "Use git进行版本管理"  # "Use git" (8 EN) + "进行版本管理" (5 CJK)
    mixed_tokens = trimmer.estimate_tokens(mixed_text)
    logger.debug("Mixed estimate: text=%r tokens=%d", mixed_text, mixed_tokens)
    assert mixed_tokens > 0
    print(f"       text='{mixed_text}'")
    print(f"       estimated_tokens={mixed_tokens}")

    # ── 4. Budget trimming ───────────────────────────────────────────
    print("\n[4/5] Budget trimming (budget=100 tokens)")
    bullets = [
        _make_bullet("b1", "A" * 200, 0.9),    # ~50 tokens
        _make_bullet("b2", "B" * 200, 0.8),    # ~50 tokens
        _make_bullet("b3", "C" * 200, 0.7),    # ~50 tokens — should be cut
        _make_bullet("b4", "D" * 200, 0.6),    # ~50 tokens — should be cut
    ]

    trimmed = trimmer.trim(bullets)
    logger.debug("Trimmed: %d -> %d bullets", len(bullets), len(trimmed))
    for sb in trimmed:
        logger.debug("  %s: score=%.2f content_len=%d est_tokens=%d",
                     sb.bullet_id, sb.final_score, len(sb.content),
                     trimmer.estimate_tokens(sb.content))

    # Budget=100, each ~50 tokens -> should fit 2
    assert len(trimmed) == 2, f"Expected 2 after trim, got {len(trimmed)}"
    assert trimmed[0].bullet_id == "b1", "Highest score first"
    assert trimmed[1].bullet_id == "b2", "Second highest next"
    print(f"       Input: {len(bullets)} bullets")
    print(f"       Output: {len(trimmed)} bullets (budget exhausted)")
    for sb in trimmed:
        est = trimmer.estimate_tokens(sb.content)
        print(f"         {sb.bullet_id}: score={sb.final_score:.2f}, ~{est} tokens")

    # ── 5. Guarantee: at least 1 result ──────────────────────────────
    print("\n[5/5] Guarantee: at least 1 result even if over budget")
    tiny_trimmer = TokenBudgetTrimmer(token_budget=1, max_results=5)
    huge_bullet = [_make_bullet("b_huge", "X" * 1000, 1.0)]  # ~250 tokens
    trimmed_tiny = tiny_trimmer.trim(huge_bullet)
    logger.debug("Tiny budget trim: %d -> %d", len(huge_bullet), len(trimmed_tiny))
    assert len(trimmed_tiny) == 1, "Must return at least 1 result"
    print(f"       Budget=1 token, bullet=~{tiny_trimmer.estimate_tokens(huge_bullet[0].content)} tokens")
    print(f"       Result: {len(trimmed_tiny)} bullet (guarantee honored)")

    print("\nPASS: 13_token_budget")


if __name__ == "__main__":
    main()
