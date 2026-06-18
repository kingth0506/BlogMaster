"""병렬 크롤 테스트 — 3개 구를 동시에 실제로 수집되는지 확인"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')

from places_crawler import crawl_places_parallel

def _log(msg):
    print(f"[LOG] {msg}", flush=True)

def _progress(collected, scanned, msg, results):
    pass  # 너무 많이 찍힘

keywords = [
    "서울 강동구 변호사", "서울 강북구 변호사", "서울 강서구 변호사",
    "서울 구로구 변호사", "서울 관악구 변호사", "서울 광진구 변호사",
]

start = time.time()
results = crawl_places_parallel(
    keywords,
    count_per=50,
    on_progress=_progress,
    existing_places=[],
    exclude_keywords=[],
    max_workers=3,
    stop_flag=lambda: False,
    emit_log=_log,
)
elapsed = time.time() - start

print(f"\n========================================")
print(f"총 소요: {elapsed:.1f}초")
print(f"총 수집: {len(results)}개")
from collections import Counter
by_kw = Counter(p.get("search_keyword", "?") for p in results)
for kw, n in by_kw.items():
    print(f"  {kw}: {n}개")
print(f"========================================")
