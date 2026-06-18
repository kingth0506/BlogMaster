# -*- coding: utf-8 -*-
"""로그인 프로필로 크롤링 테스트 — IP 차단 여부 확인"""
import os, sys, time, re
sys.path.insert(0, os.path.dirname(__file__))

from urllib.parse import quote
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DIR = os.path.dirname(__file__)

ITEM_SEL = ("li.Fh8nG, li.UEzoS, li.VLTHu, li[class*='UEzoS'], li.DWs4Q, "
            "li.naf7A, li[class*='naf7A'], li.sv5z6, "
            "#_pcmap_list_scroll_container ul > li[class]")

NAME_SEL = ("span.moQ_p, span.TYaxT, a.place_bluelink, span.YwYLL, span.q2LdB, "
            "span.O_Uah, a span.O_Uah, "
            ".pui__ek7lQY span, [class*='place_bluelink'] span, "
            "div.H0S1k span, div.KgfA6 span, "
            "a[role='button'] > span:first-child")


def make_logged_in_driver(blog_id="todayisgood77"):
    """로그인 세션이 저장된 Chrome 프로필로 드라이버 생성"""
    import undetected_chromedriver as uc

    profile_dir = os.path.join(BASE_DIR, "chrome_profile", blog_id)
    print(f"프로필 경로: {profile_dir}")

    # 이전 lock 파일 제거
    for lock in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        p = os.path.join(profile_dir, lock)
        if os.path.exists(p):
            os.remove(p)

    o = uc.ChromeOptions()
    o.add_argument(f"--user-data-dir={profile_dir}")
    o.add_argument("--window-size=1400,900")
    o.add_argument("--disable-gpu")
    o.add_argument("--no-sandbox")
    o.add_argument("--mute-audio")
    o.add_argument("--disable-background-networking")

    drv = uc.Chrome(options=o, headless=False)
    return drv


def test(keyword, drv):
    print(f"\n{'='*55}")
    print(f"키워드: {keyword}")
    print('='*55)

    drv.get(f"https://map.naver.com/p/search/{quote(keyword)}?searchType=place")
    time.sleep(4)

    # searchIframe 대기
    try:
        WebDriverWait(drv, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
        )
    except Exception as e:
        print(f"  [FAIL] searchIframe 없음: {e}")
        return

    drv.switch_to.frame("searchIframe")
    time.sleep(2)

    # 차단 여부
    body_text = drv.find_element(By.TAG_NAME, "body").text
    if "서비스 이용에 제한" in body_text:
        print("  [BLOCKED] 차단 메시지 감지!")
        print(f"  본문 앞부분: {body_text[:200]}")
        drv.switch_to.default_content()
        return

    items = drv.find_elements(By.CSS_SELECTOR, ITEM_SEL)
    li_all = drv.find_elements(By.TAG_NAME, "li")
    print(f"  [결과] ITEM_SEL={len(items)}개  li전체={len(li_all)}개")

    if items:
        print("  [업체 목록]")
        for i, it in enumerate(items[:5]):
            try:
                name = it.find_element(By.CSS_SELECTOR, NAME_SEL).text.strip()
            except:
                name = it.text.split("\n")[0][:30]
            cls = it.get_attribute("class") or ""
            print(f"    {i+1}. {name!r}  class={cls!r}")
        print(f"  → 로그인 세션으로 정상 수집 가능!")
    else:
        # 5초 더 대기 후 재확인
        print("  [대기] 5초 추가...")
        time.sleep(5)
        items2 = drv.find_elements(By.CSS_SELECTOR, ITEM_SEL)
        li_all2 = drv.find_elements(By.TAG_NAME, "li")
        print(f"  [7초 후] ITEM_SEL={len(items2)}개  li전체={len(li_all2)}개")
        if not items2:
            # app-root 상태 확인
            try:
                ar = drv.find_element(By.ID, "app-root")
                inner = drv.execute_script("return arguments[0].innerHTML.substring(0,300)", ar)
                print(f"  [app-root] {inner!r}")
            except:
                pass

    drv.switch_to.default_content()


# ── 실행 ──
drv = make_logged_in_driver("todayisgood77")

try:
    test("광주 동구 요양원", drv)   # 문제 키워드
    test("광주 동구 동물병원", drv) # 비교용 (이전에 됐던 것)
finally:
    input("\nEnter 누르면 종료...")
    drv.quit()
