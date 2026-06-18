# -*- coding: utf-8 -*-
"""카테고리 v2 실제 검증 — 발행 차단된 상태로 다이얼로그까지 진행 후 state 캡처."""
import sys, os, io, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from naver_poster import NaverBlogPoster

# active = kidth1[0] = todayisgood77 / category=추천
BLOG_ID = "todayisgood77"
TARGET = "추천"

captured = {"v2_state": None, "blocked": False, "error": None}

def block_publish(self):
    """최종 발행 차단 — 다이얼로그 상태 캡처 후 종료"""
    print("[hook] _publish 호출 — 카테고리 클릭 직후 상태 캡처")
    try:
        time.sleep(1)
        state = self.driver.execute_script(r"""
            const btn = document.querySelector('button[aria-label*="카테고리"]');
            const btnText = btn ? (btn.textContent||'').trim() : '';
            const checked = Array.from(document.querySelectorAll('input[type="radio"]:checked'))
                .map(r => ({
                    label: (r.closest('label')?.textContent || r.parentElement?.textContent || '').trim().slice(0,40),
                    name: r.name||'',
                    value: r.value||''
                }));
            return {btnText, checked};
        """)
        captured["v2_state"] = state
        print(f"[hook] btn:{state.get('btnText')!r} / checked:{state.get('checked')}")
    except Exception as e:
        captured["error"] = str(e)
        print(f"[hook] 캡처 실패: {e}")
    captured["blocked"] = True
    return True  # 발행 안 됨

NaverBlogPoster._publish = block_publish

print(f"=== 카테고리 v2 검증 — blog={BLOG_ID} target={TARGET} ===\n")
poster = NaverBlogPoster(naver_id="", naver_pw="", blog_id=BLOG_ID,
                         headless=False, window_x=80, window_y=60,
                         window_w=1280, window_h=900)
try:
    print("[1] 브라우저 시작...")
    poster.start_browser()
    print("[2] write_post 호출 (발행은 차단됨)...")
    success = poster.write_post(
        title="[v2 검증] 무시 — 발행 안 됨",
        body="카테고리 v2 React state 검증용 본문. 실제 발행되지 않습니다.",
        tags=["테스트"],
        image_paths=None,
        category=TARGET,
        schedule_time=None,
    )
    print(f"\n[3] write_post 반환: {success}")
finally:
    print("\n[4] 5초 후 종료")
    time.sleep(5)
    try: poster.driver.quit()
    except: pass

print("\n" + "=" * 60)
print("=== 최종 검증 결과 ===")
print("=" * 60)
state = captured.get("v2_state")
if not state:
    print("❌ 다이얼로그까지 도달 못함")
    print(f"   에러: {captured.get('error')}")
    print(f"   blocked: {captured.get('blocked')}")
else:
    bt = state.get("btnText", "")
    ck = state.get("checked", [])
    print(f"카테고리 버튼 표시: {bt!r}")
    print(f"체크된 radio: {ck}")
    has_target = TARGET in bt or any(TARGET in c.get("label", "") for c in ck)
    if has_target:
        print(f"\n✅ 성공: '{TARGET}' React state 적용됨 — v2 정상 동작")
    else:
        print(f"\n❌ 실패: '{TARGET}' state 미반영 — 추가 fix 필요")
