# -*- coding: utf-8 -*-
"""[QA] 네이버 플레이스 데이터에 '근처 역' 정보가 들어있는지 탐색.

HTML Apollo 상태의 PlaceListBusinessesItem 전체 필드를 덤프해서
subway / station / x / y / 역 관련 필드가 있는지 확인.
"""
import io, sys, json, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from naver_crawler import build_mobile_headers, extract_apollo_state, SEARCH_URL

kw = sys.argv[1] if len(sys.argv) > 1 else "동작구 헬스장"
resp = requests.get(SEARCH_URL, params={"query": kw}, headers=build_mobile_headers(), timeout=15)
state = extract_apollo_state(resp.text)

items = [v for v in state.values()
         if isinstance(v, dict) and v.get("__typename") == "PlaceListBusinessesItem"]
print(f"PlaceListBusinessesItem: {len(items)}개\n")

if items:
    it = items[0]
    print(f"=== 첫 업체 '{it.get('name')}' 전체 필드 ===")
    for k, v in it.items():
        print(f"  {k:<22} = {repr(v)[:90]}")

    # 역/좌표 관련 키만 추출
    print("\n=== 역/좌표 후보 필드 (전 업체 통합) ===")
    keys = set()
    for it in items:
        keys.update(it.keys())
    hit = [k for k in sorted(keys)
           if any(t in k.lower() for t in ("subway","station","metro","x","y","coord","lng","lat","dist","near","road"))
           or "역" in k]
    print("  ", hit)
    # subway/station 값 샘플
    for it in items[:6]:
        sub = {k: it.get(k) for k in it if any(t in k.lower() for t in ("subway","station")) or "역" in k}
        print(f"  {it.get('name')[:18]:<18} {sub}")
