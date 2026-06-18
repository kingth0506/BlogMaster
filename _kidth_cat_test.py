# -*- coding: utf-8 -*-
"""kidth0506 실제 로그인 → 발행 다이얼로그 → 카테고리 '추천' 선택만 검증 (실제 발행 X)"""
import sys, os, io, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from naver_poster import NaverBlogPoster

cfg = json.load(open('config.json', 'r', encoding='utf-8'))
acc = next(a for a in cfg['accounts'] if a.get('blog_id') == 'kidth0506')
target_cat = "독서"

print(f"=== kidth0506 카테고리 '{target_cat}' 선택 검증 ===\n")

poster = NaverBlogPoster(
    naver_id=acc["naver_id"], naver_pw=acc["naver_pw"], blog_id=acc["blog_id"],
    headless=False, window_x=80, window_y=80, window_w=1200, window_h=850,
)
try:
    print("[1] 브라우저 + 로그인")
    poster.start_browser()
    if not poster.login():
        print("❌ 로그인 실패")
        sys.exit(1)
    print("✅ 로그인 성공")

    print("\n[2] 글쓰기 페이지 이동")
    write_url = poster.BLOG_WRITE_URL.format(blog_id=acc["blog_id"])
    poster.driver.get(write_url)
    time.sleep(3)

    try:
        poster.driver.switch_to.frame("mainFrame")
    except Exception:
        pass

    # 작성중 팝업 처리
    try:
        poster.driver.execute_script("""
            for (const b of document.querySelectorAll('button')) {
                const t = (b.textContent||'').trim();
                if (t === '취소' && b.getBoundingClientRect().width > 0) {
                    b.click();
                    break;
                }
            }
        """)
    except Exception:
        pass
    time.sleep(0.8)

    print("\n[3] 제목/본문 최소 입력 (발행 버튼 활성화용)")
    poster._input_title(f"카테고리 테스트 {time.strftime('%H%M%S')}")
    time.sleep(0.4)
    poster._input_body("category select test")
    time.sleep(0.6)

    print("\n[4] 1차 발행 버튼 클릭 → 다이얼로그 오픈")
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    publish_btn = WebDriverWait(poster.driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "button.publish_btn__m9KHH, button[class*='publish_btn']"))
    )
    poster.driver.execute_script("arguments[0].click();", publish_btn)
    time.sleep(1.0)

    print("\n[5] 다이얼로그 사전 상태")
    pre = poster.driver.execute_script(r"""
        const btn = document.querySelector('button[aria-label*="카테고리"]');
        const checked = Array.from(document.querySelectorAll('input[type="radio"]:checked'))
            .map(r => (r.closest('label')?.textContent || '').trim().slice(0,30));
        const items = [...document.querySelectorAll('li[class*="item"]')]
            .map(e => (e.textContent||'').trim()).filter(t => t && t.length < 30);
        return {
            btnText: btn ? (btn.textContent||'').trim() : '',
            checked: checked,
            items: [...new Set(items)],
        };
    """)
    print(f"  버튼 텍스트: {pre.get('btnText')!r}")
    print(f"  현재 체크: {pre.get('checked')}")
    print(f"  보이는 항목: {pre.get('items')}")

    print(f"\n[6] _select_category_in_dialog('{target_cat}') 호출")
    poster._select_category_in_dialog(target_cat)
    time.sleep(1.0)

    print("\n[7] 다이얼로그 사후 상태")
    post = poster.driver.execute_script(r"""
        const btn = document.querySelector('button[aria-label*="카테고리"]');
        const checked = Array.from(document.querySelectorAll('input[type="radio"]:checked'))
            .map(r => (r.closest('label')?.textContent || '').trim().slice(0,30));
        return {
            btnText: btn ? (btn.textContent||'').trim() : '',
            checked: checked,
        };
    """)
    print(f"  버튼 텍스트: {post.get('btnText')!r}")
    print(f"  현재 체크: {post.get('checked')}")

    print("\n=== 판정 ===")
    btn_ok = target_cat in (post.get('btnText') or '')
    radio_ok = any(target_cat in c for c in (post.get('checked') or []))
    if btn_ok and radio_ok:
        print(f"✅ 성공 — 버튼 + radio 둘 다 '{target_cat}' 반영")
    elif radio_ok and not btn_ok:
        print(f"⚠ radio만 체크 — 버튼 텍스트 미갱신 (React state 부분 반영)")
    elif btn_ok:
        print(f"⚠ 버튼만 표시 — radio 체크 안됨")
    else:
        print(f"❌ 실패 — '{target_cat}' 적용 안 됨")

    print("\n[8] 다이얼로그 닫고 종료 (실제 발행 X)")
    time.sleep(2)
finally:
    try: poster.driver.quit()
    except: pass
