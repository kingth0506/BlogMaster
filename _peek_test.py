# -*- coding: utf-8 -*-
"""peek_reservations 테스트 — kingte0560 (todayisgood77) 예약 시간 조회"""
import sys, os, io, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from naver_poster import NaverBlogPoster

cfg = json.load(open('config.json', 'r', encoding='utf-8'))
acc = cfg.get('accounts_by_user', {}).get('kidth1', [])[0]  # kingte0560 / todayisgood77

print(f"=== peek 테스트 — naver_id={acc['naver_id']}, blog_id={acc['blog_id']} ===\n")
poster = NaverBlogPoster(
    naver_id=acc["naver_id"], naver_pw=acc["naver_pw"], blog_id=acc["blog_id"],
    headless=False, window_x=80, window_y=80, window_w=1100, window_h=800,
)
try:
    print("[1] 브라우저 시작...")
    poster.start_browser()
    print("[2] 로그인...")
    if not poster.login():
        print("로그인 실패")
        sys.exit(1)
    print("[3] peek_reservations 호출...")
    t0 = time.time()
    reservations = poster.peek_reservations()
    elapsed = time.time() - t0
    print(f"\n=== 결과 ({elapsed:.1f}초) ===")
    if not reservations:
        print("예약 글 0개 (또는 조회 실패)")
    else:
        print(f"예약 글 {len(reservations)}개:")
        for r in sorted(reservations):
            print(f"  - {r.strftime('%Y-%m-%d %H:%M')}")
        latest = max(reservations)
        print(f"\n가장 늦은 예약: {latest.strftime('%Y-%m-%d %H:%M')}")
finally:
    time.sleep(3)
    try: poster.driver.quit()
    except: pass
