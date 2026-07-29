# -*- coding: utf-8 -*-
"""[QA] 관악구 '헬스장' 검색에서 2차필터에 걸려 빠지는 업체들의 카테고리 분석."""
import io, sys
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from naver_crawler import fetch_all_places
from places_crawler import _match_biz

raw = fetch_all_places("관악구 헬스장", count=2000, sleep_range=(0.4, 0.8))
gwanak = [r for r in raw if r.get("구") == "관악구"]

passed = [r for r in gwanak if _match_biz("헬스장", r.get("category", ""))]
dropped = [r for r in gwanak if not _match_biz("헬스장", r.get("category", ""))]

print(f"관악구 전체: {len(gwanak)}개 / 통과(헬스장): {len(passed)}개 / 탈락: {len(dropped)}개\n")

print("[통과한 업체 카테고리]")
for cat, n in Counter(r.get("category","") for r in passed).most_common():
    print(f"  {cat:<16} {n}개")

print("\n[탈락한 업체 카테고리] ← 이 중 헬스장 살릴지 결정")
for cat, n in Counter(r.get("category","") for r in dropped).most_common():
    print(f"  {cat:<16} {n}개")

print("\n[탈락 '스포츠시설' 업체명 샘플 15개]")
for r in [x for x in dropped if x.get("category")=="스포츠시설"][:15]:
    print(f"  {r['name']}")
