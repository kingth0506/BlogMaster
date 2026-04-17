# -*- coding: utf-8 -*-
"""네이버 지도 크롤링 모듈 (Selenium Chrome — API키 불필요)"""
import os
import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def crawl_places(keyword: str, count: int = 100, on_progress=None) -> list[dict]:
    """네이버 지도에서 키워드로 업체 크롤링 (Chrome)"""

    parts = keyword.strip().split()
    area = parts[0] if len(parts) >= 2 else ""
    biz_type = parts[-1] if len(parts) >= 2 else keyword
    if len(parts) >= 3:
        area = " ".join(parts[:-1])
        biz_type = parts[-1]
    area_filter = parts[-2] if len(parts) >= 3 else (parts[0] if len(parts) >= 2 else "")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    results = []
    collected_names = set()
    scanned = 0

    try:
        driver.get(f"https://map.naver.com/p/search/{keyword}?searchType=place")
        time.sleep(4)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
        )
        driver.switch_to.frame("searchIframe")
        time.sleep(3)

        while len(results) < count:
            if on_progress:
                try:
                    on_progress(len(results), scanned, "목록 수집 중...")
                except InterruptedError:
                    raise

            prev_count = len(results)

            # 각 업체 항목의 상세주소 버튼을 순서대로 처리
            # 모든 상세주소 열기 버튼 가져오기
            addr_btns = driver.find_elements(By.CSS_SELECTOR, ".uFxr1")

            for btn_idx in range(len(addr_btns)):
                if len(results) >= count:
                    break
                try:
                    # 버튼 다시 가져오기 (DOM 갱신 대응)
                    addr_btns = driver.find_elements(By.CSS_SELECTOR, ".uFxr1")
                    if btn_idx >= len(addr_btns):
                        break

                    btn = addr_btns[btn_idx]

                    # 이 버튼이 속한 업체 카드에서 이름 가져오기
                    card = btn.find_element(By.XPATH, "./ancestor::li | ./ancestor::div[contains(@class,'CHC5F')]")

                    name = ""
                    try:
                        name_el = card.find_element(By.CSS_SELECTOR, ".TYaxT, span.YwYLL, a.tzwk0, .place_bluelink")
                        name = name_el.text.strip()
                    except Exception:
                        try:
                            # 카드 텍스트에서 첫 줄
                            card_text = card.text.strip().split("\n")
                            for line in card_text:
                                if line.strip() and line.strip() != "이미지수" and not line.strip().isdigit():
                                    name = line.strip()
                                    break
                        except Exception:
                            continue

                    if not name or name in collected_names:
                        continue

                    scanned += 1

                    # 짧은 주소 추출
                    short_addr = ""
                    try:
                        card_text = card.text
                        # 패턴1: XX시/도 XX구/군 XX동
                        match = re.search(r"(\S+\s+\S+[구군]\s+\S+동)", card_text)
                        if not match:
                            # 패턴2: XX구 XX동
                            match = re.search(r"(\S+[구군]\s+\S+동)", card_text)
                        if match:
                            short_addr = match.group(1)
                    except Exception:
                        pass

                    # 지역 필터
                    if area_filter and area_filter not in short_addr:
                        collected_names.add(name)
                        continue

                    # 카테고리
                    category = ""
                    try:
                        cat_el = card.find_element(By.CSS_SELECTOR, ".KCMnt, span.YzBgS")
                        category = cat_el.text.strip()
                    except Exception:
                        pass

                    # 업종 필터: 카테고리에 업종 키워드가 포함된 것만 (이름은 무시)
                    if biz_type and biz_type not in category:
                        collected_names.add(name)
                        continue

                    # 상세주소 열기 클릭 → 지번 수집
                    jibun_addr = ""
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.8)

                        card_text_after = card.text

                        # 지번
                        jibun_match = re.search(r"지번\s*\n\s*(.+?)(?:\n|복사)", card_text_after)
                        if jibun_match:
                            jibun_addr = jibun_match.group(1).strip()

                        # 닫기
                        try:
                            close_btns = card.find_elements(By.CSS_SELECTOR, "[class*=close], .uFxr1")
                            for cb in close_btns:
                                if "닫기" in (cb.get_attribute("aria-label") or cb.text or ""):
                                    driver.execute_script("arguments[0].click();", cb)
                                    break
                            else:
                                driver.execute_script("arguments[0].click();", btn)
                        except Exception:
                            pass
                        time.sleep(0.3)

                    except Exception:
                        pass

                    # 근처역: 업체 클릭 → entryIframe에서 수집
                    nearby_station = ""
                    try:
                        name_el = card.find_element(By.CSS_SELECTOR, ".TYaxT, span.YwYLL, a.tzwk0, .place_bluelink")
                        driver.execute_script("arguments[0].click();", name_el)
                        time.sleep(0.8)

                        driver.switch_to.default_content()

                        WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#entryIframe"))
                        )
                        driver.switch_to.frame("entryIframe")
                        time.sleep(0.5)

                        page_text = driver.find_element(By.TAG_NAME, "body").text
                        station_match = re.search(r"(\S+역)\s*\d+번\s*출구", page_text)
                        if station_match:
                            raw_station = station_match.group(1)
                            # 노선번호 제거 (예: "36GTX-A연신내역" → "연신내역")
                            cleaned = re.sub(r"^[\d호선GTX\-A-Za-z]+", "", raw_station)
                            nearby_station = cleaned if cleaned.endswith("역") else raw_station

                        driver.switch_to.default_content()
                        driver.switch_to.frame("searchIframe")

                    except Exception:
                        try:
                            driver.switch_to.default_content()
                            driver.switch_to.frame("searchIframe")
                        except Exception:
                            pass

                    # 주소: 서울 XX구 XX동 (리스트에 보이는 동 주소)
                    address = short_addr

                    dong = _extract_dong(short_addr)
                    front_keywords = _generate_front_keywords(area_filter, biz_type, dong)
                    tags = _generate_tags(dong, biz_type, area_filter, nearby_station)
                    pixabay_keywords = _generate_pixabay_keywords(area_filter, biz_type, dong)

                    place = {
                        "index": len(results) + 1,
                        "name": name,
                        "address": address,
                        "jibun_address": jibun_addr,
                        "category": category,
                        "nearby_station": nearby_station,
                        "front_keywords": front_keywords,
                        "tags": tags,
                        "pixabay_keywords": pixabay_keywords,
                        "dong": dong,
                    }

                    collected_names.add(name)
                    results.append(place)

                    if on_progress:
                        try:
                            on_progress(len(results), scanned, name)
                        except InterruptedError:
                            raise

                except InterruptedError:
                    raise
                except Exception:
                    continue

            # 스크롤 여러 번 시도
            prev_btn_count = len(driver.find_elements(By.CSS_SELECTOR, ".uFxr1"))
            scroll_tries = 0
            while scroll_tries < 5:
                driver.execute_script(
                    "let el = document.querySelector('.Ryr1F') || document.querySelector('[class*=scroll]');"
                    "if(el) el.scrollTop += 800; else window.scrollBy(0, 800);"
                )
                time.sleep(1.5)
                new_btn_count = len(driver.find_elements(By.CSS_SELECTOR, ".uFxr1"))
                if new_btn_count > prev_btn_count:
                    prev_btn_count = new_btn_count
                    break
                scroll_tries += 1

            # 스크롤로 새 항목 안 나오면 다음 페이지
            addr_btns_after = driver.find_elements(By.CSS_SELECTOR, ".uFxr1")
            if len(addr_btns_after) <= len(addr_btns):
                if on_progress:
                    try:
                        on_progress(len(results), scanned, "다음 페이지 이동 중...")
                    except InterruptedError:
                        raise
                # 스크롤을 맨 아래로 내려서 페이지 버튼 보이게
                driver.execute_script(
                    "let el = document.querySelector('.Ryr1F') || document.querySelector('[class*=scroll]');"
                    "if(el) el.scrollTop = el.scrollHeight; else window.scrollTo(0, document.body.scrollHeight);"
                )
                time.sleep(1)
                if not _click_next_page(driver):
                    break
                # 페이지 로딩 대기
                time.sleep(3)
                # 새 페이지 로딩 후 상세주소 버튼 대기
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".uFxr1"))
                    )
                except Exception:
                    pass
                time.sleep(1)

    except InterruptedError:
        raise
    except Exception as e:
        if on_progress:
            try:
                on_progress(len(results), scanned, f"오류: {e}")
            except Exception:
                pass
    finally:
        driver.quit()

    return results


