"""Assemble system + user prompts from template + few-shot + libraries."""
from __future__ import annotations
import json
import random
from . import data


SYSTEM_PROMPT = """你是一名深圳本地的初中数学家教老师，正在小红书写纯文字爆款帖。

你必须严格按用户给定的【模板 block 列表】顺序输出，每个 block 填入符合槽位定义的内容。

输出要求：
1. 必须返回合法 JSON，结构为 {"blocks": [{"type": "...", ...其他字段}, ...]}
2. block 顺序、type 名称必须和用户给的模板一致
3. 引流 block 的 keyword 必须从用户给定的【可选引流资料】列表里选（不允许编造）
4. 真题案例如需具体年份/题号，使用占位符 {TODO: 填真题}，不要编造
5. 风格：口语化、短句、第一人称"我"、多用 emoji、案例用化名+具体数字
6. 不要输出 markdown 代码块，直接输出 JSON
"""


SYSTEM_PROMPT_FREE = """你是一名深圳本地的初中数学家教老师，正在小红书写纯文字爆款帖。

请根据用户给的主题和额外要求，自由设计帖子结构（不限定模板），输出 block 列表。

输出要求：
1. 必须返回合法 JSON，结构为 {"blocks": [{"type": "...", ...其他字段}, ...]}
2. block type 必须从【可用 block 类型】列表中选择，每个 block 的字段按定义填写
3. 一篇帖子建议 4-8 个 block，必须包含 1 个 title 开头，并以 1 个 lead_magnet 引流 block 收尾
4. 引流 block 的 keyword 必须从用户给定的【可选引流资料】列表里选（不允许编造）
5. 真题案例如需具体年份/题号，使用占位符 {TODO: 填真题}，不要编造
6. 风格：口语化、短句、第一人称"我"、多用 emoji、案例用化名+具体数字
7. 根据主题特点和额外要求，自由组合最合适的 block 序列（如解题类多用 principle/case_study/method；情绪类多用 opener/insight/before_after）
8. 不要输出 markdown 代码块，直接输出 JSON
"""


def _format_few_shot(post: dict) -> str:
    lm = post.get("lead_magnet", {})
    return f"""【范例 {post['id']}】{post['title']}
- 模板：{post['template_id']}
- 受众：{post.get('audience')}
- 标签：{post.get('topics', []) + post.get('pain_points', [])}
- 关键素材：{post.get('key_lines', [])}
- 核心金句：{post.get('core_insight', '')}
- 引流：回复【{lm.get('keyword', '')}】领《{lm.get('resource', '')}》
"""


def _build_magnet_pool(topic: str) -> list[dict]:
    libs = data.libraries()
    all_magnets = libs["lead_magnet_examples"]
    related = [m for m in all_magnets if any(
        t.lower() in topic.lower() or topic.lower() in t.lower()
        for t in [m["keyword"], m["resource_name"]]
    )]
    pool = related + random.sample(all_magnets, min(5, len(all_magnets)))
    seen, magnet_options = set(), []
    for m in pool:
        if m["keyword"] not in seen:
            magnet_options.append(m)
            seen.add(m["keyword"])
        if len(magnet_options) >= 6:
            break
    return magnet_options


def build_prompt(
    topic: str,
    audience: str,
    template_id: str | None,
    few_shot_posts: list[dict],
    extra_notes: str | None = None,
) -> tuple[str, str]:
    """template_id 为 None 时进入自由模式，LLM 自由组合 block。"""
    if template_id is None:
        return _build_prompt_free(topic, audience, few_shot_posts, extra_notes)

    template = data.get_template(template_id)
    if not template:
        raise ValueError(f"Unknown template_id: {template_id}")

    libs = data.libraries()
    magnet_options = _build_magnet_pool(topic)
    title_hooks = libs["title_hook_patterns"]

    user_prompt = f"""【主题】{topic}
【受众】{audience}
【模板】{template['name']}（{template['id']}）— 适用：{template['use_case']}

【模板 block 序列】（必须严格按此顺序输出）：
{json.dumps(template['blocks'], ensure_ascii=False, indent=2)}

【block 类型字段定义参考】：
{json.dumps(data.block_types(), ensure_ascii=False, indent=2)}

【可选引流资料】（lead_magnet 的 keyword/resource_name/resource_desc 必须从这里选）：
{json.dumps(magnet_options, ensure_ascii=False, indent=2)}

【标题钩子风格参考】（任选其一）：
{json.dumps(title_hooks, ensure_ascii=False, indent=2)}

【few-shot 范例帖】（参考语感和结构，不要照抄内容）：
{chr(10).join(_format_few_shot(p) for p in few_shot_posts[:3])}

{f'【额外要求】{extra_notes}' if extra_notes else ''}

请按上面的 block 序列输出 JSON。"""

    return SYSTEM_PROMPT, user_prompt


def _build_prompt_free(
    topic: str,
    audience: str,
    few_shot_posts: list[dict],
    extra_notes: str | None,
) -> tuple[str, str]:
    libs = data.libraries()
    magnet_options = _build_magnet_pool(topic)
    title_hooks = libs["title_hook_patterns"]

    user_prompt = f"""【主题】{topic}
【受众】{audience}
【生成模式】自由模式 — 不限定模板，请根据主题和额外要求自由设计 block 序列

【可用 block 类型及字段定义】（type 必须从此处选）：
{json.dumps(data.block_types(), ensure_ascii=False, indent=2)}

【可选引流资料】（lead_magnet 的 keyword/resource_name/resource_desc 必须从这里选）：
{json.dumps(magnet_options, ensure_ascii=False, indent=2)}

【标题钩子风格参考】（任选其一）：
{json.dumps(title_hooks, ensure_ascii=False, indent=2)}

【few-shot 范例帖】（参考语感，可借鉴结构思路但不要照抄）：
{chr(10).join(_format_few_shot(p) for p in few_shot_posts[:3])}

{f'【额外要求 — 高优先级，必须遵守】{extra_notes}' if extra_notes else ''}

请自由设计 4-8 个 block，输出 JSON。记得 title 开头、lead_magnet 收尾。"""

    return SYSTEM_PROMPT_FREE, user_prompt
