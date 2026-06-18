"""단일 크롤 테스트 — 병렬 없이 Chrome 혼자"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from places_crawler import crawl_places

def _progress(collected, scanned, msg, results):
    if collected % 5 == 0 or msg.startswith("오류"):
        print(f"  수집 {collected} / 스캔 {scanned}: {msg}", flush=True)

start = time.time()
r = crawl_places("서울 강동구 변호사", count=20, on_progress=_progress,
                 existing_places=[], exclude_keywords=[])
elapsed = time.time() - start
print(f"\n=== 단일 크롤 결과: {len(r)}개 / {elapsed:.1f}초 ===")
for p in r[:5]:
    print(f"  - {p.get('name')} | {p.get('address')}")
