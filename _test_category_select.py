# -*- coding: utf-8 -*-
"""실제 _select_category_in_dialog 동작 확인 — 눈앞에서 카테고리 선택 시연"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from config import load_config, get_active_account
from naver_poster import NaverBlogPoster, _dlog

cfg = load_config()
acc = get_active_account(cfg)
if not acc.get("naver_id") or not acc.get("naver_pw"):
    print("계정 설정 없음")
    sys.exit(1)

category = acc.get("blog_category", "").strip()
if not category:
    print("blog_category가 비어 있습니다. 설정에서 카테고리를 입력해주세요.")
    sys.exit(1)

print(f"계정: {acc['naver_id']}, 카테고리: {category}")

poster = NaverBlogPoster(
    naver_id=acc["naver_id"],
    naver_pw=acc["naver_pw"],
    blog_id=acc.get("blog_id", ""),
    window_w=1200, window_h=900,
    headless=False,
)
poster.start_browser()
if not poster.login():
    print("로그인 실패")
    sys.exit(1)

print("로그인 성공, 글쓰기 페이지 이동...")
try:
    write_url = poster.BLOG_WRITE_URL.format(blog_id=poster.blog_id)
    poster.driver.get(write_url)
    time.sleep(3)
    try:
        poster.driver.switch_to.frame("mainFrame")
    except Exception:
        pass
    time.sleep(2)

    # 제목 입력
    poster.driver.execute_script("""
        const t = document.querySelector('.se-title-text');
        if (t) { t.click(); }
    """)
    time.sleep(0.3)
    poster.driver.execute_script("document.execCommand('insertText', false, '카테고리 선택 테스트');")
    time.sleep(0.3)

    # 본문 입력
    poster.driver.execute_script("""
        const b = document.querySelector('.se-component.se-text .se-text-paragraph');
        if (b) b.click();
    """)
    time.sleep(0.3)
    poster.driver.execute_script("document.execCommand('insertText', false, '테스트 본문입니다.');")
    time.sleep(0.5)

    # 발행 버튼
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    publish_btn = WebDriverWait(poster.driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "button.publish_btn__m9KHH, button[class*='publish_btn']"))
    )
    poster.driver.execute_script("arguments[0].click();", publish_btn)
    print("발행 다이얼로그 오픈...")
    time.sleep(1.5)

    # 카테고리 선택 시도
    print(f"카테고리 선택 시도: {category}")
    poster._select_category_in_dialog(category)
    time.sleep(1)
    print("완료. 창 닫으시면 종료됩니다.")

    while True:
        try:
            _ = poster.driver.title
            time.sleep(2)
        except Exception:
            break
finally:
    try:
        poster.close()
    except Exception:
        pass
