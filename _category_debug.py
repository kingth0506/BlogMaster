# -*- coding: utf-8 -*-
"""네이버 블로그 발행 다이얼로그의 카테고리 선택 UI 구조 실시간 디버깅.

- 크롬 비헤드리스로 열어 사용자가 직접 볼 수 있음
- 발행 다이얼로그 열고 카테고리 드롭다운 펼친 상태에서
- 0.5초마다 DOM 스냅샷 찍어 바탕화면 category_debug.log 에 append
- 찾은 카테고리 목록을 터미널에도 실시간 출력
"""
import os
import sys
import time
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from naver_poster import NaverBlogPoster, _dlog
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

LOG_PATH = os.path.expanduser(r"~/OneDrive/Desktop/category_debug.log")


def log(msg):
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_account():
    from config import load_config, get_active_account
    cfg = load_config()
    acc = get_active_account(cfg)
    return acc


DOM_SCAN_JS = r"""
// 1) 카테고리 드롭다운 버튼
const btns = Array.from(document.querySelectorAll('button[aria-label*="카테고리"], button[data-click-area*="category"], button[class*="selectbox"]'));
const btnInfo = btns.filter(b => {
  const r = b.getBoundingClientRect();
  return r.width > 0 && r.height > 0;
}).map(b => ({
  aria: b.getAttribute('aria-label'),
  cls: b.className,
  text: (b.textContent||'').trim().slice(0,50),
  expanded: b.getAttribute('aria-expanded'),
}));

// 2) 드롭다운 펼쳤을 때 보이는 모든 옵션 (label, span[data-testid])
const items = Array.from(document.querySelectorAll('label[class*="radio_label"], label[role="button"], span[data-testid^="categoryItem"], div[class*="category"] li'));
const itemInfo = items.filter(el => {
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0;
}).map(el => ({
  tag: el.tagName,
  cls: el.className,
  testid: el.getAttribute('data-testid'),
  text: (el.textContent||'').trim().slice(0,50),
}));

return { buttons: btnInfo, items: itemInfo };
"""


def scan(driver):
    try:
        res = driver.execute_script(DOM_SCAN_JS)
    except Exception as e:
        log(f"scan err: {e}")
        return
    btns = res.get("buttons", [])
    items = res.get("items", [])
    log(f"--- 드롭다운 버튼 {len(btns)}개 ---")
    for b in btns:
        log(f"  BTN [{b['aria']}] class={b['cls'][:60]} text='{b['text']}' expanded={b['expanded']}")
    log(f"--- 항목 {len(items)}개 ---")
    for it in items[:30]:
        log(f"  ITEM <{it['tag']}> class={it['cls'][:40]} testid={it['testid']} text='{it['text']}'")


