"""Recommend templates and few-shot example posts for a given topic + audience."""
from __future__ import annotations
from collections import Counter
from . import data


def _score_post(post: dict, topic: str, audience: str | None) -> int:
    score = 0
    topic_lower = topic.lower()

    for t in post.get("topics", []):
        if t.lower() in topic_lower or topic_lower in t.lower():
            score += 5
    for p in post.get("pain_points", []):
        if p.lower() in topic_lower or topic_lower in p.lower():
            score += 3
    if topic_lower in post.get("title", "").lower():
        score += 4

    if audience and audience != "both":
        if post.get("audience") == audience or post.get("audience") == "both":
            score += 2
        else:
            score -= 2
    return score


def recommend(topic: str, audience: str | None = None, top_k: int = 3) -> dict:
    scored = [(p, _score_post(p, topic, audience)) for p in data.posts()]
    scored = [(p, s) for p, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)

    template_counter: Counter[str] = Counter()
    template_posts: dict[str, list[str]] = {}
    for p, s in scored:
        tid = p["template_id"]
        template_counter[tid] += s
        template_posts.setdefault(tid, []).append(p["id"])

    template_ranking = [
        {"template_id": tid, "score": score, "matched_posts": template_posts[tid][:3]}
        for tid, score in template_counter.most_common(top_k)
    ]

    if not template_ranking:
        template_ranking = [
            {"template_id": "T2_pain_resonance", "score": 0, "matched_posts": []}
        ]

    few_shot = [p for p, _ in scored[:3]]
    if len(few_shot) < 2:
        for p in data.posts():
            if p not in few_shot:
                few_shot.append(p)
                if len(few_shot) >= 2:
                    break

    return {"templates": template_ranking, "few_shot_posts": few_shot}
