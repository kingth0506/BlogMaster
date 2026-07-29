# -*- coding: utf-8 -*-
"""[QA] Throttle 우회 2대책 결정론적 검증 (네트워크 無 / crawl_places 목킹).

대책1) 구>=10 이면 자동 2봇 하향, 미만이면 설정 봇 유지.
대책2) 메인 크롤 후 '딱 5개'에서 멈춘 차단 의심 구만 순차 1회 재시도해 복구.
"""
import io, sys, time, threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import places_crawler as pc
from places_crawler import (
    crawl_places_parallel, SIDO_DISTRICTS,
    THROTTLE_DISTRICT_THRESHOLD, THROTTLE_SAFE_WORKERS, STRAGGLER_TRIP_COUNT,
)

PASS, FAIL = "✅ PASS", "❌ FAIL"


def make_mock(blocked_first_pass):
    """crawl_places 목 생성.
    - 동시 호출 수(실제 봇 수) 추적
    - blocked_first_pass에 든 구는 1차엔 딱 5개로 잘리고, 재시도(existing 5개 전달)땐 30개로 복구
    """
    state = {"active": 0, "max_active": 0, "first_seen": set()}
    lock = threading.Lock()

    def mock(keyword, count, on_progress=None, existing_places=None,
             exclude_keywords=None, no_filter=False, on_item=None,
             stop_flag=lambda: False, emit_log=None, **kw):
        with lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        try:
            time.sleep(0.03)  # 동시성 관찰용 짧은 작업시간
            existing = list(existing_places or [])
            is_retry = len(existing) >= STRAGGLER_TRIP_COUNT  # 재시도 호출 식별
            with lock:
                first = keyword not in state["first_seen"]
                state["first_seen"].add(keyword)

            if keyword in blocked_first_pass and first and not is_retry:
                n = STRAGGLER_TRIP_COUNT          # 1차: 차단으로 딱 5개에서 잘림
                base = 0
            else:
                n = 30                            # 정상 구 or 재시도 복구: 30개
                base = len(existing)
            out = list(existing)
            for i in range(base, n):
                out.append({"name": f"{keyword}_업체{i+1}", "구": keyword.split()[1]})
            return out
        finally:
            with lock:
                state["active"] -= 1
    return mock, state


# ThreadPoolExecutor를 가로채 엔진이 실제 결정한 봇 수를 정확히 포착
# (스태거 타이밍에 흔들리지 않는 결정론적 측정)
import concurrent.futures as _cf
_orig_tpe = _cf.ThreadPoolExecutor
_captured = {"workers": None}

class _SpyTPE(_orig_tpe):
    def __init__(self, max_workers=None, *a, **k):
        _captured["workers"] = max_workers
        super().__init__(max_workers=max_workers, *a, **k)


def run_case(title, keywords, max_workers, blocked):
    mock, state = make_mock(set(blocked))
    orig_cp = pc.crawl_places
    pc.crawl_places = mock
    _cf.ThreadPoolExecutor = _SpyTPE
    _captured["workers"] = None
    logs = []
    try:
        res = crawl_places_parallel(
            keywords, count_per=300, max_workers=max_workers,
            emit_log=logs.append, save_batch=lambda *a, **k: None,
        )
    finally:
        pc.crawl_places = orig_cp
        _cf.ThreadPoolExecutor = _orig_tpe
    state["engine_workers"] = _captured["workers"]
    from collections import Counter
    by_kw = Counter(r.get("search_keyword", "?") for r in res)
    print(f"\n=== {title} ===")
    print(f"  요청 봇={max_workers} / 엔진 실제 봇 수={state['engine_workers']}")
    print(f"  총 수집={len(res)}개, 구={len(keywords)}개")
    return res, by_kw, state, logs


fails = 0

# ── 케이스 A: 서울 25구, 3봇 요청 → 자동 2봇 + 7구 차단 복구 ──────────────
seoul = [f"서울 {g} 헬스장" for g in SIDO_DISTRICTS["서울"]]
blocked7 = seoul[:7]
res, by_kw, state, logs = run_case("A) 서울 25구 · 3봇요청 · 7구 차단", seoul, 3, blocked7)

# 검증1: 자동 봇조절 (3 → 2)
ok = state["engine_workers"] == THROTTLE_SAFE_WORKERS
print(f"  [대책1 자동봇조절] 엔진 봇 수 {state['engine_workers']} == {THROTTLE_SAFE_WORKERS}  {PASS if ok else FAIL}")
fails += 0 if ok else 1

throttle_log = any("자동 하향" in m for m in logs)
print(f"  [대책1 로그] '자동 하향' 메시지 출력  {PASS if throttle_log else FAIL}")
fails += 0 if throttle_log else 1

# 검증2: 스트래글러 복구 — 차단됐던 7구가 5개→30개로 살아났는지
recovered_all = all(by_kw.get(k, 0) == 30 for k in blocked7)
cut = [k for k in seoul if by_kw.get(k, 0) == STRAGGLER_TRIP_COUNT]
print(f"  [대책2 복구] 7개 차단구 전부 30개로 복구  {PASS if recovered_all else FAIL}  (잔여 5개구={len(cut)})")
fails += 0 if recovered_all else 1

retry_log = any("스트래글러 복구" in m and "순차 재시도" in m for m in logs)
print(f"  [대책2 로그] '스트래글러 복구' 재시도 메시지  {PASS if retry_log else FAIL}")
fails += 0 if retry_log else 1

# ── 케이스 B: 구 3개, 3봇 요청 → 하향 없이 3봇 유지 ──────────────────────
few = ["서울 강남구 카페", "서울 서초구 카페", "서울 송파구 카페"]
res2, by_kw2, state2, logs2 = run_case("B) 3구 · 3봇요청 · 차단없음", few, 3, [])
ok_keep = state2["engine_workers"] == 3
print(f"  [대책1 유지] 3구는 3봇 유지(엔진 봇 수={state2['engine_workers']})  {PASS if ok_keep else FAIL}")
fails += 0 if ok_keep else 1
no_retry = any("차단 의심 구 없음" in m for m in logs2)
print(f"  [대책2] 차단 없으니 재시도 스킵  {PASS if no_retry else FAIL}")
fails += 0 if no_retry else 1

# ── 케이스 C: 경계값 — 정확히 10구면 하향 발동 ───────────────────────────
ten = [f"경기 지역{i} 미용실" for i in range(THROTTLE_DISTRICT_THRESHOLD)]
res3, by_kw3, state3, logs3 = run_case(f"C) 경계값 {THROTTLE_DISTRICT_THRESHOLD}구 · 3봇요청", ten, 3, [])
ok_edge = state3["engine_workers"] == THROTTLE_SAFE_WORKERS
print(f"  [대책1 경계] {THROTTLE_DISTRICT_THRESHOLD}구에서 하향 발동(엔진 봇 수={state3['engine_workers']})  {PASS if ok_edge else FAIL}")
fails += 0 if ok_edge else 1

print("\n" + "=" * 50)
print(f"QA 최종: {'전체 통과 ✅' if fails == 0 else f'{fails}건 실패 ❌'}")
sys.exit(1 if fails else 0)
