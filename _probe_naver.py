# -*- coding: utf-8 -*-
"""네이버 이웃신청 관리 / 댓글 페이지 HTML 덤프 (셀렉터 분석용).
사용법:  python _probe_naver.py todayisgood77
  - chrome_profile/<blog_id> 의 로그인 세션을 그대로 재사용 (재로그인 X)
  - 충돌 방지 위해 프로필을 임시폴더로 복사해서 사용
결과: _probe_*.html 파일들 생성 → 그걸 보고 셀렉터 작성
"""
import sys, os, time, shutil, tempfile, json
import undetected_chromedriver as uc

blog_id = sys.argv[1] if len(sys.argv) > 1 else "todayisgood77"
HERE = os.path.dirname(os.path.abspath(__file__))
src_profile = os.path.join(HERE, "chrome_profile", blog_id)
if not os.path.isdir(src_profile):
    print("프로필 없음:", src_profile); sys.exit(1)

# 잠금 충돌 방지: 프로필 복사본 사용
tmp_profile = os.path.join(tempfile.gettempdir(), f"probe_profile_{blog_id}")
shutil.rmtree(tmp_profile, ignore_errors=True)
print("프로필 복사 중...")
shutil.copytree(src_profile, tmp_profile, ignore=shutil.ignore_patterns("Singleton*", "lockfile"))

import subprocess, re as _re
def _chrome_major():
    for path in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
        try:
            out = subprocess.check_output([path, "--version"], timeout=5, stderr=subprocess.DEVNULL)
            m = _re.search(r"(\d+)\.", out.decode(errors="ignore"))
            if m:
                return int(m.group(1))
        except Exception:
            continue
    return 149
ver = _chrome_major()
print("Chrome 버전:", ver)

o = uc.ChromeOptions()
o.add_argument(f"--user-data-dir={tmp_profile}")
o.add_argument("--window-size=1300,950")
o.add_argument("--mute-audio")
try:
    d = uc.Chrome(options=o, use_subprocess=True, version_main=ver)
except Exception as _e:
    print("version_main 재시도:", str(_e)[:80])
    d = uc.Chrome(options=o, use_subprocess=True)

def dump(name, url, wait=4.0):
    try:
        d.get(url); time.sleep(wait)
        html = d.page_source
        # iframe 안 내용도 같이 (네이버 관리화면은 iframe 많음)
        frames = d.find_elements("tag name", "iframe")
        for i, fr in enumerate(frames):
            try:
                d.switch_to.frame(fr); time.sleep(0.6)
                html += f"\n<!-- ===== IFRAME {i} ===== -->\n" + d.page_source
                d.switch_to.default_content()
            except Exception:
                d.switch_to.default_content()
        open(os.path.join(HERE, f"_probe_{name}.html"), "w", encoding="utf-8").write(html)
        print(f"[OK] {name}: {d.current_url}  ({len(html)} bytes)")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")

# ── 이웃신청 관리(받은 신청) 후보들 ──
dump("admin_home", f"https://admin.blog.naver.com/{blog_id}?Redirect=Manage")
dump("buddy_manage", f"https://admin.blog.naver.com/{blog_id}/buddy/MutualBuddyList.naver")
dump("buddy_invite", f"https://admin.blog.naver.com/BuddyInviteManageForm.naver?blogId={blog_id}")
dump("buddy_accept", f"https://blog.naver.com/BuddyAcceptForm.naver?blogId={blog_id}")
# ── 댓글 관리 ──
dump("comment_manage", f"https://admin.blog.naver.com/{blog_id}/comment/CommentList.naver")
dump("blog_home", f"https://blog.naver.com/{blog_id}")

try:
    d.quit()
except Exception:
    pass
print("\n완료 — _probe_*.html 파일들 확인")
