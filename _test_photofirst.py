# -*- coding: utf-8 -*-
"""사진먼저 레이아웃 실발행 테스트 — write_post 직접 호출.
사용: python _test_photofirst.py <blog_id>
본문에 [이미지] 마커를 문단 사이에 넣어도, image_layout=top이면 발행 시 상단으로 몰려야 함.
"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
from naver_poster import NaverBlogPoster

target = sys.argv[1] if len(sys.argv) > 1 else ""
# 설치본 앱이 실제 저장하는 위치: %APPDATA%\NaverBlogAuto\config.json (사장님이 바꾼 비번이 여기 있음)
_appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
cfgpath = os.path.join(_appdata, "NaverBlogAuto", "config.json")
if not os.path.exists(cfgpath):
    cfgpath = "config.json"   # 폴백: 개발 폴더
print(f"config 경로: {cfgpath}")
raw = json.load(open(cfgpath, encoding="utf-8"))
# 비번을 갱신한 앱-유저(kidth1)의 계정을 '우선'으로 읽는다 (인자로 유저 지정 가능)
APP_USER = sys.argv[2] if len(sys.argv) > 2 else "kidth1"
abu = raw.get("accounts_by_user", {}) or {}
acc = next((a for a in (abu.get(APP_USER) or [])
            if a.get("blog_id") == target and a.get("naver_id") and a.get("naver_pw")), None)
if acc is None:
    # 폴백: 전체에서 탐색
    pool = []
    for _u, _lst in abu.items():
        pool += list(_lst or [])
    pool += list(raw.get("accounts", []) or [])
    acc = next((a for a in pool if a.get("blog_id") == target and a.get("naver_id") and a.get("naver_pw")), None)
if acc is None:
    ids = sorted({a.get("blog_id") for a in pool if a.get("blog_id")})
    print(f"계정 못 찾음(config={cfgpath}). 자격증명 있는 blog_id:", ids)
    sys.exit(1)

title = "[테스트] 사진먼저 레이아웃 확인 (삭제예정)"
body = """사진 먼저 배치가 잘 되는지 확인하는 테스트 글입니다.

[이미지]

첫 번째 문단입니다. 원래 여기 사진 마커가 있었지만 상단으로 이동해야 합니다.

두 번째 문단 내용입니다. 글이 사진 아래에 잘 붙는지 봅니다.

[이미지]

세 번째 문단으로 마무리합니다. 확인 후 이 글은 삭제하세요.
"""
imgdir = os.path.join(os.environ.get("TEMP", "."), "photofirst_test")
imgs = [os.path.join(imgdir, f"test{i}.png") for i in (1, 2, 3)]
tags = ["테스트"]

# 즉시발행 (예약 X) — 글이 바로 뜨는지 확실히 확인하려고. 확인 후 삭제 가능.
schedule_time = None

print(f"발행 대상: {acc['blog_id']}  (naver_id={acc.get('naver_id')})")
print(f"예약 시간: {schedule_time}")
p = NaverBlogPoster(acc["naver_id"], acc["naver_pw"], acc["blog_id"], headless=False)
try:
    p.start_browser()
    logged = p.login()
    if not logged:
        # 캡차/2단계 인증 — 크롬 창에서 사용자가 풀 시간을 최대 5분 더 준다
        from selenium.webdriver.common.by import By as _By
        import time as _t
        print(">>> 크롬 창에서 로그인(캡차 포함) 완료해주세요. 최대 5분 대기합니다...", flush=True)
        deadline = _t.time() + 300
        while _t.time() < deadline:
            try:
                p.driver.find_element(_By.CSS_SELECTOR, "a[href*='logout']")
                logged = True
                print(">>> 로그인 확인됨! 발행을 진행합니다.", flush=True)
                break
            except Exception:
                pass
            _t.sleep(3)
    if not logged:
        print("로그인 여전히 미완료 — 중단")
        sys.exit(1)
    ok = p.write_post(title, body, tags, image_paths=imgs, schedule_time=schedule_time)
    print("발행 결과:", "성공" if ok else "실패")
    import time as _t
    _t.sleep(2)
    cur = ""
    try:
        cur = p.driver.current_url
    except Exception:
        pass
    print("발행 후 URL:", cur)
    # 실제로 글이 있는지: 블로그 최근글로 이동해서 확인용으로 열어둠
    try:
        p.driver.get("https://blog.naver.com/todayisgood77")
    except Exception:
        pass
    print(">>> 블로그 열어둠 (2분). 최근글에 [테스트] 사진먼저... 있는지 확인.")
    _t.sleep(120)
except Exception as e:
    import traceback; traceback.print_exc()
    print("오류:", e)
