# -*- coding: utf-8 -*-
"""예약발행 달력 네비게이션 독립 테스트
- 네이버 블로그 글쓰기 → 발행 다이얼로그 → 예약 체크 → 달력 오픈까지 진행
- 오늘부터 오프셋(일) 목록을 순차 테스트 → 각 날짜 클릭 시도 → 실제 input값 기록
"""
import sys
import os
import time
import datetime
import json

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from naver_poster import NaverBlogPoster, _dlog
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 테스트할 offset (일) 목록 — 90일 이후는 제외 (사용자 요청)
OFFSETS = [1, 7, 15, 30, 35, 60]


def load_config_account():
    from config import load_config, get_active_account
    cfg = load_config()
    acc = get_active_account(cfg)
    return acc


DATE_JS = r"""
const y = parseInt(arguments[0]);
const m = parseInt(arguments[1]);
const d = parseInt(arguments[2]);

const findDatepicker = () => {
    const dps = document.querySelectorAll('.ui-datepicker:not(.ui-datepicker-header)');
    for (const dp of dps) {
        const r = dp.getBoundingClientRect();
        if (r.width > 100 && r.height > 100) return dp;
    }
    return null;
};
const sleep = (ms) => { const t0 = Date.now(); while (Date.now() - t0 < ms) {} };

let dp = findDatepicker();
if (!dp) return 'no_datepicker_visible';

const readHeader = () => {
    const title = dp.querySelector('.ui-datepicker-title');
    if (!title) return null;
    const t = (title.textContent || '').trim();
    const mt = t.match(/(\d{4})[^\d]+(\d{1,2})/);
    if (!mt) return null;
    return {year: parseInt(mt[1]), month: parseInt(mt[2])};
};

const fireClick = (el) => {
    // 한 번만 클릭
    try { el.click(); } catch(e) {
        const rect = el.getBoundingClientRect();
        el.dispatchEvent(new MouseEvent('click', {
            bubbles: true, cancelable: true, view: window,
            clientX: rect.left + rect.width/2,
            clientY: rect.top + rect.height/2,
        }));
    }
};
let navCount = 0;
let safety = 36;
while (safety-- > 0) {
    const h = readHeader();
    if (!h) return 'no_header_in_dp';
    if (h.year === y && h.month === m) break;
    const goNext = (h.year < y || (h.year === y && h.month < m));
    const navSel = goNext ? '.ui-datepicker-next' : '.ui-datepicker-prev';
    const nav = dp.querySelector(navSel);
    if (!nav) return 'nav_not_found:' + navSel + ',header=' + h.year + '-' + h.month;
    if (nav.disabled || nav.classList.contains('ui-state-disabled')) {
        return 'nav_disabled:' + navSel + ',header=' + h.year + '-' + h.month;
    }
    const beforeMonth = h.month, beforeYear = h.year;
    fireClick(nav);
    navCount++;
    // 헤더가 바뀔 때까지 최대 2초 폴링
    let changed = false;
    for (let i = 0; i < 20; i++) {
        sleep(100);
        dp = findDatepicker();
        if (!dp) break;
        const hp = readHeader();
        if (hp && (hp.year !== beforeYear || hp.month !== beforeMonth)) {
            changed = true;
            break;
        }
    }
    if (!dp) return 'dp_lost_after_nav,nav=' + navCount;
    if (!changed) {
        return 'nav_click_no_effect:stuck_at=' + beforeYear + '-' + beforeMonth + ',attempts=' + navCount;
    }
}

const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
};
const isOtherMonth = (el) => {
    let cur = el;
    for (let i = 0; i < 3; i++) {
        if (!cur) break;
        const cls = (cur.className || '').toString().toLowerCase();
        if (cls.includes('other-month') || cls.includes('outside') ||
            cls.includes('unselectable') || cls.includes('disabled')) return true;
        cur = cur.parentElement;
    }
    return false;
};

const trySelectors = [
    '.ui-datepicker-calendar td:not(.ui-datepicker-other-month):not(.ui-datepicker-unselectable) a',
    'td:not(.ui-datepicker-other-month):not(.ui-datepicker-unselectable) a',
    'a.ui-state-default',
    'td a',
    'a[data-date]',
    'button[data-date]',
    'td button',
];

for (const sel of trySelectors) {
    const nodes = dp.querySelectorAll(sel);
    for (const el of nodes) {
        if (!isVisible(el)) continue;
        if (isOtherMonth(el)) continue;
        const t = (el.textContent || el.getAttribute('data-date') || '').trim();
        const num = parseInt(t);
        if (num === d) {
            el.click();
            ['mousedown', 'mouseup', 'click'].forEach(ev => {
                el.dispatchEvent(new MouseEvent(ev, {bubbles:true, cancelable:true, view:window}));
            });
            return 'clicked[' + sel + '],nav=' + navCount + ',day=' + d;
        }
    }
}
const allClickable = document.querySelectorAll('td a, td button, a.ui-state-default, button.ui-state-default, [role="button"]');
for (const el of allClickable) {
    if (!isVisible(el)) continue;
    if (isOtherMonth(el)) continue;
    const t = (el.textContent || '').trim();
    if (parseInt(t) === d && t.length <= 2) {
        el.click();
        return 'clicked[global_fallback],nav=' + navCount + ',day=' + d;
    }
}
return 'day_cell_not_found,nav=' + navCount + ',day=' + d;
"""


