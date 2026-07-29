# -*- coding: utf-8 -*-
"""계정 전환(프로필 크롬 재시작)이 제대로 되는지 실제 검증.
앱의 _ensure_mgr 전환 로직과 동일: close → 프로필 크롬 kill → 2초 대기 → 새 프로필로 start.
A→B→A 두 번 전환하며 매번 브라우저가 정상 기동하는지 확인."""
import time, subprocess, sys
from naver_poster import NaverBlogPoster


def kill_profile_chrome(blog_id):
    if not blog_id:
        return
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
          "Where-Object { $_.CommandLine -like '*chrome_profile*" + blog_id + "*' } | "
          "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       timeout=15, capture_output=True)
    except Exception as e:
        print(f"  (kill 실패: {e})")


def start(blog_id, attempts=3):
    """앱과 동일하게 최대 3회 재시도하여 기동."""
    last = None
    for i in range(attempts):
        p = None
        try:
            p = NaverBlogPoster(naver_id="x", naver_pw="y", blog_id=blog_id,
                                headless=False, window_w=1180, window_h=820,
                                stop_flag=lambda: False)
            p.start_browser()
            url = p.driver.current_url  # 실제로 살아있는지 확인
            print(f"  [{blog_id}] start OK (att {i+1}) url={url[:40]}")
            return p
        except Exception as e:
            last = e
            print(f"  [{blog_id}] start fail {i+1}/{attempts}: {str(e)[:70]}")
            try:
                if p:
                    p.close()
            except Exception:
                pass
            time.sleep(2.5)
    raise RuntimeError(f"{blog_id} 기동 실패: {last}")


def switch_from(prev_poster, prev_blog, next_blog):
    """앱 전환 로직 그대로: 이전 close → kill → 2초 → 다음 start."""
    print(f"전환: {prev_blog} → {next_blog}")
    try:
        prev_poster.close()
    except Exception as e:
        print(f"  (이전 close 예외: {e})")
    kill_profile_chrome(prev_blog)
    time.sleep(2.0)
    return start(next_blog)


def main():
    A = sys.argv[1] if len(sys.argv) > 1 else "hscci93"
    B = sys.argv[2] if len(sys.argv) > 2 else "fkfkfk333"
    print(f"=== 계정 전환 테스트: A={A}, B={B} ===")

    print(f"1) A({A}) 최초 기동")
    p = start(A)
    cur = A
    time.sleep(1.0)

    # A → B → A 두 번 전환
    for nxt in (B, A):
        p = switch_from(p, cur, nxt)
        cur = nxt
        time.sleep(1.0)

    print("정리")
    try:
        p.close()
    except Exception:
        pass
    kill_profile_chrome(cur)
    print("=== SWITCH OK: 모든 전환 정상 ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"=== SWITCH FAIL: {e} ===")
        sys.exit(1)
