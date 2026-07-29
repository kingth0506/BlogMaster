# -*- coding: utf-8 -*-
"""최종 검증 — 반영구화장, 키즈카페, 방탈출 + 나머지 미처리 6개"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from image_handler import _get_en_queries, _fetch_hits, _tag_filter_for, _tag_exclude_for

def _get_key():
    try:
        from users import load_users
        u = load_users().get("admin", {})
        ks = (u.get("api_keys") or {}).get("pixabay_key_list") or []
        return ks[0] if ks else ""
    except Exception:
        return ""

CATS = [
    "반영구화장", "키즈카페", "방탈출",
    "고양이카페", "애견호텔", "볼링장", "도배", "버블티", "pt샵",
]

def test_cat(api_key, cat):
    queries = _get_en_queries(cat)
    if not queries:
        return f"[{cat}] NO QUERY"
    tag_filter = _tag_filter_for(cat)
    tag_exclude = _tag_exclude_for(cat)

    def _hit_matches(h):
        tags = (h.get("tags") or "").lower()
        if tag_exclude and any(t in tags for t in tag_exclude):
            return False
        if not tag_filter:
            return True
        return any(t in tags for t in tag_filter)

    found = []
    for q in queries:
        hits = _fetch_hits(api_key, q, page=1, per_page=20)
        for h in hits:
            if _hit_matches(h):
                found.append(h)
            if len(found) >= 3:
                break
        if len(found) >= 3:
            break

    if not found:
        # 2차: 필터 완화 (exclude만 적용)
        for q in queries:
            hits = _fetch_hits(api_key, q, page=1, per_page=20)
            for h in hits:
                tags = (h.get("tags") or "").lower()
                if not tag_exclude or not any(t in tags for t in tag_exclude):
                    found.append(h)
                if len(found) >= 2:
                    break
            if len(found) >= 2:
                break
        if not found:
            return f"[NO RESULT] {cat}"
        return f"[{cat}★필터완화] {found[0].get('tags','')[:100]}"
    tags_preview = found[0].get("tags","")[:100]
    return f"[{cat}] {tags_preview}"

def main():
    api_key = _get_key()
    if not api_key:
        print("API 키 없음")
        return
    no_result = []
    for cat in CATS:
        result = test_cat(api_key, cat)
        print(result, flush=True)
        if result.startswith("[NO RESULT]"):
            no_result.append(cat)
    print(f"\n결과없음({len(no_result)}): {no_result}")

if __name__ == "__main__":
    main()