def open_calendar(poster):
    """발행 다이얼로그 열고 예약 체크 → 달력 띄우기"""
    # 글쓰기 페이지
    write_url = poster.BLOG_WRITE_URL.format(blog_id=poster.blog_id)
    poster.driver.get(write_url)
    time.sleep(2)
    # mainFrame 전환
    try:
        poster.driver.switch_to.frame("mainFrame")
    except Exception:
        pass
    time.sleep(1)

    # 제목/본문 최소 입력
    poster.driver.execute_script("""
        const title_area = document.querySelector('.se-title-text');
        if (title_area) title_area.click();
    """)
    time.sleep(0.5)
    poster.driver.execute_script("""
        document.execCommand('insertText', false, '테스트');
    """)
    time.sleep(0.3)

    poster.driver.execute_script("""
        const body = document.querySelector('.se-component.se-text .se-text-paragraph');
        if (body) body.click();
    """)
    time.sleep(0.3)
    poster.driver.execute_script("""
        document.execCommand('insertText', false, '본문 테스트입니다');
    """)
    time.sleep(0.5)

    # 오버레이 제거 (도움말 dim이 발행 버튼 가림)
    poster.driver.execute_script("""
        document.querySelectorAll('.se-popup-dim, [class*="popup-dim"], [class*="placesMap"], [class*="dim"]').forEach(el => el.remove());
    """)
    time.sleep(0.3)

    # 발행 버튼 — JS click으로 오버레이 우회
    publish_btn = WebDriverWait(poster.driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "button.publish_btn__m9KHH, button[class*='publish_btn']"))
    )
    poster.driver.execute_script("arguments[0].click();", publish_btn)
    time.sleep(1.5)

    # 예약 라디오
    poster.driver.execute_script("""
        const labels = document.querySelectorAll('label');
        for (const l of labels) {
            if ((l.textContent || '').trim() === '예약') { l.click(); return; }
        }
    """)
    time.sleep(0.8)

    # 날짜 input 클릭 → 달력 오픈
    poster.driver.execute_script("""
        const inp = document.querySelector('input[class*="input_date"]');
        if (inp) { inp.removeAttribute('readonly'); inp.focus(); inp.click(); }
    """)
    time.sleep(0.8)


_GET_HEADER = r"""
const dps = document.querySelectorAll('.ui-datepicker:not(.ui-datepicker-header)');
let dp = null;
for (const d of dps) {
    const r = d.getBoundingClientRect();
    if (r.width > 100 && r.height > 100) { dp = d; break; }
}
if (!dp) return null;
const t = dp.querySelector('.ui-datepicker-title');
if (!t) return null;
const m = (t.textContent || '').trim().match(/(\d{4})[^\d]+(\d{1,2})/);
return m ? {year: parseInt(m[1]), month: parseInt(m[2])} : null;
"""

_CLICK_NAV = r"""
const sel = arguments[0];
const dps = document.querySelectorAll('.ui-datepicker:not(.ui-datepicker-header)');
let dp = null;
for (const d of dps) {
    const r = d.getBoundingClientRect();
    if (r.width > 100 && r.height > 100) { dp = d; break; }
}
if (!dp) return 'no_dp';
const nav = dp.querySelector(sel);
if (!nav) return 'no_nav';
if (nav.disabled || nav.classList.contains('ui-state-disabled')) return 'disabled';
nav.click();
return 'clicked';
"""

