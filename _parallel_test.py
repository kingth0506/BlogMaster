# -*- coding: utf-8 -*-
"""[QA] 3방향 병렬 크롤 안전성 — crawl_places_parallel(max_workers=3)."""
import io, sys, time
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from places_crawler import crawl_places_parallel

keywords = ["관악구 헬스장", "동작구 헬스장", "강남구 헬스장"]
logs = []
def emit(m):
    logs.append(m)

t0 = time.time()
results = crawl_places_parallel(
    keywords,
    count_per=300,          # 구별 풀크롤(상한까지)
    max_workers=3,          # 3봇 동시
    emit_log=emit,
    save_batch=lambda *a, **k: None,
)
elapsed = time.time() - t0

print(f"=== 3봇 병렬 크롤 결과 ({elapsed:.0f}초) ===")
print(f"총 수집(중복제거): {len(results)}개\n")

# 키워드(구)별 분포
by_kw = Counter(r.get("search_keyword","?") for r in results)
print("[구별 수집]")
for kw in keywords:
    print(f"  {kw:<12} {by_kw.get(kw,0)}개")

# 차단/에러 흔적
bad = [m for m in logs if any(t in m for t in ("실패","차단","오류","429","제한","비정상","예외"))]
print(f"\n[차단/에러 로그] {len(bad)}건")
for m in bad[:10]:
    print(f"  {m}")
if not bad:
    print("  없음 ✅")

# 구 정합성
wrong = sum(1 for r in results if r.get("search_keyword","").split()[0] not in (r.get("구") or ""))
print(f"\n구 불일치(검색구≠주소구): {wrong}개")
