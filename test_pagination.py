# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"C:\Mac\Home\Desktop\program\블로그마스터")
from places_crawler import crawl_places

results = crawl_places(
    "서울 강남구 헬스장", count=40,
    emit_log=lambda m: print(m, flush=True),
    on_progress=lambda cur, scanned, name, res: print(f"[{cur}] {name}", flush=True),
    stop_flag=lambda: False,
    profile_dir=r"C:\Mac\Home\Desktop\program\블로그마스터\chrome_profile\todayisgood77",
    force_visible=True,
)
print(f"\n=== 최종: {len(results)}개 ===")
for r in results:
    print(f"{r['index']}. {r['name']}")