_stations_cache = None

def _get_stations() -> list:
    global _stations_cache
    if _stations_cache is None:
        stations_file = os.path.join(os.path.dirname(__file__), "stations.json")
        try:
            with open(stations_file, "r", encoding="utf-8") as f:
                _stations_cache = json.load(f)
        except Exception:
            _stations_cache = []
    return _stations_cache


def _click_next_page(driver) -> bool:
    try:
        result = driver.execute_script("""
            // 페이지 번호 버튼들 찾기
            let pages = document.querySelectorAll('.zRM9F a, [class*="paginator"] a');
            let currentNum = 0;

            // 현재 페이지 번호 찾기
            for(let p of pages) {
                if(p.getAttribute('aria-current') === 'page' || p.classList.contains('OxGdy')) {
                    currentNum = parseInt(p.textContent.trim());
                    break;
                }
            }

            // 다음 페이지 번호 클릭
            if(currentNum > 0) {
                for(let p of pages) {
                    let num = parseInt(p.textContent.trim());
                    if(num === currentNum + 1) {
                        p.click();
                        return true;
                    }
                }
            }

            // "다음" 버튼 클릭
            for(let p of pages) {
                let label = p.getAttribute('aria-label') || p.textContent || '';
                if(label.includes('다음') && p.getAttribute('aria-disabled') !== 'true') {
                    p.click();
                    return true;
                }
            }

            return false;
        """)
        if result:
            time.sleep(3)
        return bool(result)
    except Exception:
        return False


