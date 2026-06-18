# -*- coding: utf-8 -*-
"""3번 검증 — 새 크롤링이 jibun_address(동 정보) 제대로 채우는지 확인. 10개만."""
import sys, os, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from places_crawler import crawl_places
from content_generator import _build_full_title

KEYWORD = "강남구 변호사"
COUNT = 10

print(f"=== {KEYWORD} / {COUNT}개 크롤 ===\n")
def on_progress(cur, scanned, name, results=None):
    print(f"  [{cur}] {name}")

t0 = time.time()
results = crawl_places(KEYWORD, count=COUNT, on_progress=on_progress)
elapsed = time.time() - t0
print(f"\n=== 완료 {len(results)}개 / {elapsed:.1f}초 ===\n")

# 통계
has_jibun = sum(1 for p in results if p.get("jibun_address"))
has_station = sum(1 for p in results if p.get("nearby_station"))
import re as _re

def _check_prefix(p, ptype):
    """해당 형식이 prefix에 정상 적용됐는지"""
    cp = dict(p)
    cp["_override_title_prefix"] = ptype
    title = _build_full_title(cp, KEYWORD, "테스트")
    name = p.get("name", "")
    prefix = title.replace(f" {name} 테스트", "")
    if ptype == "dong":
        return bool(_re.match(r"[가-힣]+동\s", prefix))
    if ptype == "station":
        return bool(_re.match(r"[가-힣A-Za-z0-9]+역\s", prefix))
    if ptype == "gu":
        return bool(_re.match(r"[가-힣]+구\s", prefix))
    return False

dong_ok = sum(1 for p in results if _check_prefix(p, "dong"))
sta_ok = sum(1 for p in results if _check_prefix(p, "station"))
gu_ok = sum(1 for p in results if _check_prefix(p, "gu"))

print(f"=== 데이터 통계 ===")
print(f"jibun_address: {has_jibun}/{len(results)}")
print(f"nearby_station: {has_station}/{len(results)}")
print()
print(f"=== prefix 적용 성공률 ===")
print(f"동 prefix:  {dong_ok}/{len(results)}")
print(f"역 prefix:  {sta_ok}/{len(results)}")
print(f"구 prefix:  {gu_ok}/{len(results)}")
print()

# 각 업체별 결과
for i, p in enumerate(results, 1):
    name = p.get("name", "?")
    jibun = p.get("jibun_address", "") or "(빈)"
    sta = p.get("nearby_station", "") or "(빈)"
    print(f"[{i}] {name}")
    print(f"    jibun: {jibun} / station: {sta}")
    for ptype in ("dong", "station", "gu"):
        cp = dict(p)
        cp["_override_title_prefix"] = ptype
        title = _build_full_title(cp, KEYWORD, "추천 마무리")
        prefix = title.replace(f" {name} 추천 마무리", "")
        ok = "✅" if _check_prefix(p, ptype) else "❌"
        print(f"    [{ptype:7s}] {ok} {prefix}")
print()

# 판정
all_ok = (dong_ok == len(results) and sta_ok == len(results) and gu_ok == len(results))
if all_ok:
    print(f"✅ 전체 통과 — 동/역/구 모든 prefix 정상")
else:
    print(f"⚠ 부분 통과 — 동:{dong_ok} 역:{sta_ok} 구:{gu_ok}")