_CLICK_DAY = r"""
const d = parseInt(arguments[0]);
const dps = document.querySelectorAll('.ui-datepicker:not(.ui-datepicker-header)');
let dp = null;
for (const x of dps) {
    const r = x.getBoundingClientRect();
    if (r.width > 100 && r.height > 100) { dp = x; break; }
}
if (!dp) return 'no_dp';
const sels = [
    '.ui-datepicker-calendar td:not(.ui-datepicker-other-month):not(.ui-datepicker-unselectable) a',
    'td:not(.ui-datepicker-other-month):not(.ui-datepicker-unselectable) a',
    'a.ui-state-default', 'td a', 'a[data-date]', 'button[data-date]', 'td button',
];
for (const sel of sels) {
    for (const el of dp.querySelectorAll(sel)) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        let cur = el; let other = false;
        for (let i = 0; i < 3; i++) {
            if (!cur) break;
            const cls = (cur.className || '').toString().toLowerCase();
            if (cls.includes('other-month') || cls.includes('outside') ||
                cls.includes('unselectable') || cls.includes('disabled')) { other = true; break; }
            cur = cur.parentElement;
        }
        if (other) continue;
        const t = (el.textContent || el.getAttribute('data-date') || '').trim();
        if (parseInt(t) === d) {
            el.click();
            return 'clicked:' + sel + ':' + d;
        }
    }
}
return 'day_not_found:' + d;
"""


def test_date(poster, offset_days):
    """특정 offset으로 날짜 클릭 테스트 — Python에서 nav 루프 (jQuery에 처리 시간 부여)."""
    target = datetime.date.today() + datetime.timedelta(days=offset_days)
    y, m, d = target.year, target.month, target.day
    drv = poster.driver

    # 달력 다시 열기
    drv.execute_script("""
        const inp = document.querySelector('input[class*="input_date"]');
        if (inp) { inp.focus(); inp.click(); }
    """)
    time.sleep(0.8)

    nav_count = 0
    last_err = ""
    for _ in range(36):
        h = drv.execute_script(_GET_HEADER)
        if not h:
            last_err = "no_header"
            break
        if h.get("year") == y and h.get("month") == m:
            break
        go_next = (h["year"], h["month"]) < (y, m)
        sel = ".ui-datepicker-next" if go_next else ".ui-datepicker-prev"
        before_y, before_m = h["year"], h["month"]
        res = drv.execute_script(_CLICK_NAV, sel)
        nav_count += 1
        if res != "clicked":
            last_err = f"nav_{res}"
            break
        # Python에서 sleep — 이 동안 jQuery가 헤더 갱신
        for _ in range(20):
            time.sleep(0.1)
            h2 = drv.execute_script(_GET_HEADER)
            if h2 and (h2.get("year") != before_y or h2.get("month") != before_m):
                break
        else:
            last_err = f"stuck_at_{before_y}-{before_m}"
            break

    # 일자 클릭
    if not last_err:
        click_res = drv.execute_script(_CLICK_DAY, d)
        time.sleep(0.5)
    else:
        click_res = f"skipped_{last_err}"

    actual = drv.execute_script(
        "return document.querySelector('input[class*=\"input_date\"]').value || '';"
    )
    expected = f"{y}. {m:02d}. {d:02d}"
    ok = actual.strip() == expected
    status = "[OK]  " if ok else "[FAIL]"
    print(f"{status} +{offset_days:>3}d ({expected}) -> nav={nav_count} click={click_res} input='{actual}'")
    return {"offset": offset_days, "expected": expected, "actual": actual,
            "nav_count": nav_count, "click": click_res, "ok": ok}


def main():
    acc = load_config_account()
    if not acc.get("naver_id") or not acc.get("naver_pw"):
        print("[FAIL] 네이버 계정 정보 없음 - 환경설정에서 저장 후 재실행")
        return

    poster = NaverBlogPoster(
        naver_id=acc["naver_id"],
        naver_pw=acc["naver_pw"],
        blog_id=acc["blog_id"],
        window_w=900, window_h=700,
    )
    poster.start_browser()
    ok = poster.login()
    if not ok:
        print("자동 로그인 실패 — 브라우저에서 직접 로그인해 주세요 (최대 90초 대기)")
        for _ in range(90):
            time.sleep(1)
            try:
                cur = poster.driver.current_url
                src = poster.driver.page_source.lower()
                if "nidlogin" not in cur and ("logout" in src or "blog.naver.com" in cur):
                    ok = True
                    print("→ 로그인 감지, 테스트 진행")
                    break
            except Exception:
                pass
    if not ok:
        print("[FAIL] 90초 내 로그인 안 됨")
        poster.close()
        return

    try:
        print("\n달력 열기...")
        open_calendar(poster)

        results = []
        for off in OFFSETS:
            try:
                r = test_date(poster, off)
                results.append(r)
            except Exception as e:
                print(f"[FAIL] +{off}d exception: {e}")
                results.append({"offset": off, "error": str(e)})

        ok_count = sum(1 for r in results if r.get("ok"))
        print(f"\n=== Result: {ok_count}/{len(OFFSETS)} passed ===")

        out = os.path.join(os.path.dirname(__file__), "datepicker_test_result.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Details: {out}")

    finally:
        time.sleep(2)
        poster.close()


if __name__ == "__main__":
    main()
