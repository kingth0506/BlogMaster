# -*- coding: utf-8 -*-
"""[자가치유+테스트] 업체명에서 역 토큰 추출 → 좌표표에 없으면 채움 → 해당 구 근처역 테스트.

고정 역목록(stations.json/station_locations.json)이 불완전(노원역 누락 등)해서,
실제 크롤한 업체명에 등장하는 '○○역'을 직접 발굴해 station_coords.json을 보강한다.
"""
import io, sys, os, re, json, time, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from naver_crawler import fetch_all_places, fetch_places_html, _load_station_coords

BASE = os.path.dirname(__file__)
OUT = os.path.join(BASE, "station_coords.json")
GU = sys.argv[1] if len(sys.argv) > 1 else "노원구"

coords = json.load(open(OUT, encoding="utf-8"))
before = len(coords)

# 1) 해당 구 헬스장 크롤 (업체명 확보)
places = fetch_all_places(f"{GU} 헬스장", count=400, sleep_range=(0.4, 0.8))
print(f"[{GU} 헬스장] {len(places)}개 수집")

# 2) 업체명에서 역 토큰 추출 ('○○역점','○○역' 등)
tok_re = re.compile(r"([가-힣A-Za-z0-9]{2,10}역)")
tokens = set()
for p in places:
    for m in tok_re.findall(p.get("name") or ""):
        # '지하철역','전철역' 류 일반어 제외
        if m in ("지하철역", "전철역", "기차역"):
            continue
        tokens.add(m)
print(f"업체명에서 발견한 역 토큰: {len(tokens)}개")

# 3) 좌표표에 없는 역만 라이브 지오코딩해서 추가
missing = [t for t in tokens if t not in coords]
print(f"좌표표에 없는 역: {len(missing)}개 → {missing}")
added = 0
for st in missing:
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
            added += 1
            print(f"  + {st} {coords[st]}")
    except Exception as e:
        print(f"  ! {st} 실패 {e}")
    time.sleep(random.uniform(0.4, 0.7))

if added:
    json.dump(coords, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n역좌표 {before} → {len(coords)} (+{added})")

# 4) 캐시 리셋 후 근처역 재계산 테스트
import naver_crawler as nc
nc._STATION_COORDS = None
nc._STATION_NAMES_BY_LEN = None
from naver_crawler import resolve_nearby_station

hit = 0
samples = []
for p in places:
    si = resolve_nearby_station(p.get("name"), p.get("x"), p.get("y"))
    if si.get("station"):
        hit += 1
        if len(samples) < 10:
            samples.append((p["name"], si["station"], si.get("distance_m"), si.get("source")))
print(f"\n[{GU}] 근처역 채워짐: {hit}/{len(places)} ({hit*100//max(1,len(places))}%)")
for nm, st, d, src in samples:
    print(f"  {nm[:22]:<22} → {st} 약 {d}m ({src})")
