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
p = NaverBlogPoster(acc["naver_id"], acc["naver_pw"], "todayisgood77", headless=False)
p.start_browser()
p.login()
# 관리 페이지 글목록(예약 포함)으로 이동
p.driver.get("https://blog.naver.com/todayisgood77/224349425466")
time.sleep(3)
print(">>> 현재 URL:", p.driver.current_url)
print(">>> 제목영역:", (p.driver.title or "")[:80])
print(">>> 브라우저 15분 열어둠")
time.sleep(900)
