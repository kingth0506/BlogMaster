# -*- coding: utf-8 -*-
import sys, time, random
sys.path.insert(0, r"C:\Mac\Home\Desktop\program\블로그마스터")

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from places_crawler import _make_driver

KEYWORD = "서울 강남구 헬스장"
PROFILE = r"C:\Mac\Home\Desktop\program\블로그마스터\chrome_profile\todayisgood77"
ITEM_SEL = "li.UEzoS, li.VLTHu, li[class*='place_bluelink'], li[data-id]"
NAME_SEL = "span.TYaxT, span.place_bluelink, strong.OXiLu, .place_name"

driver = _make_driver(headless=False)

try:
    from urllib.parse import quote
    driver.get(f"https://map.naver.com/p/search/{quote(KEYWORD)}?searchType=place")
    time.sleep(3)

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
    )
    driver.switch_to.frame("searchIframe")
    time.sleep(2)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ITEM_SEL))
        )
    except:
        src = driver.page_source
        print("=== 페이지 소스 앞 2000자 ===")
        print(src[:2000])
        driver.quit()
        sys.exit(1)

    collected = set()
    no_new_count = 0

    while no_new_count < 3:
        items = driver.find_elements(By.CSS_SELECTOR, ITEM_SEL)
        before = len(collected)

        for item in items:
            try:
                name = ""
                try:
                    name = item.find_element(By.CSS_SELECTOR, NAME_SEL).text.strip()
                except:
                    name = item.text.strip().split("\n")[0]
                if name and name not in collected:
                    collected.add(name)
                    print(f"[{len(collected)}] {name}", flush=True)
            except:
                continue

        if len(collected) == before:
            no_new_count += 1
        else:
            no_new_count = 0

        # 스크롤 컨테이너 아래로 스크롤
        try:
            container = driver.find_element(By.CSS_SELECTOR, "#_pcmap_list_scroll_container")
            driver.execute_script("arguments[0].scrollTop += 500;", container)
        except:
            driver.execute_script("window.scrollBy(0, 500);")

        time.sleep(random.uniform(1.0, 1.5))

    print(f"\n=== 최종: {len(collected)}개 ===")
    for i, name in enumerate(collected, 1):
        print(f"{i}. {name}")

finally:
    driver.quit()
