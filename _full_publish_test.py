# -*- coding: utf-8 -*-
"""6번 — peek 후 base_time 기반 5개 글 예약 발행 (2시간 간격)"""
import sys, os, io, json, time, datetime as _dt
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from naver_poster import NaverBlogPoster

cfg = json.load(open('config.json', 'r', encoding='utf-8'))
acc = cfg.get('accounts_by_user', {}).get('kidth1', [])[0]
TOTAL = 5
INTERVAL_SEC = 2 * 3600  # 2시간

print(f"=== {TOTAL}개 예약 발행 — naver_id={acc['naver_id']}, blog_id={acc['blog_id']} ===\n")

poster = NaverBlogPoster(
    naver_id=acc["naver_id"], naver_pw=acc["naver_pw"], blog_id=acc["blog_id"],
    headless=False, window_x=80, window_y=80, window_w=1100, window_h=800,
)
try:
    print("[1] 브라우저 + 로그인")
    poster.start_browser()
    if not poster.login():
        print("로그인 실패")
        sys.exit(1)

    print("\n[2] peek_reservations — 마지막 예약 시간 조회")
    existing = poster.peek_reservations()
    if existing:
        latest = max(existing)
        print(f"  기존 예약 {len(existing)}개, 가장 늦음: {latest.strftime('%Y-%m-%d %H:%M')}")
        base_time = latest
    else:
        latest = None
        base_time = _dt.datetime.now()
        print("  기존 예약 없음 — 현재 시각 기준")

    print(f"\n[3] {TOTAL}개 예약 시간 미리 계산 (각 +2시간)")
    schedule_times = []
    running = base_time
    for i in range(TOTAL):
        running = running + _dt.timedelta(seconds=INTERVAL_SEC)
        running = running.replace(minute=(running.minute // 10) * 10, second=0, microsecond=0)
        if running <= _dt.datetime.now():
            running = _dt.datetime.now() + _dt.timedelta(minutes=10)
            running = running.replace(minute=(running.minute // 10) * 10, second=0, microsecond=0)
        schedule_times.append(running.strftime("%Y-%m-%d %H:%M"))
    for i, st in enumerate(schedule_times, 1):
        print(f"  [{i}] {st}")

    print(f"\n[4] {TOTAL}개 글 예약 발행")
    success_count = 0
    for i, sched in enumerate(schedule_times, 1):
        print(f"\n--- [{i}/{TOTAL}] schedule_time={sched} ---")
        t0 = time.time()
        ok = poster.write_post(
            title=f"[테스트{i}] {_dt.datetime.now().strftime('%H%M%S')} {sched}",
            body=f"5개 예약 검증 {i}/{TOTAL}\n예약 시각: {sched}",
            tags=["테스트"],
            image_paths=None,
            category=acc.get("blog_category", ""),
            schedule_time=sched,
        )
        elapsed = time.time() - t0
        print(f"  결과: {'✅ 성공' if ok else '❌ 실패'} ({elapsed:.1f}초)")
        if ok:
            success_count += 1

    print(f"\n[5] 최종 peek로 확인")
    time.sleep(3)
    final = poster.peek_reservations()
    print(f"  현재 예약 ({len(final)}개):")
    for d in sorted(final):
        print(f"    - {d.strftime('%Y-%m-%d %H:%M')}")

    print(f"\n=== 결과 ===")
    print(f"  발행 시도: {TOTAL}개 / 보고된 성공: {success_count}개")
    print(f"  최종 예약 수: {len(final)} (시작 시 {len(existing) if existing else 0}개)")
    print(f"  실제 추가됨: {len(final) - (len(existing) if existing else 0)}개")
finally:
    time.sleep(3)
    try: poster.driver.quit()
    except: pass
