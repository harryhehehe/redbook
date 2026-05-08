"""Render block JSON into Xiaohongshu plain text."""
from __future__ import annotations

DIVIDER = "——————"
NUM_EMOJI = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
CIRCLED = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨"]


def _render_title(b: dict) -> str:
    return b.get("text", "").strip()


def _render_opener(b: dict) -> str:
    return b.get("text", "").strip()


def _render_principle(b: dict) -> str:
    out = []
    if b.get("heading"):
        out.append(f"📝 {b['heading']}")
        out.append("")
    for i, item in enumerate(b.get("items", [])):
        if isinstance(item, str):
            out.append(f"{NUM_EMOJI[i] if i < 9 else f'{i+1}.'} {item}")
        else:
            idx = item.get("emoji_index") or (NUM_EMOJI[i] if i < 9 else f"{i+1}.")
            label = item.get("label", "")
            detail = item.get("detail", "")
            line = f"{idx} {label}"
            if detail:
                line += f"\n   {detail}"
            out.append(line)
    return "\n".join(out)


def _render_case_study(b: dict) -> str:
    out = []
    head = b.get("topic") or "举个例子"
    out.append(f"🌰 {head}")
    if b.get("condition"):
        out += ["", f"条件：{b['condition']}"]
    if b.get("common_approach"):
        out += ["", f"常规做法：{b['common_approach']} ❌"]
    if b.get("new_approach"):
        out += ["", f"用我的方法：{b['new_approach']} ✅"]
    if b.get("result"):
        out += ["", f"结果：{b['result']}"]
    return "\n".join(out)


def _render_breakdown(b: dict) -> str:
    out = []
    if b.get("heading"):
        out.append(f"🔥 {b['heading']}")
        out.append("")
    for i, item in enumerate(b.get("items", [])):
        if isinstance(item, str):
            out.append(f"{CIRCLED[i] if i < 9 else f'{i+1}.'} {item}")
            continue
        idx = item.get("emoji_index") or (CIRCLED[i] if i < 9 else f"{i+1}.")
        label = item.get("label", "")
        detail = item.get("detail", "")
        diagnosis = item.get("diagnosis", "")
        block = f"{idx} {label}"
        if detail:
            block += f"\n{detail}"
        if diagnosis:
            block += f"\n→ {diagnosis}"
        out.append(block)
        out.append("")
    return "\n".join(out).rstrip()


def _render_before_after(b: dict) -> str:
    out = ["【改造前】"]
    for x in b.get("before", []):
        out.append(f"❌ {x}")
    out += ["", "【改造后】"]
    for x in b.get("after", []):
        out.append(f"✅ {x}")
    return "\n".join(out)


def _render_insight(b: dict) -> str:
    text = b.get("text", "").strip()
    if not text.startswith("💡"):
        text = f"💡 关键认知：\n{text}"
    return text


def _render_method(b: dict) -> str:
    out = []
    if b.get("heading"):
        out.append(f"🔧 {b['heading']}")
        out.append("")
    for i, step in enumerate(b.get("steps", [])):
        if isinstance(step, str):
            out.append(f"Step {NUM_EMOJI[i] if i < 9 else i+1} {step}")
            continue
        idx = step.get("index") or f"Step {NUM_EMOJI[i] if i < 9 else i+1}"
        name = step.get("name", "")
        action = step.get("action", "")
        out.append(f"{idx} {name}")
        if action:
            out.append(action)
        out.append("")
    return "\n".join(out).rstrip()


def _render_divider(_b: dict) -> str:
    return DIVIDER


def _render_engagement_hook(b: dict) -> str:
    return b.get("question", "").strip()


def _render_lead_magnet(b: dict) -> str:
    kw = b.get("keyword", "")
    name = b.get("resource_name", "")
    desc = b.get("resource_desc", "")
    out = [f"回复【{kw}】", f"领《{name}》"]
    if desc:
        out.append(f"（{desc}）")
    return "\n".join(out)


RENDERERS = {
    "title": _render_title,
    "opener": _render_opener,
    "principle": _render_principle,
    "case_study": _render_case_study,
    "breakdown": _render_breakdown,
    "before_after": _render_before_after,
    "insight": _render_insight,
    "method": _render_method,
    "divider": _render_divider,
    "engagement_hook": _render_engagement_hook,
    "lead_magnet": _render_lead_magnet,
}


def render(blocks: list[dict]) -> str:
    parts = []
    for b in blocks:
        t = b.get("type")
        fn = RENDERERS.get(t)
        if not fn:
            parts.append(f"[未知 block: {t}]")
            continue
        text = fn(b)
        if text:
            parts.append(text)
    return "\n\n".join(parts)
