# -*- coding: utf-8 -*-
"""6번 검증 — peek_reservations + schedule_time 계산이 마지막 예약 이후로 잡히는지.
실제 글은 안 올림. 시간 계산만 시뮬레이션."""
import sys, os, io, json, time, datetime as _dt
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from naver_poster import NaverBlogPoster

cfg = json.load(open('config.json', 'r', encoding='utf-8'))
acc = cfg.get('accounts_by_user', {}).get('kidth1', [])[0]

print(f"=== 6번 검증 — naver_id={acc['naver_id']}, blog_id={acc['blog_id']} ===\n")

poster = NaverBlogPoster(
    naver_id=acc["naver_id"], naver_pw=acc["naver_pw"], blog_id=acc["blog_id"],
    headless=False, window_x=80, window_y=80, window_w=1100, window_h=800,
)
try:
    print("[1] 브라우저 + 로그인...")
    poster.start_browser()
    if not poster.login():
        print("로그인 실패")
        sys.exit(1)

    print("[2] peek_reservations 호출")
    t0 = time.time()
    existing = poster.peek_reservations()
    print(f"  ({time.time()-t0:.1f}초) 기존 예약: {[d.strftime('%Y-%m-%d %H:%M') for d in existing]}")

    # === main.py 워커 로직 시뮬레이션 ===
    base_time = _dt.datetime.now()
    first_immediate = True

    # 체크박스 켜진 상태 가정
    if existing:
        latest = max(existing)
        print(f"  가장 늦은 예약: {latest.strftime('%Y-%m-%d %H:%M')}")
        if latest > base_time:
            base_time = latest
            first_immediate = False
            print(f"  → base_time을 {base_time.strftime('%Y-%m-%d %H:%M')}로 조정")

    # 5개 글 예약 시뮬레이션 (2시간 간격)
    print("\n[3] 새 글 5개 예약 시간 시뮬레이션 (2시간 간격):")
    interval_sec = 2 * 3600
    running_dt = base_time
    total = 5
    for i in range(1, total + 1):
        if i == 1 and first_immediate:
            print(f"  [{i}/{total}] 즉시 발행")
            continue
        running_dt = running_dt + _dt.timedelta(seconds=interval_sec)
        sched = running_dt
        # 10분 단위 반올림
        minute = (sched.minute // 10) * 10
        sched = sched.replace(minute=minute, second=0, microsecond=0)
        if sched <= _dt.datetime.now():
            sched += _dt.timedelta(minutes=10)
        print(f"  [{i}/{total}] 예약 시간: {sched.strftime('%Y-%m-%d %H:%M')}")

    # 검증
    print("\n[4] 검증")
    if existing:
        latest = max(existing)
        # 첫 새 예약이 latest 이후인지
        first_new = latest + _dt.timedelta(seconds=interval_sec)
        first_new_rounded = first_new.replace(minute=(first_new.minute // 10) * 10, second=0, microsecond=0)
        if first_new_rounded > latest:
            print(f"  ✅ 첫 새 예약({first_new_rounded.strftime('%H:%M')}) > 마지막 기존 예약({latest.strftime('%H:%M')})")
        else:
            print(f"  ❌ 첫 새 예약이 기존 예약보다 같거나 이전")
finally:
    time.sleep(2)
    try: poster.driver.quit()
    except: pass
