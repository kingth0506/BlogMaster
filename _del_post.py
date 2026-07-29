# -*- coding: utf-8 -*-
import sys, os, json, time
sys.stdout.reconfigure(encoding="utf-8")
from naver_poster import NaverBlogPoster
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
_ad = os.environ.get("APPDATA") or os.path.expanduser("~")
cfgpath = os.path.join(_ad, "NaverBlogAuto", "config.json")
if not os.path.exists(cfgpath): cfgpath = "config.json"
raw = json.load(open(cfgpath, encoding="utf-8"))
abu = raw.get("accounts_by_user", {}) or {}
acc = next((a for a in (abu.get("kidth1") or []) if a.get("blog_id")=="todayisgood77" and a.get("naver_id")), None)
LOGNO = "224349466892"
p = NaverBlogPoster(acc["naver_id"], acc["naver_pw"], "todayisgood77", headless=False)
p.start_browser(); p.login()
p.driver.get(f"https://blog.naver.com/PostView.naver?blogId=todayisgood77&logNo={LOGNO}")
time.sleep(4)
r = p.driver.execute_script(r"""
  function f(re){ return Array.from(document.querySelectorAll('a,button,span')).find(function(x){return re.test((x.textContent||'').trim()) && x.getBoundingClientRect().width>0;}); }
  var del = f(/^삭제$/);
  if(del){ (del.closest('a')||del.closest('button')||del).click(); return 'clicked'; }
  return 'no-btn';
""")
print(">>> 삭제 클릭:", r)
# confirm/추가 alert 순차 수락
for i in range(4):
    try:
        WebDriverWait(p.driver, 4).until(EC.alert_is_present())
        a = p.driver.switch_to.alert
        print(f">>> alert[{i}]:", (a.text or "")[:40])
        a.accept()
        time.sleep(1.5)
    except Exception:
        break
time.sleep(3)
# 삭제 검증: 글 URL 다시 열어 "삭제되었거나" 뜨면 삭제 성공
p.driver.get(f"https://blog.naver.com/todayisgood77/{LOGNO}")
time.sleep(3)
gone = False
try:
    WebDriverWait(p.driver, 3).until(EC.alert_is_present())
    at = p.driver.switch_to.alert.text
    print(">>> 확인 alert:", at[:40]); p.driver.switch_to.alert.accept()
    if "삭제" in at or "없" in at: gone = True
except Exception:
    pass
print(">>> 삭제됨?" , gone, "| URL:", p.driver.current_url)
time.sleep(30)
