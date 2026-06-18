# -*- coding: utf-8 -*-
"""광주 동구 요양원 vs 정상 키워드 비교 디버그"""
import time, re, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote
from places_crawler import _make_driver

ITEM_SEL = ("li.Fh8nG, li.UEzoS, li.VLTHu, li[class*='UEzoS'], li.DWs4Q, "
            "li.naf7A, li[class*='naf7A'], li.sv5z6, "
            "#_pcmap_list_scroll_container ul > li[class]")

NAME_SEL = ("span.moQ_p, span.TYaxT, a.place_bluelink, span.YwYLL, span.q2LdB, "
            "span.O_Uah, a span.O_Uah, "
            ".pui__ek7lQY span, [class*='place_bluelink'] span, "
            "div.H0S1k span, div.KgfA6 span, "
            "a[role='button'] > span:first-child")

def test_keyword(keyword, driver):
    print(f"\n{'='*50}")
    print(f"키워드: {keyword}")
    print('='*50)

    # 파싱
    parts = keyword.strip().split()
    area_filter = parts[-2] if len(parts) >= 3 else (parts[0] if len(parts) >= 2 else "")
    biz_type = parts[-1] if len(parts) >= 2 else keyword
    print(f"  area_filter={area_filter!r}  biz_type={biz_type!r}")

    # 페이지 이동
    driver.get("https://www.naver.com")
    time.sleep(1)
    driver.get(f"https://map.naver.com/p/search/{quote(keyword)}?searchType=place")
    time.sleep(4)

    # searchIframe
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
        )
        print("  [OK] searchIframe 있음")
    except Exception as e:
        print(f"  [FAIL] searchIframe 없음: {e}")
        return

    driver.switch_to.frame("searchIframe")
    time.sleep(2)

    # 현재 iframe URL
    try:
        iframe_url = driver.execute_script("return window.location.href")
        print(f"  [URL] {iframe_url}")
    except:
        pass

    # 차단 체크
    body_text = driver.find_element(By.TAG_NAME, "body").text
    if "서비스 이용에 제한" in body_text or "이용에 제한" in body_text:
        print("  [BLOCK] 네이버 차단 페이지 감지!")
        driver.switch_to.default_content()
        return

    # ITEM_SEL로 찾기
    items = driver.find_elements(By.CSS_SELECTOR, ITEM_SEL)
    print(f"  [2초 후] ITEM_SEL 매칭: {len(items)}개 / li전체: {len(driver.find_elements(By.TAG_NAME, 'li'))}개")

    if not items:
        # 5초 더 기다려서 React 렌더링 완료 여부 확인
        print("  [대기] 5초 추가 대기...")
        time.sleep(5)
        items = driver.find_elements(By.CSS_SELECTOR, ITEM_SEL)
        all_li = driver.find_elements(By.TAG_NAME, "li")
        print(f"  [7초 후] ITEM_SEL 매칭: {len(items)}개 / li전체: {len(all_li)}개")

        # app-root 자식 구조
        try:
            app_root = driver.find_element(By.ID, "app-root")
            inner_html = driver.execute_script("return arguments[0].innerHTML.substring(0,500)", app_root)
            print(f"  [app-root] {inner_html!r}")
        except Exception as ex:
            print(f"  [app-root] 없음: {ex}")

        # pcmap 컨테이너 확인
        try:
            container = driver.find_element(By.CSS_SELECTOR, "#_pcmap_list_scroll_container")
            children = container.find_elements(By.XPATH, ".//*")
            print(f"  [진단] pcmap_container 하위 요소: {len(children)}개")
            tags = {}
            for c in children[:30]:
                t = c.tag_name
                tags[t] = tags.get(t, 0) + 1
            print(f"  [진단] 태그 분포: {tags}")
        except Exception as ex:
            print(f"  [진단] pcmap_container 없음: {ex}")

        driver.switch_to.default_content()
        return

    # 첫 3개 항목 이름 추출
    for i, item in enumerate(items[:3]):
        try:
            name_el = item.find_element(By.CSS_SELECTOR, NAME_SEL)
            name = name_el.text.strip()
        except:
            name = item.text.split("\n")[0][:30] if item.text else "(이름없음)"
        item_cls = item.get_attribute("class") or ""
        print(f"  [{i+1}] name={name!r}  li_class={item_cls[:40]!r}")

    # 1번 항목 클릭 → entryIframe → 주소 추출
    try:
        item = items[0]
        try:
            name_el = item.find_element(By.CSS_SELECTOR, NAME_SEL)
        except:
            name_el = item
        driver.execute_script("arguments[0].click();", name_el)
        time.sleep(1.5)
        driver.switch_to.default_content()
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#entryIframe"))
        )
        driver.switch_to.frame("entryIframe")
        time.sleep(1)
        body = driver.find_element(By.TAG_NAME, "body").text
        addr_match = re.search(
            r"((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)\s+\S+[시군구]\s+\S+(?:로|길|동|리|가)[^\n]*)",
            body
        )
        short_addr = addr_match.group(1).strip() if addr_match else ""
        print(f"  [주소] short_addr={short_addr!r}")
        print(f"  [필터] area_filter={area_filter!r} in short_addr → {area_filter in short_addr}")
    except Exception as ex:
        print(f"  [entryIframe 실패] {ex}")

    driver.switch_to.default_content()


# ── 실행 ──
os.environ["CRAWL_VISIBLE"] = "1"  # 헤드리스 해제 (눈으로 확인)
drv = _make_driver()

try:
    test_keyword("광주 동구 요양원", drv)   # 문제 키워드
    test_keyword("광주 남구 요양원", drv)   # 이전에 됐던 키워드
    test_keyword("광주 동구 동물병원", drv) # 다른 업종으로도 테스트
finally:
    input("\nEnter 누르면 브라우저 종료...")
    drv.quit()
