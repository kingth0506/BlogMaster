# -*- coding: utf-8 -*-
"""앱 실제 함수 search_images 그대로 재테스트 — 강화된 GPT 검색어 적용 후"""
import json, os
import requests
import image_handler as ih

c = json.load(open('config.json', encoding='utf-8'))
admin = c['api_keys_by_user']['admin']
gpt_key = [k for k in admin.get('gpt_key_list', []) if k][0]
px_key = [k for k in admin.get('pixabay_key_list', []) if k][0]

# 캐시 초기화(새 GPT 규칙 적용) 후 설정
open('_test_cache.json','w').write('{}')
ih.configure_ai_extractor(gpt_key, '_test_cache.json')

DESK = r"C:\Mac\Home\Desktop\사진테스트2"
TARGETS = {"요양원": "강남구 요양원", "이사": "서울 이사", "보관이사": "서울 보관이사"}
N = 15

for folder, kw in TARGETS.items():
    out = os.path.join(DESK, folder)
    os.makedirs(out, exist_ok=True)
    # GPT 검색어 확인
    q = ih.extract_pixabay_queries(kw, gpt_key)
    print(f"\n[{folder}] kw='{kw}'  GPT검색어={q}")
    # 앱이 실제로 쓰는 함수 그대로
    results = ih.search_images(px_key, kw, count=N, ai_api_key=gpt_key)
    print(f"  search_images 반환: {len(results)}장")
    saved = 0
    for r in results:
        url = r.get("large_url") or r.get("url")
        if not url:
            continue
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                saved += 1
                with open(os.path.join(out, f"{saved:02d}_{r.get('id')}.jpg"), "wb") as f:
                    f.write(resp.content)
        except Exception:
            pass
    print(f"  저장: {saved}장 -> {out}")

print("\n=== 완료 ===")