def main():
    # 이전 로그 초기화
    try:
        open(LOG_PATH, "w", encoding="utf-8").close()
    except Exception:
        pass
    log(f"=== category debug 시작 ===")

    acc = load_account()
    if not acc.get("naver_id") or not acc.get("naver_pw"):
        log("계정 없음")
        return

    poster = NaverBlogPoster(
        naver_id=acc["naver_id"],
        naver_pw=acc["naver_pw"],
        blog_id=acc["blog_id"],
        window_w=1200, window_h=900,
    )
    poster.start_browser()
    if not poster.login():
        log("로그인 실패")
        return

    try:
        write_url = poster.BLOG_WRITE_URL.format(blog_id=poster.blog_id)
        poster.driver.get(write_url)
        time.sleep(3)
        try:
            poster.driver.switch_to.frame("mainFrame")
        except Exception:
            pass
        time.sleep(2)

        # 최소 제목/본문 입력
        poster.driver.execute_script("""
            const t = document.querySelector('.se-title-text');
            if (t) t.click();
        """)
        time.sleep(0.4)
        poster.driver.execute_script("document.execCommand('insertText', false, '카테고리 테스트');")
        time.sleep(0.3)
        poster.driver.execute_script("""
            const b = document.querySelector('.se-component.se-text .se-text-paragraph');
            if (b) b.click();
        """)
        time.sleep(0.3)
        poster.driver.execute_script("document.execCommand('insertText', false, '본문');")
        time.sleep(0.5)

        # 오버레이/도움말 제거 시도
        poster.driver.execute_script("""
            document.querySelectorAll('.se-help-panel, .se-help-title, [class*="help"]').forEach(el => {
                try { el.style.display = 'none'; } catch(e) {}
            });
            // 닫기 버튼 있으면 클릭
            document.querySelectorAll('button[aria-label*="닫기"], button.close').forEach(b => {
                try { b.click(); } catch(e) {}
            });
        """)
        time.sleep(0.5)

        # 발행 버튼 - JS 직접 클릭
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(poster.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button.publish_btn__m9KHH"))
        )
        poster.driver.execute_script("""
            const b = document.querySelector('button.publish_btn__m9KHH');
            if (b) b.click();
        """)
        time.sleep(2)

        log("--- 발행 다이얼로그 오픈 직후 ---")
        scan(poster.driver)

        # 카테고리 드롭다운 클릭 — 여러 방식 시도
        time.sleep(1)
        opened = poster.driver.execute_script("""
            const btn = document.querySelector('button.selectbox_button__jb1Dt, button[aria-label*="카테고리"]');
            if (!btn) return 'no_btn';
            btn.scrollIntoView({block:'center'});
            const rect = btn.getBoundingClientRect();
            // 1) focus + click
            btn.focus();
            btn.click();
            // 2) MouseEvent dispatch (native click 실패 대응)
            ['mousedown','mouseup','click'].forEach(ev => {
                btn.dispatchEvent(new MouseEvent(ev, {
                    bubbles:true, cancelable:true, view:window,
                    clientX: rect.left + rect.width/2,
                    clientY: rect.top + rect.height/2,
                }));
            });
            // 3) Enter 키
            btn.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', bubbles:true}));
            return 'tried ' + btn.getAttribute('aria-expanded');
        """)
        log(f"드롭다운 클릭 시도: {opened}")
        time.sleep(2)

        # 카테고리 목록이 실제로 다른 곳(별도 ul/li) 에 렌더된 경우도 스캔
        extra = poster.driver.execute_script(r"""
            // aria-expanded=true 찾기
            const exp = document.querySelectorAll('button[aria-expanded="true"], [role="listbox"], ul[class*="option"], ul[class*="category"], li[class*="option"], li[class*="category"]');
            const out = [];
            exp.forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) {
                    out.push({
                        tag: el.tagName,
                        cls: el.className,
                        role: el.getAttribute('role'),
                        text: (el.textContent||'').trim().slice(0,200),
                    });
                }
            });
            // 모든 가시 li/option 텍스트
            const lis = document.querySelectorAll('li, [role="option"]');
            const visLis = [];
            lis.forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0 && r.height < 60) {
                    const t = (el.textContent||'').trim();
                    if (t && t.length < 40) visLis.push({cls: el.className.slice(0,40), text: t});
                }
            });
            return { expanded: out, items: visLis };
        """)
        log(f"--- expanded listbox/ul {len(extra.get('expanded',[]))}개 ---")
        for e in extra.get("expanded", []):
            log(f"  EXP <{e['tag']}> role={e['role']} class={e['cls'][:50]} text='{e['text'][:80]}'")
        log(f"--- 가시 li/option {len(extra.get('items',[]))}개 ---")
        for it in extra.get("items", [])[:40]:
            log(f"  LI class={it['cls']} text='{it['text']}'")

        log("--- 드롭다운 펼친 후 standard scan ---")
        scan(poster.driver)

        log("브라우저는 열어둠. 창 닫으시면 종료됩니다.")
        # 브라우저 닫힐 때까지 유지
        while True:
            try:
                _ = poster.driver.title
                time.sleep(2)
            except Exception:
                break
    finally:
        try: poster.close()
        except: pass
        log("=== 종료 ===")


if __name__ == "__main__":
    main()
