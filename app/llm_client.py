"""Qwen (DashScope) LLM client using OpenAI-compatible mode."""
from __future__ import annotations
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class LLMError(Exception):
    pass


def _client():
    from openai import OpenAI
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key or api_key.startswith("sk-xxxx"):
        raise LLMError(
            "未配置 DASHSCOPE_API_KEY。请复制 .env.example 为 .env 并填入千问 API Key。\n"
            "（或使用 --dry-run 仅打印 prompt 不调用 LLM）"
        )
    return OpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)


def generate_blocks(system_prompt: str, user_prompt: str, retry: int = 1) -> dict:
    model = os.getenv("QWEN_MODEL", "qwen-plus")
    client = _client()

    last_err = None
    for attempt in range(retry + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.85,
            )
            text = resp.choices[0].message.content
            obj = json.loads(text)
            if "blocks" not in obj or not isinstance(obj["blocks"], list):
                raise LLMError(f"返回 JSON 缺少 blocks 字段：{text[:200]}")
            return obj
        except (json.JSONDecodeError, LLMError) as e:
            last_err = e
            if attempt < retry:
                continue
            raise LLMError(f"LLM 调用失败：{e}") from e
    raise LLMError(str(last_err))


def generate_blocks_raw(system_prompt: str, user_prompt: str) -> dict:
    """Call Qwen with arbitrary system+user prompts, expect any JSON object back."""
    model = os.getenv("QWEN_MODEL", "qwen-plus")
    client = _client()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )
    return json.loads(resp.choices[0].message.content)


def generate_titles(body_text: str, n: int = 5) -> list[dict]:
    model = os.getenv("QWEN_MODEL", "qwen-plus")
    client = _client()
    prompt = f"""下面是一篇小红书帖子正文，请按 5 种不同风格各生成 1 个标题（≤20 字，可带 emoji）：
1. 扎心型
2. 数字型
3. 疑问型
4. 反常识型
5. 身份型（带'深圳/初二家长'等）

返回 JSON：{{"titles": [{{"style": "扎心", "text": "..."}}, ...]}}

正文：
{body_text}"""
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.9,
    )
    return json.loads(resp.choices[0].message.content).get("titles", [])
