# -*- coding: utf-8 -*-
"""[QA] 업체 상세에서 '근처 역+거리' 추출 + IP 차단 부하 테스트.

1) 검색으로 업체 N개 id 확보
2) 각 상세(m.place.naver.com/place/{id}/home) 연속 요청
3) subway_exit_distance_text / SubwayStation 추출
4) 성공률 + 차단(비정상 응답) 발생 여부 측정
"""
import io, sys, re, time, random, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from naver_crawler import build_mobile_headers, extract_apollo_state, fetch_all_places

kw = sys.argv[1] if len(sys.argv) > 1 else "강남구 헬스장"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 50
DELAY = (float(sys.argv[3]) if len(sys.argv) > 3 else 0.3)  # 일부러 짧게 줘서 차단 유발 테스트

places = fetch_all_places(kw, count=N, sleep_range=(0.3, 0.6))
print(f"검색 확보: {len(places)}개 / 상세 {min(N,len(places))}개 연속 요청 (딜레이 {DELAY}s)\n")


def extract_subway(state: dict):
    """Apollo 상태에서 가장 가까운 역 텍스트/역명 추출."""
    best_text, best_name, best_dist = "", "", 10**9
    for obj in state.values():
        if not isinstance(obj, dict):
            continue
        # 1) subway_exit_distance_text 류 직접 텍스트
        for k, v in obj.items():
            if "subway" in k.lower() and "distance" in k.lower() and isinstance(v, str) and v:
                if not best_text:
                    best_text = v
        # 2) SubwayStation 타입: 역명 + 거리
        if obj.get("__typename") in ("SubwayStation", "SubwayStationInfo"):
            nm = obj.get("name") or obj.get("stationName") or ""
            d = obj.get("distance") or obj.get("walkingDistance") or 0
            try:
                d = int(re.sub(r"[^\d]", "", str(d)) or 0)
            except Exception:
                d = 0
            if nm and (d and d < best_dist or not best_name):
                best_name, best_dist = nm, d or best_dist
    return best_text, best_name, best_dist


ok = 0
blocked = 0
station_found = 0
samples = []
for i, p in enumerate(places[:N], 1):
    pid = p["place_id"]
    if not pid:
        continue
    try:
        r = requests.get(f"https://m.place.naver.com/place/{pid}/home",
                         headers=build_mobile_headers(), timeout=15, allow_redirects=True)
        body = r.text
        # 차단 징후
        if r.status_code != 200 or len(body) < 5000 or "captcha" in body.lower() or "비정상" in body or "이용이 제한" in body:
            blocked += 1
            print(f"[{i}] ⚠️ 차단/비정상: status={r.status_code} len={len(body)}")
            continue
        ok += 1
        state = extract_apollo_state(body)
        text, name, dist = extract_subway(state)
        if text or name:
            station_found += 1
            if len(samples) < 12:
                samples.append((p["name"], text or f"{name} {dist}m"))
    except Exception as e:
        blocked += 1
        print(f"[{i}] ERR {str(e)[:50]}")
    time.sleep(random.uniform(DELAY, DELAY + 0.3))

print(f"\n=== 결과 ({ok+blocked}건 요청) ===")
print(f"정상 응답   : {ok}")
print(f"차단/실패   : {blocked}")
print(f"역정보 추출 : {station_found}/{ok}")
print(f"\n[근처 역 샘플]")
for nm, st in samples:
    print(f"  {nm[:24]:<24} → {st}")
