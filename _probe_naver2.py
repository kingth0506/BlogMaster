# -*- coding: utf-8 -*-
"""네이버 로그인까지 하고 이웃관리/댓글 페이지 덤프 (프로그램의 NaverBlogPoster 재사용).
사용법:  python _probe_naver2.py todayisgood77
캡차/기기인증 뜨면 직접 풀어주세요 (그 계정 프로필에 세션 저장됨).
"""
import sys, os, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from naver_poster import NaverBlogPoster

target = sys.argv[1] if len(sys.argv) > 1 else "todayisgood77"
cfg = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
acc = None
for a in cfg.get("accounts", []):
    if a.get("blog_id") == target:
        acc = a; break
if not acc:
    print("계정 못찾음:", target); sys.exit(1)

nid, npw, bid = acc.get("naver_id"), acc.get("naver_pw"), acc.get("blog_id")
print("계정:", bid)

poster = NaverBlogPoster(nid, npw, bid)
poster.start_browser()          # 드라이버 생성 (이게 빠졌었음)
ok = poster.login()
print("로그인 결과:", ok)
d = poster.driver
if d is None:
    print("드라이버 생성 실패 — 중단"); sys.exit(1)

def dump(name, url, wait=4.0):
    try:
        d.get(url); time.sleep(wait)
        html = d.page_source
        for i, fr in enumerate(d.find_elements("tag name", "iframe")):
            try:
                d.switch_to.frame(fr); time.sleep(0.5)
                html += "\n<!-- IFRAME %d -->\n" % i + d.page_source
                d.switch_to.default_content()
            except Exception:
                d.switch_to.default_content()
        open(os.path.join(HERE, "_probe_%s.html" % name), "w", encoding="utf-8").write(html)
        print("[OK] %s : %s (%d bytes)" % (name, d.current_url, len(html)))
    except Exception as e:
        print("[FAIL] %s : %s" % (name, str(e)[:100]))

# ── 서로이웃 받은 신청 (SPA route + iframe 내용) ──
dump("buddy_me", "https://admin.blog.naver.com/%s/buddy/me" % bid)
dump("buddy_manage", "https://admin.blog.naver.com/%s/buddy/manage" % bid)
# 직접 iframe 내용 URL
dump("buddy_received_direct", "https://admin.blog.naver.com/BuddyInviteReceivedManage.naver?blogId=%s" % bid)
dump("buddy_list_direct", "https://admin.blog.naver.com/BuddyListManage.naver?blogId=%s" % bid)
# ── 댓글 ──
dump("comment_spa", "https://admin.blog.naver.com/%s/userfilter/commentlist" % bid)
dump("comment_direct", "https://admin.blog.naver.com/AdminCommentFilteredView.naver?blogId=%s" % bid)

try:
    poster.close()
except Exception:
    pass
print("done")
