"""Load structured JSON data (templates / posts / libraries)."""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "structured"


@lru_cache(maxsize=1)
def _load_templates():
    with open(DATA_DIR / "templates.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_posts():
    with open(DATA_DIR / "posts.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_libraries():
    with open(DATA_DIR / "libraries.json", encoding="utf-8") as f:
        return json.load(f)


def templates() -> list[dict]:
    return _load_templates()["templates"]


def block_types() -> dict:
    return _load_templates()["block_types"]


def posts() -> list[dict]:
    return _load_posts()["posts"]


def libraries() -> dict:
    return _load_libraries()


def get_template(template_id: str) -> dict | None:
    return next((t for t in templates() if t["id"] == template_id), None)


def get_post(post_id: str) -> dict | None:
    return next((p for p in posts() if p["id"] == post_id), None)
