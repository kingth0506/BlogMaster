# -*- coding: utf-8 -*-
import sys, json, time
sys.stdout.reconfigure(encoding="utf-8")
from naver_poster import NaverBlogPoster
raw = json.load(open("config.json", encoding="utf-8"))
pool = list(raw.get("accounts", []) or [])
for _u,_l in (raw.get("accounts_by_user") or {}).items(): pool += list(_l or [])
acc = next(a for a in pool if a.get("blog_id")=="todayisgood77" and a.get("naver_id"))
p = NaverBlogPoster(acc["naver_id"], acc["naver_pw"], "todayisgood77", headless=False)
p.start_browser()
p.driver.get("https://nid.naver.com/nidlogin.login")
time.sleep(2.5)
js = r'''
  const s=(v)=>(v||'').toString().slice(0,40);
  const r={};
  r.url = location.href;
  r.id_field = !!document.getElementById('id');
  r.pw_field = !!document.getElementById('pw');
  r.log_login = !!document.getElementById('log.login');
  r.buttons = Array.from(document.querySelectorAll('button, input[type=submit], a[role=button]')).slice(0,15).map(b=>({tag:b.tagName, id:s(b.id), cls:s(b.className), txt:s(b.innerText||b.value), type:s(b.type)}));
  r.forms = Array.from(document.querySelectorAll('form')).map(f=>({id:s(f.id), action:s(f.action)}));
  return JSON.stringify(r);
'''
info = json.loads(p.driver.execute_script(js))
print("DIAG_RESULT_START")
print(json.dumps(info, ensure_ascii=False, indent=1))
print("DIAG_RESULT_END")
