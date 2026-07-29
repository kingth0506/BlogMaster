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
try:
    p.driver.get(p.BLOG_WRITE_URL.format(blog_id="todayisgood77"))
except Exception as e:
    print("이동중 알림:", e)
    try: p.driver.switch_to.alert.accept()
    except Exception: pass
    try: p.driver.get(p.BLOG_WRITE_URL.format(blog_id="todayisgood77"))
    except Exception: pass
time.sleep(2)
print(">>> URL:", p.driver.current_url)
print(">>> 글쓰기 페이지 열림. 우측상단 '발행' → '예약 1건' 확인하세요. (15분 열어둠)")
time.sleep(900)
