# -*- coding: utf-8 -*-
"""[QA] 관악구 헬스장 진짜 개수 — 상한 안 걸고 자연 소진까지."""
import io, sys
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from naver_crawler import fetch_all_places
from places_crawler import crawl_places

BIG = 2000  # 285로 안 막고 네이버가 더 안 줄 때까지

raw = fetch_all_places("관악구 헬스장", count=BIG, sleep_range=(0.4, 0.8))
raw_ok = [r for r in raw if r.get("구") == "관악구"]
print("[원본 fetch_all_places / 상한 2000]")
print(f"  네이버가 실제로 내준 전체 : {len(raw)}개  (= 더 요청해도 이만큼만 줌)")
print(f"  그 중 진짜 관악구          : {len(raw_ok)}개")
print(f"  관악구 아닌 인접 섞임      : {len(raw)-len(raw_ok)}개")

res = crawl_places("관악구 헬스장", count=BIG, emit_log=lambda m: None)
res_ok = sum(1 for r in res if r.get("구") == "관악구")
print(f"\n[실제 프로그램 crawl_places / 구·업종 필터]")
print(f"  사용자가 보는 최종 개수 : {len(res)}개")
print(f"  관악구 맞음             : {res_ok}/{len(res)}")

c = Counter((r.get("dong") or "(동없음)") for r in res)
print(f"\n[관악구 동별 분포] ({len(c)}개 동)")
for d, n in c.most_common():
    print(f"  {d:<10} {n}개")
