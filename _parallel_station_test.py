# -*- coding: utf-8 -*-
"""[QA] 3봇 병렬 + 근처역 수집 동시 — 실사용 그대로 최종 부하 테스트."""
import io, sys, time
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from places_crawler import crawl_places_parallel

keywords = ["강남구 헬스장", "강동구 헬스장", "강북구 헬스장"]
logs = []
t0 = time.time()
results = crawl_places_parallel(
    keywords,
    count_per=300,
    max_workers=3,
    emit_log=lambda m: logs.append(m),
    save_batch=lambda *a, **k: None,
)
elapsed = time.time() - t0

print(f"=== 3봇 병렬 + 역수집 ({elapsed:.0f}초) ===")
print(f"총 수집(중복제거): {len(results)}개\n")

by_kw = Counter(r.get("search_keyword", "?") for r in results)
print("[구별 수집]")
for kw in keywords:
    sub = [r for r in results if r.get("search_keyword") == kw]
    st = sum(1 for r in sub if r.get("nearby_station"))
    print(f"  {kw:<12} {len(sub)}개 (근처역 {st}개)")

bad = [m for m in logs if any(t in m for t in ("실패", "차단", "오류", "429", "제한", "비정상", "예외"))]
print(f"\n[차단/에러 로그] {len(bad)}건")
for m in bad[:10]:
    print(f"  {m}")
if not bad:
    print("  없음 ✅")

wrong = sum(1 for r in results if r.get("search_keyword", "").split()[0] not in (r.get("구") or ""))
st_total = sum(1 for r in results if r.get("nearby_station"))
print(f"\n구 불일치: {wrong}개")
print(f"근처역 채워짐: {st_total}/{len(results)} ({st_total*100//max(1,len(results))}%)")

print("\n[샘플 9개]")
for r in results[:9]:
    print(f"  {r['name'][:18]:<18} | {r.get('구')} | {r.get('nearby_station_text') or '역없음'}")
