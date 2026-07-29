# -*- coding: utf-8 -*-
"""[QA] 동작구 헬스장 - crawl_places vs fetch_all_places 동 필드 비교 디버그."""
import io, sys
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from places_crawler import crawl_places
from naver_crawler import fetch_all_places

print("=== A) 원본 fetch_all_places (필터X) — 동작구 item 동 필드 ===")
raw = fetch_all_places("동작구 헬스장", count=400, sleep_range=(0.4, 0.8))
raw_dj = [r for r in raw if r.get("구") == "동작구"]
print(f"원본 동작구: {len(raw_dj)}개")
for r in raw_dj[:5]:
    print(f"  {r['name'][:18]:<18} | 구={r.get('구')} 동={r.get('동')!r} | jibun={r.get('jibun_address')}")

print("\n=== B) crawl_places (필터O) — 결과 item 동 필드 ===")
res = crawl_places("동작구 헬스장", count=400, emit_log=lambda m: None)
print(f"최종 수집: {len(res)}개 / 동작구 {sum(1 for r in res if r.get('구')=='동작구')}개")
for r in res[:5]:
    print(f"  {r['name'][:18]:<18} | 구={r.get('구')!r} 동={r.get('동')!r} | jibun={r.get('jibun_address')!r}")

c = Counter((r.get("동") or "(없음)") for r in res)
print(f"\n[crawl_places 동별 분포] {dict(c.most_common())}")
