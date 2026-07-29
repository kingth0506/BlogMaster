# -*- coding: utf-8 -*-
import sys, os, json, time
sys.stdout.reconfigure(encoding="utf-8")
from naver_poster import NaverBlogPoster
_ad = os.environ.get("APPDATA") or os.path.expanduser("~")
cfgpath = os.path.join(_ad, "NaverBlogAuto", "config.json")
if not os.path.exists(cfgpath): cfgpath = "config.json"
raw = json.load(open(cfgpath, encoding="utf-8"))
abu = raw.get("accounts_by_user", {}) or {}
acc = next((a for a in (abu.get("kidth1") or []) if a.get("blog_id")=="todayisgood77" and a.get("naver_id")), None)
if not acc:
    print("계정 못찾음"); sys.exit(1)
p = NaverBlogPoster(acc["naver_id"], acc["naver_pw"], "todayisgood77", headless=False)
p.start_browser()
p.login()
try:
    res = p.get_existing_reservations()
    print(">>> 예약 목록 시간:", res)
except Exception as e:
    print(">>> 예약목록 읽기 시도 중 예외:", e)
    try:
        p.driver.get(p.BLOG_WRITE_URL.format(blog_id="todayisgood77"))
    except Exception:
        pass
print(">>> 브라우저를 15분간 열어둡니다. 예약 글 확인 후 삭제하세요.")
time.sleep(900)
