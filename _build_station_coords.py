# -*- coding: utf-8 -*-
"""[1회성] 역 좌표표 구축 — stations.json 각 역을 검색해 좌표 수집 → station_coords.json.

이후 크롤에서 업체 좌표 ↔ 역 좌표 최단거리로 근처 역을 '즉시' 계산(요청 0).
"""
import io, sys, os, json, time, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from naver_crawler import fetch_places_html

BASE = os.path.dirname(__file__)
OUT = os.path.join(BASE, "station_coords.json")

# 소스: station_locations.json (685개, 깨끗하고 완전 — 강북 등 전부 포함)
stations = list(json.load(open(os.path.join(BASE, "station_locations.json"), encoding="utf-8")).keys())
clean = []
seen = set()
for s in stations:
    s = (s or "").strip()
    if not s.endswith("역") or len(s) < 2:
        continue
    if s in seen:
        continue
    seen.add(s)
    clean.append(s)

print(f"대상 역: {len(clean)}개 (원본 {len(stations)}개)\n")

# 이어하기: 기존 결과 있으면 로드
coords = {}
if os.path.exists(OUT):
    try:
        coords = json.load(open(OUT, encoding="utf-8"))
        print(f"기존 {len(coords)}개 로드(이어하기)")
    except Exception:
        coords = {}

ok = len(coords)
miss_streak = 0
for i, st in enumerate(clean, 1):
    if st in coords:
        continue
    got = False
    for attempt in range(2):
        try:
            rows, _ = fetch_places_html(st)
            pick = None
            for r in rows:
                if st[:-1] in (r.get("name") or "") and r.get("x"):
                    pick = r
                    break
            if not pick and rows and rows[0].get("x"):
                pick = rows[0]
            if pick and pick.get("x") and pick.get("y"):
                coords[st] = [float(pick["x"]), float(pick["y"])]
                ok += 1
                got = True
                break
        except Exception:
            pass
        # 실패 → throttle 의심
        miss_streak += 1
        if miss_streak >= 5:
            json.dump(coords, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
            print(f"  throttle 의심(연속 {miss_streak}) → 90초 쿨다운... ({i}/{len(clean)}, 수집 {ok})")
            time.sleep(90)
            miss_streak = 0
    if got:
        miss_streak = 0
    if i % 25 == 0:
        json.dump(coords, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  {i}/{len(clean)} 진행 (수집 {ok}개)")
    time.sleep(random.uniform(0.5, 0.9))

json.dump(coords, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n완료: {len(coords)}개 역 좌표 저장 → station_coords.json")
print("샘플:", dict(list(coords.items())[:3]))
