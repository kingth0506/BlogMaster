# -*- coding: utf-8 -*-
"""페이지 2에서 pagination 버튼 실제 HTML 덤프"""
import sys, time, random
sys.path.insert(0, r"C:\Mac\Home\Desktop\program\블로그마스터")
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from places_crawler import _make_driver, _get_driver_path

KEYWORD = "서울 강남구 헬스장"
ITEM_SEL = ("#_pcmap_list_scroll_container ul > li[class], "
            "li.naf7A, li.UEzoS, li.VLTHu, li.Fh8nG, li.DWs4Q")

driver = _make_driver(headless=False)

try:
    from urllib.parse import quote
    driver.get(f"https://map.naver.com/p/search/{quote(KEYWORD)}?searchType=place")
    time.sleep(4)

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
    )
    driver.switch_to.frame("searchIframe")
    time.sleep(2)

    # 페이지 1 스크롤 끝까지
    for _ in range(10):
        driver.execute_script(
            "let el = document.querySelector('#_pcmap_list_scroll_container');"
            "if(el) el.scrollTop += 2000;"
        )
        time.sleep(0.8)

    # 페이지 2 버튼 클릭
    candidates = driver.find_elements(By.CSS_SELECTOR, "a, button, span[role], li[role]")
    for el in candidates:
        try:
            if (el.text or "").strip() == "2" and el.is_displayed():
                ActionChains(driver).move_to_element(el).pause(0.2).click().perform()
                print("페이지 2 클릭 성공")
                time.sleep(2)
                break
        except:
            continue

    # searchIframe 재진입
    driver.switch_to.default_content()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
    )
    driver.switch_to.frame("searchIframe")
    time.sleep(2)

    # 페이지 2 끝까지 스크롤
    for _ in range(10):
        driver.execute_script(
            "let el = document.querySelector('#_pcmap_list_scroll_container');"
            "if(el) el.scrollTop += 2000;"
        )
        time.sleep(0.8)
    time.sleep(1)

    # === 이 시점에서 보이는 모든 후보 버튼 덤프 ===
    print("\n=== 후보 버튼 전체 목록 ===")
    SEL = "a, button, span[role], li[role], div[role='button'], span[role='button']"
    candidates = driver.find_elements(By.CSS_SELECTOR, SEL)
    for el in candidates:
        try:
            txt = (el.text or "").strip()
            tag = el.tag_name
            cls = el.get_attribute("class") or ""
            role = el.get_attribute("role") or ""
            aria_cur = el.get_attribute("aria-current") or ""
            displayed = el.is_displayed()
            if txt:
                print(f"  [{tag}] text={repr(txt[:30])} class={cls[:30]} role={role} aria-current={aria_cur} displayed={displayed}")
        except:
            continue

    # 페이지 소스 저장
    with open("page2_iframe.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("\npage2_iframe.html 저장 완료")

finally:
    input("엔터 누르면 닫힘...")
    driver.quit()
