# -*- coding: utf-8 -*-
"""업종별 실제 네이버 카테고리 수집 + _match_biz 매칭 검증"""
import sys, os, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from places_crawler import _match_biz, BIZ_SYNONYMS

BIZ_TYPES = [
    "요양원","헬스장","미용실","필라테스","요가","풀빌라","펜션","캠핑장",
    "고시원","공유오피스","골프장","맛집","스터디카페","안과","치과","피부과",
    "성형외과","손세차","디테일링","골프연습장","스크린골프","왁싱샵","네일샵",
    "누수탐지","하수구","원룸텔","카센터","자동차정비소","타이어","파티룸",
    "스튜디오","통증의학과","한의원","중고차","렌터카","렌트카","인테리어",
    "가전제품","반려동물","동물병원","강아지","고양이","포장이사","이사","용달",
    "가구청소","쇼파청소","침구류청소","에어컨청소","안마의자","웨딩홀","예식장",
    "메이크업","웨딩드레스"
]

AREAS = ["서울 강남구", "서울 서초구", "서울 마포구"]
PER_BIZ = 15  # 지역당 업종당 수집 샘플 수

def _make_driver():
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--disable-blink-features=AutomationControlled")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--window-size=1920,1080")
    opt.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    opt.add_experimental_option("excludeSwitches", ["enable-automation"])
    d = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
    d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return d

def probe(driver, keyword, limit=PER_BIZ):
    """카테고리 + 이름만 빠르게 수집"""
    driver.get(f"https://map.naver.com/p/search/{keyword}?searchType=place")
    time.sleep(5)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
        )
        driver.switch_to.frame("searchIframe")
    except Exception as e:
        return []
    time.sleep(3)
    # 스크롤 2번
    for _ in range(2):
        try:
            driver.execute_script(
                "var e=document.querySelector('#_pcmap_list_scroll_container');"
                "if(e){e.scrollTop+=1500;}"
            )
        except Exception:
            pass
        time.sleep(1.2)
    out = []
    items = driver.find_elements(By.CSS_SELECTOR, "li.UEzoS")
    for it in items[:limit]:
        try:
            name = it.find_element(By.CSS_SELECTOR, "span.TYaxT").text.strip()
        except Exception:
            continue
        cat = ""
        try:
            cat = it.find_element(By.CSS_SELECTOR, "span.KCMnt").text.strip()
        except Exception:
            pass
        out.append((name, cat))
    driver.switch_to.default_content()
    return out

def main():
    from collections import Counter
    out_path = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop", "업종매칭테스트결과.txt")
    lines = []
    lines.append(f"=== 업종 매칭 전수 테스트 (실행: {datetime.datetime.now()}) ===")
    lines.append(f"지역: {AREAS} | 업종당 샘플: {PER_BIZ} × {len(AREAS)} = 최대 {PER_BIZ*len(AREAS)}")
    lines.append("")

    driver = _make_driver()
    try:
        total_ok = 0
        total_count = 0
        miss_by_biz = {}  # biz → Counter of missed categories
        match_cat_by_biz = {}  # biz → Counter of matched categories
        total_biz = len(BIZ_TYPES)

        for i, biz in enumerate(BIZ_TYPES, 1):
            biz_ok = 0
            biz_total = 0
            biz_missed = Counter()
            biz_matched = Counter()
            biz_samples_log = []

            for area in AREAS:
                kw = f"{area} {biz}"
                print(f"[{i}/{total_biz}] {kw} ...", flush=True)
                try:
                    samples = probe(driver, kw)
                except Exception as e:
                    print(f"  ERR: {e}")
                    samples = []
                for n, c in samples:
                    ok = _match_biz(biz, c)
                    biz_samples_log.append((area, n, c, ok))
                    biz_total += 1
                    if ok:
                        biz_ok += 1
                        if c:
                            biz_matched[c] += 1
                    elif c:
                        biz_missed[c] += 1

            lines.append(f"[{biz}] 총 {biz_total}건 수집, 매칭 {biz_ok}건 ({(biz_ok/biz_total*100 if biz_total else 0):.0f}%)")
            if biz_matched:
                lines.append(f"  ✔ 매칭된 카테고리: {dict(biz_matched.most_common())}")
            if biz_missed:
                lines.append(f"  ✘ 놓친 카테고리: {dict(biz_missed.most_common())}")
                miss_by_biz[biz] = biz_missed
            lines.append(f"  현재 유의어: {BIZ_SYNONYMS.get(biz, [])}")
            # 샘플 상위 5개만 로그
            for (area, n, c, ok) in biz_samples_log[:5]:
                lines.append(f"    {'✔' if ok else '✘'} [{area}] {n} | {c or '(없음)'}")
            lines.append("")

            total_ok += biz_ok
            total_count += biz_total

        lines.append("=" * 60)
        lines.append(f"전체 매칭률: {total_ok}/{total_count} ({(total_ok/total_count*100 if total_count else 0):.1f}%)")
        lines.append("")
        if miss_by_biz:
            lines.append("=" * 60)
            lines.append("[ACTION] 유의어 사전에 추가 권장 (업종 → 놓친 카테고리:빈도)")
            for biz, cats in miss_by_biz.items():
                top = cats.most_common(5)
                lines.append(f"  {biz}: {top}")
    finally:
        driver.quit()

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n결과 저장: {out_path}")

if __name__ == "__main__":
    main()
