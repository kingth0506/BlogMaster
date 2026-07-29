# -*- coding: utf-8 -*-
"""전체 카테고리 픽사베이 이미지 수집 — 바탕화면에 카테고리별 폴더 저장"""
import sys, os, shutil, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from image_handler import BIZ_TO_EN, _get_en_queries, _fetch_hits, _tag_filter_for, _tag_exclude_for

SAVE_DIR = r"C:\Mac\Home\Desktop\픽사베이_테스트"
IMAGES_PER_CAT = 50

def _get_key():
    try:
        from users import load_users
        u = load_users().get("admin", {})
        ks = (u.get("api_keys") or {}).get("pixabay_key_list") or []
        return ks[0] if ks else ""
    except Exception:
        return ""

def _hit_matches(h, tag_filter, tag_exclude):
    tags = (h.get("tags") or "").lower()
    if tag_exclude and any(t in tags for t in tag_exclude):
        return False
    if not tag_filter:
        return True
    return any(t in tags for t in tag_filter)

def fetch_for_cat(api_key, cat):
    queries = _get_en_queries(cat)
    if not queries:
        return [], "NO_QUERY"
    tag_filter = _tag_filter_for(cat)
    tag_exclude = _tag_exclude_for(cat)

    found = []
    for q in queries:
        for page in range(1, 4):
            hits = _fetch_hits(api_key, q, page=page)
            if not hits:
                break
            for h in hits:
                if _hit_matches(h, tag_filter, tag_exclude):
                    found.append(h)
                if len(found) >= IMAGES_PER_CAT:
                    break
            if len(found) >= IMAGES_PER_CAT:
                break
        if len(found) >= IMAGES_PER_CAT:
            break

    if not found:
        # 필터 완화 (exclude만)
        for q in queries:
            hits = _fetch_hits(api_key, q, page=1)
            for h in hits:
                tags = (h.get("tags") or "").lower()
                if not tag_exclude or not any(t in tags for t in tag_exclude):
                    found.append(h)
                if len(found) >= IMAGES_PER_CAT:
                    break
            if len(found) >= IMAGES_PER_CAT:
                break
        status = "FILTER_RELAXED" if found else "NO_RESULT"
    else:
        status = "OK"

    return found[:IMAGES_PER_CAT], status

def download_hit(h, save_path):
    url = h.get("largeImageURL") or h.get("webformatURL", "")
    if not url:
        return False
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"  다운로드 실패: {e}")
        return False

def main():
    api_key = _get_key()
    if not api_key:
        print("API 키 없음")
        return

    if os.path.exists(SAVE_DIR):
        shutil.rmtree(SAVE_DIR)
    os.makedirs(SAVE_DIR)

    cats = list(BIZ_TO_EN.keys())
    print(f"총 {len(cats)}개 카테고리 테스트 시작\n")

    no_result = []
    relaxed = []

    for i, cat in enumerate(cats, 1):
        cat_dir = os.path.join(SAVE_DIR, cat)
        os.makedirs(cat_dir, exist_ok=True)

        hits, status = fetch_for_cat(api_key, cat)
        tag_info = hits[0].get("tags", "")[:80] if hits else ""
        print(f"[{i:3}/{len(cats)}] {cat:15} {status}  {tag_info}", flush=True)

        for j, h in enumerate(hits, 1):
            save_path = os.path.join(cat_dir, f"{j}.jpg")
            download_hit(h, save_path)

        if status == "NO_RESULT":
            no_result.append(cat)
        elif status == "FILTER_RELAXED":
            relaxed.append(cat)

    print(f"\n결과없음 ({len(no_result)}개): {no_result}")
    print(f"필터완화  ({len(relaxed)}개): {relaxed}")
    print(f"\n저장 위치: {SAVE_DIR}")

if __name__ == "__main__":
    main()