def _extract_dong(address: str) -> str:
    if not address:
        return ""
    match = re.search(r"[구군]\s+(\S+동)\b", address)
    if match:
        return match.group(1)
    return ""


def _dedup(items: list) -> str:
    """중복 제거 후 쉼표로 합침"""
    seen = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return ",".join(seen)


def _generate_front_keywords(area: str, biz_type: str, dong: str) -> str:
    kw = []
    if area and biz_type:
        kw.append(f"{area}{biz_type}")
    if dong:
        kw.append(dong)
    return _dedup(kw)


def _generate_tags(dong: str, biz_type: str, area: str, station: str = "") -> str:
    tags = []
    if dong and biz_type:
        tags.append(f"{dong}{biz_type}")
    if area and biz_type:
        tags.append(f"{area}{biz_type}")
    if station and biz_type:
        station_clean = station[:-1] if station.endswith("역") else station
        tags.append(f"{station_clean}{biz_type}")
        tags.append(f"{station}{biz_type}")
    return _dedup(tags)


def _generate_pixabay_keywords(area: str, biz_type: str, dong: str) -> str:
    kw = []
    if area and biz_type:
        kw.append(f"{area}{biz_type}")
    if dong and biz_type:
        kw.append(f"{dong}{biz_type}")
    return _dedup(kw) if kw else biz_type


def save_results(results: list[dict], filepath: str, keyword: str = ""):
    data = {"keyword": keyword, "items": results}
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_results(filepath: str) -> dict:
    """{'keyword': str, 'items': list} 반환. 구버전 호환."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"keyword": "", "items": data}
    return data
