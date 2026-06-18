# -*- coding: utf-8 -*-
"""카테고리 클릭 로직 단독 검증 — ㄴ prefix 하위 카테고리 시나리오"""
import sys, os, io, time, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 실제 네이버 UI처럼 "소개" 부모 아래 "ㄴ 추천" 형태의 자식 카테고리
SAMPLE_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>cat test</title>
<style>
.indent::before { content: 'ㄴ '; }
</style>
</head>
<body>
<button type="button" aria-label="카테고리 선택" aria-expanded="true" class="selectbox_btn">소개</button>
<ul role="listbox">
  <li class="item__sAGX9" role="option">
    <label class="radio_label__mB6ia">
      <input type="radio" name="category" value="소개" checked>
      <span data-testid="categoryItemText_p">소개</span>
    </label>
  </li>
  <li class="item__sAGX9 sub" role="option">
    <label class="radio_label__mB6ia">
      <input type="radio" name="category" value="여행">
      <span class="indent" data-testid="categoryItemText_1">여행</span>
    </label>
  </li>
  <li class="item__sAGX9 sub" role="option">
    <label class="radio_label__mB6ia">
      <input type="radio" name="category" value="카페">
      <span class="indent" data-testid="categoryItemText_2">카페</span>
    </label>
  </li>
  <li class="item__sAGX9 sub" role="option">
    <label class="radio_label__mB6ia">
      <input type="radio" name="category" value="독서">
      <span class="indent" data-testid="categoryItemText_3">독서</span>
    </label>
  </li>
  <li class="item__sAGX9 sub" role="option">
    <label class="radio_label__mB6ia">
      <input type="radio" name="category" value="일상">
      <span class="indent" data-testid="categoryItemText_4">일상</span>
    </label>
  </li>
  <li class="item__sAGX9 sub" role="option">
    <label class="radio_label__mB6ia">
      <input type="radio" name="category" value="추천">
      <span class="indent" data-testid="categoryItemText_5">ㄴ 추천</span>
    </label>
  </li>
</ul>
<script>
document.querySelectorAll('input[type="radio"]').forEach(r => {
    r.addEventListener('change', (e) => {
        if (e.target.checked) {
            document.querySelector('button[aria-label*="카테고리"]').textContent = e.target.value;
        }
    });
});
</script>
</body></html>"""

html_path = os.path.join(tempfile.gettempdir(), "cat_click_test.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(SAMPLE_HTML)

# v2 PICK_JS — naver_poster.py와 동일 (norm + endsWith fallback)
PICK_JS = r"""
const target = arguments[0];
const norm = (s) => (s||'').replace(/[ㄴˡ└┗┣\s]+/g, '').trim();
const targetN = norm(target);
const setNativeChecked = (el, val) => {
    try {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'checked').set;
        setter.call(el, val);
    } catch(e) { el.checked = val; }
};
const fireEvents = (el) => {
    ['change','input','click'].forEach(name => {
        el.dispatchEvent(new Event(name, {bubbles:true, cancelable:true}));
    });
};
function activate(scope) {
    const r = scope.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    scope.click();
    ['mousedown','mouseup','click'].forEach(ev => {
        scope.dispatchEvent(new MouseEvent(ev, {
            bubbles:true, cancelable:true, view:window,
            clientX: r.left + r.width/2, clientY: r.top + r.height/2,
        }));
    });
    const lbl = scope.querySelector('label') || (scope.tagName === 'LABEL' ? scope : null);
    if (lbl) lbl.click();
    const radio = scope.querySelector('input[type="radio"]');
    if (radio) {
        setNativeChecked(radio, true);
        fireEvents(radio);
    }
    return true;
}
for (const el of document.querySelectorAll('li[class*="item"]')) {
    const t = (el.textContent||'').trim();
    if (norm(t) === targetN && activate(el))
        return 'clicked_li_item:' + t;
}
for (const el of document.querySelectorAll('li[class*="item"]')) {
    const t = (el.textContent||'').trim();
    if (t && (t === target || t.endsWith(target) || norm(t).endsWith(targetN)) && activate(el))
        return 'clicked_endswith_li:' + t;
}
const avail = [...document.querySelectorAll('li[class*="item"]')]
    .map(e => (e.textContent||'').trim()).filter(t => t);
return 'not_found|target=' + target + '|targetN=' + targetN + '|available=' + JSON.stringify(avail);
"""

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from naver_poster import NaverBlogPoster
poster = NaverBlogPoster(naver_id="", naver_pw="", blog_id="cat_test_local",
                         headless=False, window_x=100, window_y=100,
                         window_w=900, window_h=500)
poster.start_browser()
drv = poster.driver
results = []
try:
    drv.get(f"file:///{html_path.replace(os.sep, '/')}")
    time.sleep(1)

    for target in ["여행", "카페", "추천"]:
        s1 = drv.execute_script(r"""
            return {
                btnText: document.querySelector('button[aria-label*="카테고리"]').textContent.trim(),
                checked: Array.from(document.querySelectorAll('input[type="radio"]:checked')).map(r => r.value)
            };
        """)
        print(f"\n--- '{target}' 클릭 ---")
        print(f"[전] 버튼:{s1['btnText']!r} / 체크:{s1['checked']}")

        res = drv.execute_script(PICK_JS, target)
        print(f"[클릭] {res}")
        time.sleep(0.4)

        s2 = drv.execute_script(r"""
            return {
                btnText: document.querySelector('button[aria-label*="카테고리"]').textContent.trim(),
                checked: Array.from(document.querySelectorAll('input[type="radio"]:checked')).map(r => r.value)
            };
        """)
        print(f"[후] 버튼:{s2['btnText']!r} / 체크:{s2['checked']}")

        ok = (target in s2['btnText'] and target in s2['checked'])
        results.append((target, ok, res))
        print(f"{'✅ 성공' if ok else '❌ 실패'} — '{target}'")

    print("\n=== 최종 판정 ===")
    for t, ok, r in results:
        print(f"  {'✅' if ok else '❌'} {t}: {r}")
    n_pass = sum(1 for _, ok, _ in results if ok)
    print(f"\n총 {n_pass}/{len(results)} 통과")

    time.sleep(1.5)
finally:
    drv.quit()
    try: os.remove(html_path)
    except: pass
