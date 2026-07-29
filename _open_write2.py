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
p.start_browser(); p.login()
try:
    p.driver.get(p.BLOG_WRITE_URL.format(blog_id="todayisgood77"))
except Exception:
    try: p.driver.switch_to.alert.accept()
    except Exception: pass
time.sleep(3)
# '예약 발행 N건' 버튼 클릭 → 예약 목록 표시
try:
    clicked = p.driver.execute_script(r"""
      const all = Array.from(document.querySelectorAll('button, a, span'));
      const b = all.find(x => /예약\s*발행\s*\d+\s*건|\d+\s*건/.test((x.textContent||'').trim()) && x.offsetParent);
      if(b){ (b.closest('button')||b).click(); return (b.textContent||'').trim().slice(0,25); }
      return null;
    """)
    print(">>> 예약버튼 클릭:", clicked)
except Exception as e:
    print(">>> 클릭 예외:", e)
time.sleep(2)
print(">>> 예약 목록 열림. 15분 열어둡니다.")
time.sleep(900)
