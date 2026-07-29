# -*- coding: utf-8 -*-
"""[QA] 상세에서 근처 역 추출 — 인코딩 수정 후 여러 업체 검증."""
import io, sys, time, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from naver_crawler import build_mobile_headers, extract_apollo_state, fetch_all_places


def fetch_nearby_station(place_id: str, timeout: int = 15) -> dict:
    """업체 상세에서 가장 가까운 지하철역 정보 추출."""
    try:
        r = requests.get(f"https://m.place.naver.com/place/{place_id}/home",
                         headers=build_mobile_headers(), timeout=timeout)
        r.encoding = "utf-8"   # 상세 페이지 charset 미선언 → UTF-8 강제
        if r.status_code != 200 or len(r.text) < 5000:
            return {}
        state = extract_apollo_state(r.text)
    except Exception:
        return {}

    for obj in state.values():
        if isinstance(obj, dict) and obj.get("__typename") == "SubwayStationInfo":
            name = (obj.get("displayName") or obj.get("name") or "").strip()
            if name and not name.endswith("역"):
                name += "역"
            return {
                "station": name,
                "exit": str(obj.get("nearestExit") or "").strip(),
                "distance_m": obj.get("walkingDistance"),
                "walk_min": obj.get("walkTime"),
                "lat": obj.get("lat"),
                "lng": obj.get("lng"),
            }
    return {}


kw = sys.argv[1] if len(sys.argv) > 1 else "강남구 헬스장"
places = fetch_all_places(kw, count=8, sleep_range=(0.4, 0.8))
print(f"[{kw}] 업체 {len(places)}개 상세에서 근처 역 추출\n")
hit = 0
for p in places:
    s = fetch_nearby_station(p["place_id"])
    if s.get("station"):
        hit += 1
        print(f"  {p['name'][:22]:<22} → {s['station']} {s['exit']}번출구 {s['distance_m']}m (도보 {s['walk_min']}분)")
    else:
        print(f"  {p['name'][:22]:<22} → (역정보 없음)")
    time.sleep(1.0)
print(f"\n추출 성공: {hit}/{len(places)}")
