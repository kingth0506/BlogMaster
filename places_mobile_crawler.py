# -*- coding: utf-8 -*-
"""하위 호환 래퍼 — naver_crawler 모듈로 위임."""
from naver_crawler import (
    build_mobile_headers,
    extract_apollo_state,
    fetch_all_places,
    fetch_places_html,
    split_address_tokens,
)

__all__ = [
    "build_mobile_headers",
    "extract_apollo_state",
    "fetch_all_places",
    "fetch_places_html",
    "split_address_tokens",
    "fetch_places",
    "crawl",
]


def fetch_places(keyword: str, timeout: int = 10) -> list[dict]:
    rows, _ = fetch_places_html(keyword, timeout=timeout)
    return [
        {
            "상호명": r["name"],
            "지번주소": r["jibun_address"],
            "시": r["시"],
            "구": r["구"],
            "동": r["동"],
            "카테고리": r["category"],
        }
        for r in rows
    ]


def crawl(keywords):
    if isinstance(keywords, str):
        keywords = [keywords]
    all_rows = []
    seen = set()
    for kw in keywords:
        for r in fetch_all_places(kw, count=100):
            if r["name"] in seen:
                continue
            seen.add(r["name"])
            all_rows.append({
                "상호명": r["name"],
                "지번주소": r["jibun_address"],
                "시": r["시"],
                "구": r["구"],
                "동": r["동"],
                "카테고리": r["category"],
            })
    return all_rows
