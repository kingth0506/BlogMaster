# -*- coding: utf-8 -*-
import sys, time, random
sys.path.insert(0, r"C:\Mac\Home\Desktop\program\블로그마스터")

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from places_crawler import _make_driver

KEYWORD = "서울 강남구 헬스장"
PROFILE = r"C:\Mac\Home\Desktop\program\블로그마스터\chrome_profile\todayisgood77"
ITEM_SEL = ("li.Fh8nG, li.UEzoS, li.VLTHu, li[class*='UEzoS'], li.DWs4Q, "
            "li.naf7A, li[class*='naf7A'], li.sv5z6, "
            "#_pcmap_list_scroll_container ul > li[class]")
NAME_SEL = "span.TYaxT, span.place_bluelink, strong.OXiLu, .place_name, span.YwYLL"

driver = _make_driver(headless=False)

try:
    from urllib.parse import quote
    driver.get(f"https://map.naver.com/p/search/{quote(KEYWORD)}?searchType=place")
    time.sleep(3)

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
    )
    driver.switch_to.frame("searchIframe")
    time.sleep(3)

    for page in range(1, 10):
        # 첫 번째 아이템 이름 가져오기
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ITEM_SEL))
            )
            items = driver.find_elements(By.CSS_SELECTOR, ITEM_SEL)
            if not items:
                print(f"[페이지 {page}] 아이템 없음")
                break
            first = items[0]
            name = ""
            try:
                name = first.find_element(By.CSS_SELECTOR, NAME_SEL).text.strip()
            except:
                name = first.text.strip().split("\n")[0]
            print(f"[페이지 {page}] 첫 항목: {name}")
        except Exception as e:
            print(f"[페이지 {page}] 아이템 찾기 실패: {e}")
            break

        # 다음 페이지 버튼 클릭
        next_num = str(page + 1)
        candidates = driver.find_elements(By.CSS_SELECTOR, "a, button, span[role], li[role]")
        clicked = False
        for el in candidates:
            try:
                if (el.text or "").strip() == next_num and el.is_displayed():
                    ActionChains(driver).move_to_element(el).pause(0.2).click().perform()
                    clicked = True
                    print(f"  → 페이지 {next_num} 클릭 성공")
                    time.sleep(random.uniform(1.5, 2.5))
                    break
            except:
                continue

        if not clicked:
            print(f"  → 페이지 {next_num} 버튼 없음, 종료")
            break

        # 페이지 전환 후 searchIframe 재진입
        driver.switch_to.default_content()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
        )
        driver.switch_to.frame("searchIframe")
        time.sleep(2)

finally:
    input("엔터 누르면 창 닫힘...")
    driver.quit()
