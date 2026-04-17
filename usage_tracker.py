# -*- coding: utf-8 -*-
"""일일 API 사용량 추적"""
import json
import os
from datetime import date

USAGE_FILE = os.path.join(os.path.dirname(__file__), "usage.json")

DAILY_LIMITS = {
    "gemini": 1500,
    "gpt": 999999,
    "pixabay": 2400,  # 100/hour * 24h
}


def _load() -> dict:
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") != str(date.today()):
            return {"date": str(date.today()), "gemini": 0, "gpt": 0, "pixabay": 0, "posts": 0}
        return data
    except Exception:
        return {"date": str(date.today()), "gemini": 0, "gpt": 0, "pixabay": 0, "posts": 0}


def _save(data: dict):
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_usage(api_type: str, count: int = 1):
    data = _load()
    data[api_type] = data.get(api_type, 0) + count
    _save(data)


def add_post():
    data = _load()
    data["posts"] = data.get("posts", 0) + 1
    _save(data)


def get_usage() -> dict:
    return _load()


def get_remaining(provider: str = "gemini") -> dict:
    data = _load()
    ai_used = data.get(provider, 0)
    ai_limit = DAILY_LIMITS.get(provider, 999999)
    pix_used = data.get("pixabay", 0)
    pix_limit = DAILY_LIMITS["pixabay"]

    ai_remaining = max(0, ai_limit - ai_used)
    pix_remaining = max(0, pix_limit - pix_used)

    # AI는 글 1개당 2회, Pixabay는 글 1개당 5회
    posts_by_ai = ai_remaining // 2
    posts_by_pix = pix_remaining // 5
    posts_remaining = min(posts_by_ai, posts_by_pix)

    return {
        "posts_today": data.get("posts", 0),
        "ai_used": ai_used,
        "ai_limit": ai_limit,
        "ai_remaining": ai_remaining,
        "pix_used": pix_used,
        "pix_limit": pix_limit,
        "pix_remaining": pix_remaining,
        "posts_remaining": posts_remaining,
    }
