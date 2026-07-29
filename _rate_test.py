# -*- coding: utf-8 -*-
"""[QA] 상세 엔드포인트 IP 차단 안전 속도 탐색.

느린 딜레이 → 빠른 딜레이 순으로 배치를 돌리며 429 발생 여부 측정.
첫 429가 나오는 배치 직전 딜레이가 '안전선'.
차단 감지 즉시 전체 중단(IP 보호).
"""
import io, sys, time, random, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from naver_crawler import build_mobile_headers, fetch_all_places

kw = "관악구 헬스장"
places = [p for p in fetch_all_places(kw, count=400, sleep_range=(0.4, 0.8)) if p.get("place_id")]
ids = [p["place_id"] for p in places]
print(f"테스트용 업체 id {len(ids)}개 확보\n")

DELAYS = [2.5, 2.0, 1.5, 1.0, 0.7]
BATCH = 20
idx = 0
safe = None

for delay in DELAYS:
    ok = blocked = 0
    t0 = time.time()
    for _ in range(BATCH):
        pid = ids[idx % len(ids)]
        idx += 1
        try:
            r = requests.get(f"https://m.place.naver.com/place/{pid}/home",
                             headers=build_mobile_headers(), timeout=15)
            if r.status_code == 429 or len(r.text) < 5000:
                blocked += 1
            else:
                ok += 1
        except Exception:
            blocked += 1
        time.sleep(delay + random.uniform(0, 0.2))
    elapsed = time.time() - t0
    rpm = BATCH / elapsed * 60
    print(f"[딜레이 {delay}s] {BATCH}건 → 정상 {ok} / 차단 {blocked}  (~{rpm:.0f}req/min)")
    if blocked > 0:
        print(f"  ⚠️ {delay}s에서 차단 발생 → 안전선은 직전 딜레이({safe}s)")
        break
    safe = delay
    time.sleep(5)  # 배치 간 휴식

print(f"\n=== 결론 ===")
if safe and blocked == 0:
    print(f"테스트한 {DELAYS}s 전부 차단 없음 → {safe}s 이하도 가능할 수 있음(더 빠르게 테스트 가능)")
elif safe:
    print(f"안전 딜레이: {safe}s 이상 권장 (그보다 빠르면 429 위험)")
else:
    print(f"가장 느린 {DELAYS[0]}s에서도 차단 → IP가 아직 쿨다운 중이거나 임계가 더 느림")
