# -*- coding: utf-8 -*-
"""수정된 카테고리들 Pixabay 재테스트"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from image_handler import BIZ_TO_EN, _get_en_queries, _fetch_hits, _tag_filter_for, _tag_exclude_for

def _get_key():
    try:
        from users import load_users
        u = load_users().get("admin", {})
        ks = (u.get("api_keys") or {}).get("pixabay_key_list") or []
        return ks[0] if ks else ""
    except Exception:
        return ""

RETEST_CATS = [
    "내과", "이비인후과", "비뇨의학과", "재활의학과", "라식라섹",
    "반영구화장", "탈모클리닉", "태닝샵", "PT샵",
    "댄스학원", "미술학원", "피아노학원",
    "키즈카페", "고양이카페", "애견호텔",
    "방탈출", "볼링장", "도배", "버블티",
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
        return f"[NO RESULT] {cat}"
    tags_preview = ", ".join(h.get("tags","")[:80] for h in found[:2])
    return f"[{cat}] {tags_preview}"

def main():
    api_key = _get_key()
    if not api_key:
        print("API 키 없음")
        return
    no_result = []
    for cat in RETEST_CATS:
        result = test_cat(api_key, cat)
        print(result, flush=True)
        if result.startswith("[NO RESULT]"):
            no_result.append(cat)
    print(f"\n결과없음({len(no_result)}): {no_result}")
    print(f"전체 {len(RETEST_CATS)}개 중 {len(RETEST_CATS)-len(no_result)}개 성공")

if __name__ == "__main__":
    main()
