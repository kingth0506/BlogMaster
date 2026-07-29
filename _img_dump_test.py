# -*- coding: utf-8 -*-
"""개선된 GPT 이미지 검색어로 요양원/이사 사진 100장씩 바탕화면에 저장 — 빌드 전 실테스트"""
import json, os, sys
import requests
import image_handler as ih

c = json.load(open('config.json', encoding='utf-8'))
admin = c['api_keys_by_user']['admin']
gpt_key = [k for k in admin.get('gpt_key_list', []) if k][0]
px_key = [k for k in admin.get('pixabay_key_list', []) if k][0]

ih.configure_ai_extractor(gpt_key, '_test_cache.json')

DESK = r"C:\Mac\Home\Desktop\사진테스트"
TARGETS = {"요양원": "강남구 요양원", "이사": "서울 보관이사"}
N = 100

for folder, kw in TARGETS.items():
    out = os.path.join(DESK, folder)
    os.makedirs(out, exist_ok=True)
    queries = ih.extract_pixabay_queries(kw, gpt_key)
    print(f"\n[{folder}] 키워드='{kw}'  GPT검색어={queries}")
    tag_exclude = ih._tag_exclude_for(kw)
    seen, saved = set(), 0
    for q in queries:
        if saved >= N:
            break
        for page in range(1, 6):
            if saved >= N:
                break
            hits = ih._fetch_hits(px_key, q, page=page, per_page=80)
            if not hits:
                break
            for h in hits:
                if saved >= N:
                    break
                hid = h.get("id")
                if hid in seen:
                    continue
                seen.add(hid)
                tags = (h.get("tags") or "").lower()
                excluded = bool(tag_exclude and any(t in tags for t in tag_exclude))
                if excluded:
                    continue  # 앱과 동일하게 제외태그 거름
                url = h.get("webformatURL", "")
                if not url:
                    continue
                try:
                    r = requests.get(url, timeout=15)
                    if r.status_code == 200:
                        saved += 1
                        fn = os.path.join(out, f"{saved:03d}_{hid}.jpg")
                        with open(fn, "wb") as f:
                            f.write(r.content)
                except Exception as e:
                    pass
    print(f"[{folder}] 저장 완료: {saved}장 -> {out}")

print("\n=== 전체 완료 ===")
