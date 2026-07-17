"""네이버 블로그 자동 포스팅 모듈 (undetected-chromedriver)"""
import time
import os
import random
import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

_DEBUG_LOG = os.path.join(os.path.dirname(__file__), "poster_debug.log")


def _dlog(msg: str):
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


class NaverBlogPoster:
    NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
    BLOG_WRITE_URL = "https://blog.naver.com/{blog_id}?Redirect=Write&"

    def __init__(self, naver_id: str, naver_pw: str, blog_id: str, headless: bool = False,
                 window_x: int = 50, window_y: int = 50,
                 window_w: int = 900, window_h: int = 700,
                 stop_flag=None, speed_factor: float = 0.7):
        self.naver_id = naver_id
        self.naver_pw = naver_pw
        self.blog_id = blog_id
        self.driver = None
        self.headless = headless
        self.window_x = window_x
        self.window_y = window_y
        self.window_w = window_w
        self.window_h = window_h
        # 중단 콜백 — MainWindow에서 self.stop_flag 람다 주입. True 반환 시 즉시 중단
        self.stop_flag = stop_flag or (lambda: False)
        # 속도 배율 — 모든 self._sleep(N) 호출이 N * speed_factor로 줄어듦.
        # 0.7 = 30% 단축(안전), 0.5 = 50% 단축(공격적), 1.0 = 원래 속도
        self.speed_factor = max(0.3, min(1.5, float(speed_factor)))

    def _sleep(self, sec: float):
        """stop_flag 즉시 반응하는 sleep — 0.2초 단위 폴링 + speed_factor 적용.
        중단 시 InterruptedError 발생 → write_post가 try/except로 잡아 False 반환."""
        import time as _t
        sec = sec * self.speed_factor
        # 최소 0.05초는 보장 (너무 빨라서 네이버가 입력 못 받는 경우 방지)
        if 0 < sec < 0.05:
            sec = 0.05
        if sec <= 0:
            if self.stop_flag():
                raise InterruptedError("사용자 중단")
            return
        end = _t.time() + sec
        while _t.time() < end:
            if self.stop_flag():
                raise InterruptedError("사용자 중단")
            _t.sleep(min(0.2, end - _t.time()))

    def start_browser(self):
        """브라우저 시작 (undetected-chromedriver)"""
        # 쿠키/설정 유지용 프로필 폴더 (계정별 분리)
        profile_dir = os.path.join(
            os.path.dirname(__file__), "chrome_profile", self.blog_id or "default"
        )
        os.makedirs(profile_dir, exist_ok=True)
        _dlog(f"Chrome 프로필 경로: {profile_dir}")

        # 이전 실행이 비정상 종료되었을 때 남은 lock 파일 제거
        for lock_name in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
            try:
                p = os.path.join(profile_dir, lock_name)
                if os.path.exists(p):
                    os.remove(p)
                    _dlog(f"lock 제거: {lock_name}")
            except Exception as e:
                _dlog(f"lock 제거 실패({lock_name}): {e}")
        try:
            p = os.path.join(profile_dir, "Default", "LOCK")
            if os.path.exists(p):
                os.remove(p)
                _dlog("Default/LOCK 제거")
        except Exception as e:
            _dlog(f"Default/LOCK 제거 실패: {e}")

        # ★ 크롬 프로필 Preferences 파일이 비대(폭주)하거나 깨졌으면 삭제 —
        # undetected_chromedriver가 handle_prefs에서 이 파일을 json.load 하다 크래시하는 것 방지.
        # (Preferences 정상 크기는 수십~수백KB. 5MB 넘으면 비정상 → 삭제하면 크롬이 새로 만듦)
        import json as _json_chk
        for _pref_rel in ["Default/Preferences", "Default/Secure Preferences",
                          "Preferences", "Secure Preferences"]:
            _pf = os.path.join(profile_dir, *_pref_rel.split("/"))
            try:
                if not os.path.exists(_pf):
                    continue
                _bad = False
                if os.path.getsize(_pf) > 5 * 1024 * 1024:   # 5MB 초과 = 비정상
                    _bad = True
                else:
                    try:
                        with open(_pf, "r", encoding="utf-8") as _f:
                            _json_chk.load(_f)
                    except Exception:
                        _bad = True   # 파싱 불가 = 손상
                if _bad:
                    os.remove(_pf)
                    _dlog(f"손상/비대 프로필 파일 삭제: {_pref_rel}")
            except Exception as e:
                _dlog(f"프로필 파일 점검 실패({_pref_rel}): {e}")

        def _build_opts():
            o = uc.ChromeOptions()
            if self.headless:
                o.add_argument("--headless=new")
            o.add_argument(f"--window-size={self.window_w},{self.window_h}")
            o.add_argument(f"--window-position={self.window_x},{self.window_y}")
            o.add_argument("--disable-gpu")
            o.add_argument(f"--user-data-dir={profile_dir}")
            # 저사양 PC 메모리 절약 — 글쓰기 시 이미지는 필요하므로 끄지 않음
            o.add_argument("--mute-audio")
            o.add_argument("--disable-background-networking")
            o.add_argument("--disable-default-apps")
            o.add_argument("--disable-sync")
            o.add_argument("--disable-extensions")
            # 비밀번호 저장 팝업 차단
            o.add_experimental_option("prefs", {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.password_manager_leak_detection": False,
            })
            o.add_argument("--disable-features=PasswordManagerOnboarding,AutofillServerCommunication,TranslateUI")
            return o

        # Chrome 버전 자동 감지 — 설치된 Chrome 메이저 버전 읽어서 version_main에 넘김
        def _get_chrome_major() -> int:
            """설치된 Chrome 메이저 버전 번호 반환. 실패 시 None."""
            import subprocess, re as _re
            # 1) 레지스트리
            try:
                import winreg
                for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                    for sub in (
                        r"Software\Google\Chrome\BLBeacon",
                        r"SOFTWARE\Google\Update\Clients\{8A69D345-D564-463c-AFF1-A69D9E530F96}",
                        r"SOFTWARE\Wow6432Node\Google\Update\Clients\{8A69D345-D564-463c-AFF1-A69D9E530F96}",
                    ):
                        try:
                            with winreg.OpenKey(root, sub) as k:
                                ver, _ = winreg.QueryValueEx(k, "version" if "BLBeacon" in sub else "pv")
                                m = _re.match(r"(\d+)", str(ver))
                                if m: return int(m.group(1))
                        except Exception:
                            continue
            except Exception:
                pass
            # 2) chrome.exe --version
            for path in (
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ):
                try:
                    out = subprocess.check_output([path, "--version"], timeout=5, stderr=subprocess.DEVNULL)
                    m = _re.search(r"(\d+)\.", out.decode(errors="ignore"))
                    if m: return int(m.group(1))
                except Exception:
                    continue
            return None

        chrome_ver = _get_chrome_major()
        _dlog(f"감지된 Chrome 버전: {chrome_ver}")
        try:
            if chrome_ver:
                self.driver = uc.Chrome(options=_build_opts(), use_subprocess=True, version_main=chrome_ver)
            else:
                self.driver = uc.Chrome(options=_build_opts(), use_subprocess=True)
        except Exception as _e:
            _dlog(f"Chrome 드라이버 실패, 버전 없이 재시도: {_e}")
            self.driver = uc.Chrome(options=_build_opts(), use_subprocess=True)
        # 프로필에 저장된 옛 창 상태가 --window-size 옵션을 덮으므로 set_window_rect로 강제
        try:
            self.driver.set_window_rect(x=self.window_x, y=self.window_y,
                                         width=self.window_w, height=self.window_h)
        except Exception:
            try:
                self.driver.set_window_size(self.window_w, self.window_h)
                self.driver.set_window_position(self.window_x, self.window_y)
            except Exception:
                pass

        # OS 파일 다이얼로그 전역 차단 (CDP로 모든 페이지에 자동 주입)
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    window.__naverFileInput = null;
                    const origClick = HTMLInputElement.prototype.click;
                    HTMLInputElement.prototype.click = function() {
                        if (this.type === 'file' && !this.hasAttribute('__allow_click')) {
                            // 네이버는 file input을 DOM에 안 붙인 채(detached) click만 호출함.
                            // → DOM에 강제로 붙여 Selenium이 찾을 수 있게 하고 캡처한다.
                            try {
                                if (!this.isConnected) {
                                    this.setAttribute('data-auto-captured', '1');
                                    this.style.position = 'fixed';
                                    this.style.left = '-99999px';
                                    this.style.width = '1px';
                                    this.style.height = '1px';
                                    (document.body || document.documentElement).appendChild(this);
                                }
                            } catch (e) {}
                            window.__naverFileInput = this;
                            return;  // OS 다이얼로그는 열지 않음 (send_keys로 직접 주입)
                        }
                        return origClick.call(this);
                    };
                """
            })
            _dlog("CDP 파일 다이얼로그 차단 주입 완료")
        except Exception as e:
            _dlog(f"CDP 주입 실패: {e}")

    def login(self) -> bool:
        """네이버 로그인 (한 글자씩 랜덤 딜레이) — 기존 세션이 있으면 스킵"""
        import random

        try:
            # 프로필에 기존 로그인 세션이 있으면 로그인 스킵
            self.driver.get("https://www.naver.com")
            # 페이지 로드 대기 (body 나올 때까지)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except Exception:
                pass
            self._sleep(0.8)
            try:
                # 로그아웃 링크(href에 logout 포함) — 정확 판별
                self.driver.find_element(By.CSS_SELECTOR, "a[href*='logout'], a[href*='nid.naver.com/nidlogin.logout']")
                _dlog("기존 로그인 세션 감지 - 로그인 스킵")
                return True
            except Exception:
                _dlog("로그인 세션 없음 - 로그인 진행")

            self.driver.get(self.NAVER_LOGIN_URL)
            # ID/PW 필드 등장 대기
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "id"))
                )
            except Exception as e:
                _dlog(f"로그인 폼 대기 실패: {e}")
            self._sleep(0.4)

            # ID/PW 입력 — 정확값 그대로 설정(JS). 오토필/타이핑 오류 방지 위해 먼저 비우고 값 설정 + 이벤트 발생.
            self.driver.execute_script(
                "var idEl=document.getElementById('id'); var pwEl=document.getElementById('pw');"
                "var setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
                "function put(el,val){ if(!el) return; el.focus();"
                "  setter.call(el,''); el.dispatchEvent(new Event('input',{bubbles:true}));"
                "  setter.call(el,val); el.dispatchEvent(new Event('input',{bubbles:true}));"
                "  el.dispatchEvent(new Event('change',{bubbles:true})); el.dispatchEvent(new Event('blur',{bubbles:true})); }"
                "put(idEl, arguments[0]); put(pwEl, arguments[1]);",
                self.naver_id, self.naver_pw
            )
            _dlog(f"ID/PW 입력 완료 (id={self.naver_id})")
            self._sleep(0.3)

            # 로그인 버튼 클릭 — 네이버 로그인 페이지 개편 대응
            #   구: id="log.login" (type=submit)  →  신: id="loginBtn_row" / "loginBtn_column" (type=button)
            #   반응형이라 둘 중 화면에 보이는 것을 클릭. 못 찾으면 '로그인' 텍스트 버튼으로 폴백.
            _LOGIN_BTN_IDS = ["loginBtn_row", "loginBtn_column", "log.login"]
            _clicked = False
            for _bid in _LOGIN_BTN_IDS:
                try:
                    _btn = self.driver.find_element(By.ID, _bid)
                    if not _btn.is_displayed():
                        continue
                    try:
                        _btn.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", _btn)
                    _clicked = True
                    _dlog(f"로그인 버튼 클릭: #{_bid}")
                    break
                except Exception:
                    continue
            if not _clicked:
                # 폴백: id 못 찾으면 보이는 '로그인' 버튼을 JS로 클릭
                try:
                    self.driver.execute_script(
                        "var b=document.getElementById('loginBtn_row')"
                        "||document.getElementById('loginBtn_column')"
                        "||document.getElementById('log.login')"
                        "||Array.from(document.querySelectorAll('button')).find("
                        "  function(x){return x.offsetParent && /로그인/.test(x.innerText||'');});"
                        "if(b){b.click();}"
                    )
                    _dlog("로그인 버튼 클릭(폴백 JS)")
                except Exception:
                    pass
            self._sleep(1.5)
            _dlog(f"로그인 후 URL: {self.driver.current_url}")

            # 새 기기 등록 페이지 처리 (deviceConfirm)
            self._handle_device_confirm()

            # 패스키 설정 안내 페이지 처리
            self._skip_passkey_bridge()

            # 로그인 확인
            _dlog(f"최종 URL: {self.driver.current_url}")
            if "nid.naver.com" not in self.driver.current_url:
                _dlog("로그인 성공 확인")
                return True

            # 캡챠/추가인증 필요 → 구석/화면밖에 있던 창을 눈앞으로 가져와 사용자가 풀게
            try:
                self.driver.set_window_position(220, 120)
                self.driver.set_window_size(1180, 860)
                self.driver.execute_script("window.focus(); try{window.alert;}catch(e){}")
            except Exception:
                pass
            # 캡챠/추가인증 대기 — 사용자가 직접 캡챠 풀고 로그인 버튼을 누름. (앱은 안 누름)
            # 사용자가 로그인 창을 닫으면 즉시 '로그인 실패'.
            _dlog("로그인 미완료 - 캡챠/추가인증 대기 (최대 120초)")
            print("로그인 확인 대기중... 캡챠를 풀고 로그인 버튼을 직접 눌러주세요.")
            import time as _t2
            deadline = _t2.time() + 120
            while _t2.time() < deadline:
                # 사용자가 로그인 창을 닫으면 즉시 실패
                try:
                    if not self.driver.window_handles:
                        _dlog("로그인 창 닫힘 → 로그인 실패")
                        return False
                except Exception:
                    _dlog("브라우저 접근 불가(창 닫힘) → 로그인 실패")
                    return False
                # 로그인 완료(네이버 도메인 벗어남) 확인
                try:
                    if "nid.naver.com" not in self.driver.current_url:
                        _dlog("추가 인증 후 로그인 성공")
                        return True
                except Exception:
                    _dlog("브라우저 접근 불가(창 닫힘) → 로그인 실패")
                    return False
                _t2.sleep(1.0)
            _dlog("로그인 확인 시간 초과")
            return False

        except Exception as e:
            print(f"로그인 실패: {e}")
            return False

    def check_status(self) -> str:
        """계정 상태 점검 — 포스팅과 '동일한' login()으로 로그인 후 페이지로 판별.
        반환: '정상' / '보호조치' / '로그인실패' / '확인불가'."""
        PROT = ["보호조치", "이용이 제한", "이용 제한", "이용제한", "로그인이 제한",
                "정책을 위반", "계정이 보호", "비정상적인 로그인", "정상적인 활동이 아"]
        try:
            ok = self.login()   # ★ 포스팅과 똑같은 로그인 방식 (기기등록·패스키 처리 포함)
            try:
                page = self.driver.page_source or ""
                url = self.driver.current_url or ""
            except Exception:
                return "확인불가"
            if any(k in page for k in PROT):
                return "보호조치"
            if ok and "nid.naver.com" not in url:
                return "정상"
            return "로그인실패"
        except Exception:
            return "확인불가"

    def _handle_device_confirm(self):
        """'새로운 기기에서 로그인' 페이지(deviceConfirm)면 '등록' 버튼 클릭"""
        try:
            self._sleep(0.2)
            if "deviceConfirm" not in self.driver.current_url:
                return
            _dlog("새 기기 등록 페이지 감지 - '등록' 클릭")
            clicked = self.driver.execute_script("""
                const btns = document.querySelectorAll('a, button, input[type="submit"]');
                for (const b of btns) {
                    const t = (b.value || b.textContent || '').trim();
                    if (t === '등록') {
                        b.click();
                        return true;
                    }
                }
                return false;
            """)
            _dlog(f"등록 버튼 클릭 결과: {clicked}")
            self._sleep(0.35)
        except Exception as e:
            _dlog(f"deviceConfirm 처리 실패: {e}")

    def _skip_passkey_bridge(self):
        """패스키 설정 안내 페이지가 뜨면 '30일 동안 안 보기' 체크 후 스킵"""
        try:
            self._sleep(0.2)
            if "passkey" not in self.driver.current_url:
                return
            _dlog("패스키 안내 페이지 감지 - 스킵 처리")
            # '30일 동안 안 보기' 체크박스 클릭
            try:
                dont_show = self.driver.find_element(
                    By.XPATH, "//*[contains(text(),'30일 동안 안 보기') or contains(text(),'30일동안 안 보기')]"
                )
                dont_show.click()
                self._sleep(0.25)
                _dlog("'30일 동안 안 보기' 클릭")
            except Exception:
                pass
            # 취소/나중에/건너뛰기 링크 클릭
            for xp in [
                "//a[contains(text(),'나중에') or contains(text(),'건너뛰기') or contains(text(),'취소')]",
                "//button[contains(text(),'나중에') or contains(text(),'건너뛰기') or contains(text(),'취소')]",
            ]:
                try:
                    self.driver.find_element(By.XPATH, xp).click()
                    self._sleep(0.2)
                    _dlog(f"스킵 버튼 클릭: {xp}")
                    return
                except Exception:
                    continue
            # 대체: 그냥 네이버 메인으로 이동
            self.driver.get("https://www.naver.com")
            self._sleep(0.2)
            _dlog("패스키 페이지 우회 - 메인으로 이동")
        except Exception as e:
            _dlog(f"패스키 스킵 실패: {e}")

    def write_post(self, title: str, body: str, tags: list[str],
                   image_paths: list[str] = None, category: str = "",
                   schedule_time: str = None,
                   place_name: str = "", place_address: str = "",
                   align_after_last: bool = False, align_offset_sec: int = 7200) -> bool:
        """블로그 글 작성 및 발행. align_after_last=True 시 다이얼로그에서 기존 예약 확인 후 schedule_time 자동 조정."""
        try:
            # macOS AppleDouble 메타파일(`._*`) 안전 필터 (네이버가 "알 수 없는 파일"로 거부)
            if image_paths:
                _orig = len(image_paths)
                image_paths = [p for p in image_paths
                               if p and not os.path.basename(p).startswith("._")]
                _filtered = _orig - len(image_paths)
                if _filtered:
                    _dlog(f"AppleDouble 메타파일 {_filtered}개 제외")
            _dlog(f"=== write_post 시작: {title[:30]} === (이미지 {len(image_paths or [])}장, 본문 마커 {body.count('[이미지]')}개)")
            # 글쓰기 페이지로 직접 이동
            write_url = self.BLOG_WRITE_URL.format(blog_id=self.blog_id)
            self.driver.get(write_url)
            _dlog(f"URL 이동 완료: {self.driver.current_url}")
            self._sleep(0.35)

            # JS alert 먼저 처리
            try:
                alert = self.driver.switch_to.alert
                _dlog(f"JS alert 감지: {alert.text}")
                alert.dismiss()
                self._sleep(0.2)
            except Exception:
                pass

            _dlog(f"sleep 후 현재 URL: {self.driver.current_url}")

            # mainFrame iframe이 있으면 전환, 없으면 직접 접근
            try:
                main_iframe = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#mainFrame, iframe[name='mainFrame']"))
                )
                self.driver.switch_to.frame(main_iframe)
                _dlog("mainFrame iframe 전환 완료")
            except Exception:
                _dlog("mainFrame iframe 없음 - 직접 접근")

            # 에디터 로딩 대기 (제목 영역 또는 SE 컴포넌트)
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".se-title-text, .se-component"))
                )
                _dlog("SmartEditor 로딩 확인")
            except Exception as e:
                _dlog(f"SmartEditor 로딩 실패: {e}")
                try:
                    all_iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    _dlog(f"iframe 개수: {len(all_iframes)}")
                    for idx, ifr in enumerate(all_iframes):
                        _dlog(f"  iframe[{idx}] id={ifr.get_attribute('id')} name={ifr.get_attribute('name')}")
                    src = self.driver.page_source[:1500]
                    _dlog(f"page_source:\n{src}")
                except Exception:
                    pass
                raise
            self._sleep(0.35)

            # "작성 중인 글" 팝업 즉시 처리 (대기 없음)
            try:
                res = self.driver.execute_script("""
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        const txt = (btn.textContent || '').trim();
                        if (txt === '취소') {
                            const rect = btn.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                btn.click();
                                return 'clicked';
                            }
                        }
                    }
                    return 'none';
                """)
                _dlog(f"'작성 중인 글' 팝업: {res}")
                if res == 'clicked':
                    self._sleep(0.15)
            except Exception as e:
                _dlog(f"팝업 처리 실패: {e}")

            # 저장된 모든 임시저장 글 삭제
            self._delete_all_drafts()

            try:
                close_btn = self.driver.find_element(
                    By.CSS_SELECTOR, ".se-help-panel-close-button, [class*='close'][class*='help']"
                )
                close_btn.click()
                _dlog("도움말 팝업 닫기")
                self._sleep(0.25)
            except Exception:
                pass

            _dlog("제목 입력 시작")
            self._input_title(title)
            _dlog("제목 입력 완료")
            self._sleep(0.2)

            _dlog("본문 입력 시작")
            self._input_body(body, image_paths)
            _dlog("본문 입력 완료")
            self._sleep(0.2)

            if place_name:
                _dlog(f"장소 삽입 시작: {place_name}")
                self._insert_place(place_name, place_address)
                _dlog("장소 삽입 완료")
                self._sleep(0.2)

            if schedule_time:
                _dlog("예약 발행")
                _ok = self._schedule_publish(schedule_time, category=category, tags=tags,
                                             align_after_last=align_after_last, align_offset_sec=align_offset_sec)
                if _ok is False:
                    _dlog("=== write_post 실패: _schedule_publish False 반환 ===")
                    return False
            else:
                _dlog("즉시 발행")
                self._publish(category=category, tags=tags)

            self._sleep(1.2)
            _dlog("=== write_post 성공 ===")
            return True

        except InterruptedError:
            _dlog("=== write_post 사용자 중단 ===")
            return False
        except Exception as e:
            _dlog(f"!!! 글 작성 실패: {e}")
            import traceback
            _dlog(traceback.format_exc())
            print(f"글 작성 실패: {e}")
            traceback.print_exc()
            return False

    def _ac_type(self, text: str):
        """포커스된 요소에 텍스트 전체 일괄 입력"""
        if not text:
            return
        ActionChains(self.driver).send_keys(text).perform()

    def _ac_key(self, key):
        ActionChains(self.driver).send_keys(key).perform()

    def _set_clipboard(self, text: str):
        """클립보드에 텍스트 저장 — Windows ctypes 사용 (GUI 없어 focus 충돌 없음)"""
        try:
            import ctypes
            from ctypes import wintypes
            CF_UNICODETEXT = 13
            GMEM_MOVEABLE = 0x0002
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            # 데이터 복사
            data = text.encode("utf-16-le") + b"\x00\x00"
            h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h:
                return False
            ptr = kernel32.GlobalLock(h)
            if not ptr:
                kernel32.GlobalFree(h)
                return False
            ctypes.memmove(ptr, data, len(data))
            kernel32.GlobalUnlock(h)
            # 클립보드 set
            if not user32.OpenClipboard(0):
                kernel32.GlobalFree(h)
                return False
            try:
                user32.EmptyClipboard()
                user32.SetClipboardData(CF_UNICODETEXT, h)
            finally:
                user32.CloseClipboard()
            return True
        except Exception as e:
            _dlog(f"클립보드 설정 실패: {e}")
            return False

    def _paste_chunked(self, text: str, target_sec: float = 5.0):
        """텍스트를 chunk로 나눠 Ctrl+V로 붙여넣기 — 총 target_sec 초 안팎으로 분산.
        ActionChains.send_keys보다 훨씬 빠르면서 즉시 paste보다는 자연스러운 타이밍."""
        if not text:
            return
        # chunk 수: 글자수에 따라 5~12개
        n = max(5, min(12, len(text) // 80))
        chunk_size = max(1, (len(text) + n - 1) // n)
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        delay = max(0.05, (target_sec - 0.3 * len(chunks)) / max(1, len(chunks)))
        _dlog(f"chunked paste — {len(chunks)}개, chunk_size={chunk_size}, delay={delay:.2f}s")
        for ch in chunks:
            if not self._set_clipboard(ch):
                # 클립보드 실패 시 ActionChains 폴백
                ActionChains(self.driver).send_keys(ch).perform()
            else:
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            self._sleep(delay)

    def _input_title(self, title: str):
        """제목 입력 — SmartEditor ONE contenteditable. 포커스 검증 + 결과 검증 + 최대 3회 재시도."""
        title_area = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".se-title-text"))
        )

        def _focus_title_editable():
            # title 영역 안의 진짜 contenteditable 찾아서 포커스
            return self.driver.execute_script("""
                const wrap = document.querySelector('.se-title-text');
                if (!wrap) return 'no_wrap';
                // contenteditable 자식 우선, 없으면 wrap 자체
                const editable = wrap.querySelector('[contenteditable="true"], .se-text-paragraph, .se-placeholder')
                              || wrap;
                editable.focus();
                editable.click();
                // 활성 요소가 title 영역 안에 있는지 확인
                const ae = document.activeElement;
                const ok = ae && wrap.contains(ae);
                return ok ? 'focused' : ('focus_lost:' + (ae ? ae.tagName : 'null'));
            """)

        def _read_title_text():
            return self.driver.execute_script("""
                const wrap = document.querySelector('.se-title-text');
                if (!wrap) return '';
                // 플레이스홀더 자식 제외
                const para = wrap.querySelector('.se-text-paragraph, [contenteditable="true"]');
                return ((para || wrap).textContent || '').trim();
            """)

        last_err = ""
        for attempt in range(1, 4):
            # 1) 클릭 + 포커스 검증
            try:
                ActionChains(self.driver).move_to_element(title_area).click().perform()
            except Exception as e:
                last_err = f"click 실패: {e}"
            self._sleep(0.25)
            focus_state = _focus_title_editable()
            _dlog(f"제목 포커스 상태[{attempt}]: {focus_state}")

            # 2) 기존 텍스트 비우기 (이전 시도/잔여)
            try:
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
                ActionChains(self.driver).send_keys(Keys.DELETE).perform()
                self._sleep(0.15)
            except Exception:
                pass

            # 3) 타이핑
            self._ac_type(title)
            self._sleep(0.4)

            # 4) 결과 검증
            actual = _read_title_text()
            _dlog(f"제목 입력 검증[{attempt}]: 기대='{title}', 실제='{actual}'")
            # 정확히 같거나 충분히 비슷하면 (공백/줄바꿈 차이 무시) 성공
            if actual.replace(" ", "").replace("\n", "") == title.replace(" ", "").replace("\n", ""):
                return
            if actual and title and (title in actual or actual in title):
                return
            last_err = f"입력 후 비교 실패: 실제='{actual}'"

        _dlog(f"⚠️ 제목 입력 최종 실패 (3회 재시도): {last_err}")

    def _normalize_image_markers(self, body: str, n: int) -> str:
        """본문의 모든 이미지 마커([이미지] / [사진N])를 일관 처리.
        이미 적정 수가 상단~하단에 퍼져 있으면 형식만 [이미지]로 통일해 유지,
        아니면 둘 다 전부 제거 후 문단 사이에 n개를 균등 재배치한다.
        (형식 혼재로 마커가 중복돼 사진이 두 번씩 들어가던 버그 방지)"""
        import re as _re
        MARK = r'(?:\[이미지\]|\[사진\s*\d+\])'
        if n <= 0:
            return _re.sub(r'[ \t]*' + MARK + r'[ \t]*\n?', '', body).strip()
        # 이미지 배치 방식 — 'top'(사진 먼저 몰기: 수익형 광고클릭 유도) / 'spread'(문단 사이 교차)
        try:
            from config import load_config as _lc
            _layout = (_lc() or {}).get("image_layout", "top")
        except Exception:
            _layout = "top"
        if _layout == "top":
            _b = _re.sub(r'[ \t]*' + MARK + r'[ \t]*\n?', '', body).strip()
            _markers = '\n'.join(['[이미지]'] * n)
            _out = _markers + ('\n\n' + _b if _b else '')
            _dlog(f"[이미지] 마커 상단 일괄 배치(사진먼저): {n}개")
            return _re.sub(r'\n{3,}', '\n\n', _out).strip()
        positions = [m.start() for m in _re.finditer(MARK, body)]
        L = max(1, len(body))
        # 마커 수가 정확히 n + 상단~하단 분산 → 형식만 [이미지]로 통일해 유지 (무조건 n장 보장)
        if (len(positions) == n
                and positions[0] < L * 0.45 and positions[-1] > L * 0.55):
            return _re.sub(MARK, '[이미지]', body)
        # 재배치: 기존 마커(둘 다) 제거 후 문단 사이 균등 삽입
        body = _re.sub(r'[ \t]*' + MARK + r'[ \t]*', '', body)
        lines = body.split('\n')
        para = [i for i, l in enumerate(lines)
                if l.strip() and not l.strip().startswith('#') and '[지도]' not in l]
        if len(para) < 2:
            for _ in range(n):
                lines.append('[이미지]')
            return _re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()
        inner = para[1:] if len(para) > n + 1 else para   # 서론 첫 문단 다음부터
        cnt = min(n, len(inner))
        picks = []
        seen = set()
        for k in range(cnt):
            j = int(round((k + 1) * len(inner) / (cnt + 1))) - 1
            j = max(0, min(len(inner) - 1, j))
            while inner[j] in seen and j < len(inner) - 1:
                j += 1
            if inner[j] in seen:
                continue
            seen.add(inner[j])
            picks.append(inner[j])
        for pos in sorted(picks, reverse=True):
            lines.insert(pos + 1, '[이미지]')
        _dlog(f"[이미지] 마커 재배치: 마커 {len(positions)}개 → {len(picks)}개 균등 분산 (이미지 {n}장)")
        return _re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()

    def _input_body(self, body: str, image_paths: list[str] = None):
        """본문 입력 — 클릭으로 포커스 후 ActionChains로 키 전송"""
        body_area = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".se-component.se-text .se-text-paragraph, .se-main-container"))
        )
        ActionChains(self.driver).move_to_element(body_area).click().perform()
        self._sleep(0.25)

        # 활성 서식 버튼 모두 끔 (se-is-selected / se-is-on 체크)
        try:
            toggled = self.driver.execute_script("""
                const targetClasses = [
                    'se-bold-toolbar-button',
                    'se-italic-toolbar-button',
                    'se-underline-toolbar-button',
                    'se-strikethrough-toolbar-button'
                ];
                const results = [];
                targetClasses.forEach(tc => {
                    const btn = document.querySelector('.' + tc);
                    if (btn && (btn.classList.contains('se-is-selected') || btn.classList.contains('se-is-on'))) {
                        btn.click();
                        results.push(tc);
                    }
                });
                return results;
            """)
            _dlog(f"서식 토글 해제: {toggled}")
        except Exception as e:
            _dlog(f"서식 토글 해제 실패: {e}")
        self._sleep(0.15)

        # 본문 영역 재포커스
        try:
            ActionChains(self.driver).move_to_element(body_area).click().perform()
            self._sleep(0.2)
        except Exception:
            pass

        import re as _re

        # [지도] 마커는 별도 단계에서 처리 — 본문 입력 시 제거
        body = body.replace('[지도]', '')

        # 이미지가 본문 중간에 고르게 들어가도록 [이미지] 마커 보정 (위 뭉침/누락 방지)
        body = self._normalize_image_markers(body, len(image_paths or []))

        # 하위 호환: 구형 [이미지] 마커 → [사진N] 순서대로 변환
        _old_idx = [0]
        def _upgrade_marker(m):
            _old_idx[0] += 1
            return f'[사진{_old_idx[0]}]'
        body = _re.sub(r'\[이미지\]', _upgrade_marker, body)

        # 마커 위치 검증 (디버깅용) — 마커 앞뒤에 줄바꿈 없으면 경고
        for _m in _re.finditer(r'\[사진\d+\]', body):
            _pos = _m.start()
            _before = body[max(0, _pos-1):_pos]
            _after = body[_m.end():_m.end()+1]
            if _before and _before != '\n' and _after and _after != '\n':
                _dlog(f"마커 위치 경고: '{_m.group()}' 앞뒤 줄바꿈 없음")

        # [사진N] 마커 기반 분리 — 번호로 image_paths 인덱스 매핑
        _marker_re = _re.compile(r'\[사진(\d+)\]')
        segments = _marker_re.split(body)
        # segments: [text0, num1, text1, num2, text2, ...]
        # 짝수 인덱스 = 텍스트, 홀수 인덱스 = 마커 번호

        for i, chunk in enumerate(segments):
            if i % 2 == 0:
                # 텍스트 파트
                text_block = chunk.strip()
                if text_block:
                    # [소제목] 태그 제거
                    cleaned_lines = []
                    for line in text_block.split("\n"):
                        s = line.strip()
                        if s.startswith("[소제목]"):
                            s = s.replace("[소제목]", "").strip()
                        cleaned_lines.append(s)
                    combined = "\n".join(cleaned_lines)
                    # 클립보드 paste — ctypes 사용 (focus 충돌 없음, ActionChains 대비 빠름)
                    if self._set_clipboard(combined):
                        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                    else:
                        ActionChains(self.driver).send_keys(combined).perform()
                    self._ac_key(Keys.ENTER)
            else:
                # 이미지 마커 번호 파트 — [사진N] → image_paths[N-1]
                img_idx = int(chunk) - 1
                if image_paths and 0 <= img_idx < len(image_paths):
                    self._insert_image(image_paths[img_idx])
                    self._sleep(0.2)
                    # 이미지 캡션에서 빠져나와 문서 끝 본문 영역으로 커서 이동
                    try:
                        # Escape로 캡션/이미지 편집 모드 종료
                        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                        self._sleep(0.2)
                        # JS로 문서 마지막 본문 문단 끝에 포커스 설정
                        self.driver.execute_script("""
                            const paragraphs = document.querySelectorAll('.se-main-container .se-text-paragraph:not(.se-caption)');
                            let target = null;
                            for (let i = paragraphs.length - 1; i >= 0; i--) {
                                const p = paragraphs[i];
                                if (!p.closest('.se-image, .se-component.se-image, [class*="caption"]')) {
                                    target = p;
                                    break;
                                }
                            }
                            if (target) {
                                target.focus();
                                const range = document.createRange();
                                range.selectNodeContents(target);
                                range.collapse(false);
                                const sel = window.getSelection();
                                sel.removeAllRanges();
                                sel.addRange(range);
                                target.click();
                            }
                        """)
                        self._sleep(0.15)
                        # 새 줄 시작
                        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                        self._sleep(0.2)
                    except Exception as e:
                        _dlog(f"커서 이동 실패: {e}")
                else:
                    _dlog(f"[사진{chunk}] 마커: 이미지 없음 (index {img_idx}, 총 {len(image_paths or [])}장) — 스킵")

    def _insert_place(self, place_name: str, place_address: str = ""):
        """툴바의 '장소' 버튼 클릭해서 장소 카드 삽입"""
        try:
            # 장소 버튼 클릭
            place_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".se-map-toolbar-button, button[class*='map-toolbar-button']"))
            )
            place_btn.click()
            self._sleep(0.6)

            # 검색 입력창에 업체명 입력
            search_input = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".se-map-search-input, input[class*='map-search'], input[placeholder*='장소']"))
            )
            search_input.click()
            search_input.clear()
            ActionChains(self.driver).send_keys(place_name).perform()
            self._sleep(0.15)
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            self._sleep(0.35)

            # 검색 결과의 "+ 추가" 버튼 클릭 — 장소 팝업 내에서 '추가' 텍스트 버튼 찾기
            self._sleep(0.6)
            try:
                clicked = self.driver.execute_script("""
                    const targetName = (arguments[1]||'').replace(/\\s+/g,'');
                    const placePopup = document.querySelector('[class*="placesMap"], [class*="place-popup"], [class*="map-popup"]');
                    const scope = placePopup || document;
                    const addBtns = Array.from(scope.querySelectorAll('button')).filter(b => {
                        const t = (b.textContent||'').trim();
                        return t === '추가' || t === '+ 추가' || t.startsWith('+ 추가');
                    });
                    if (addBtns.length === 0) return 'no_add';
                    // 주소 토큰(2글자 이상)으로 올바른 결과 선택
                    const addrToks = (arguments[0]||'').split(/[\\s,]+/).filter(s => s && s.length >= 2);
                    // '추가' 버튼이 속한 결과 행의 텍스트 추출 (목록 전체로 번지지 않게 250자 제한)
                    function rowText(b){
                        let el = b, last = b;
                        for (let i=0; i<8 && el; i++){
                            el = el.parentElement;
                            if (!el) break;
                            const tx = (el.textContent||'').trim();
                            if (tx.length > 250) break;
                            last = el;
                            if ((el.tagName||'').toLowerCase() === 'li') return tx;
                        }
                        return (last.textContent||'').trim();
                    }
                    let best = null, bestScore = -1, bestIdx = 0;
                    addBtns.forEach((b, i) => {
                        const ctx = rowText(b).replace(/\\s+/g,'');
                        let score = 0;
                        for (const tok of addrToks){
                            if (ctx.indexOf(tok.replace(/\\s+/g,'')) >= 0) score += 2;
                        }
                        if (targetName && ctx.indexOf(targetName) >= 0) score += 1;
                        if (score > bestScore){ bestScore = score; best = b; bestIdx = i; }
                    });
                    // 주소가 하나도 안 맞으면(score 0) 기존처럼 첫 결과로 폴백
                    const chosen = (bestScore > 0 ? best : addBtns[0]);
                    chosen.click();
                    return 'clicked idx=' + (bestScore>0?bestIdx:0) + ' score=' + bestScore + '/' + addBtns.length;
                """, place_address or "", place_name or "")
                _dlog(f"장소 '+ 추가' 클릭(주소매칭): {clicked}")
                self._sleep(0.2)
            except Exception as e:
                _dlog(f"추가 버튼 클릭 실패: {e}")

            # 최종 확인 버튼 (지도 + 확인 다이얼로그)
            self._sleep(0.2)
            try:
                confirm = self.driver.execute_script("""
                    const btns = Array.from(document.querySelectorAll('button'));
                    const b = btns.find(x => {
                        const t = (x.textContent||'').trim();
                        const rect = x.getBoundingClientRect();
                        // '확인' 또는 '완료' 포함 (체크마크/공백 허용)
                        const hasText = t.includes('확인') || t.includes('완료');
                        const visible = rect.width > 0 && rect.height > 0;
                        // 너무 긴 텍스트(전체 페이지 버튼)는 제외
                        return hasText && visible && t.length < 15;
                    });
                    if (b) { b.click(); return 'clicked:' + (b.textContent||'').trim(); }
                    return 'none';
                """)
                _dlog(f"장소 확인 버튼: {confirm}")
                self._sleep(0.35)
            except Exception as e:
                _dlog(f"장소 확인 버튼 클릭 실패: {e}")

        except Exception as e:
            _dlog(f"장소 삽입 실패: {e}")

    def _enter_main_frame(self):
        """최상위로 나갔다가 #mainFrame 에디터 프레임으로 복귀."""
        try:
            self.driver.switch_to.default_content()
            mf = self.driver.find_elements(By.CSS_SELECTOR, "iframe#mainFrame, iframe[name='mainFrame']")
            if mf:
                self.driver.switch_to.frame(mf[0])
        except Exception:
            pass

    def _try_send_file(self, abs_path: str) -> bool:
        """최상위 문서부터 모든 중첩 iframe까지 DFS로 뒤져 input[type=file]에 send_keys.
        (네이버 SmartEditor는 업로드 input을 mainFrame 내부의 중첩 iframe에 둔다)
        성공/실패와 무관하게 mainFrame으로 복귀한다."""
        try:
            self.driver.switch_to.default_content()
            found = self._dfs_send_file(abs_path, 0)
        except Exception as e:
            _dlog(f"프레임 탐색 오류: {e}")
            found = False
        self._enter_main_frame()
        return found

    def _dfs_send_file(self, abs_path: str, depth: int) -> bool:
        """현재 프레임의 file input 시도 후, 자식 iframe들로 재귀 하강."""
        # 0) 주입 스크립트가 캡처한 (detached였던) input 참조 우선 시도
        try:
            el = self.driver.execute_script("return window.__naverFileInput || null;")
            if el is not None:
                try:
                    el.send_keys(abs_path)
                    self.driver.execute_script("try{window.__naverFileInput=null;}catch(e){}")
                    _dlog(f"파일 경로 전송 성공 (캡처 input, depth {depth})")
                    return True
                except Exception as e:
                    _dlog(f"캡처 input send_keys 실패: {e}")
        except Exception:
            pass
        try:
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            if inputs:
                _dlog(f"file input {len(inputs)}개 발견 (frame depth {depth})")
            for fi in inputs:
                try:
                    fi.send_keys(abs_path)
                    _dlog(f"파일 경로 전송 성공 (frame depth {depth})")
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        if depth >= 4:
            return False
        try:
            n = len(self.driver.find_elements(By.CSS_SELECTOR, "iframe"))
        except Exception:
            n = 0
        for i in range(n):
            try:
                frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe")
                if i >= len(frames):
                    break
                self.driver.switch_to.frame(frames[i])
            except Exception:
                continue
            try:
                if self._dfs_send_file(abs_path, depth + 1):
                    return True
            finally:
                try:
                    self.driver.switch_to.parent_frame()
                except Exception:
                    pass
        return False

    def _dump_image_dom_debug(self):
        """이미지 삽입 실패 시 최상위~모든 중첩 iframe의 file input/이미지버튼을 재귀로 로그."""
        try:
            self.driver.switch_to.default_content()
            self._dump_frames_recursive(0, "top")
        except Exception as e:
            _dlog(f"[진단] 덤프 실패: {e}")
        finally:
            self._enter_main_frame()

    def _dump_frames_recursive(self, depth: int, label: str):
        try:
            info = self.driver.execute_script("""
                const r = {fileInputs: document.querySelectorAll("input[type=file]").length,
                           iframes: document.querySelectorAll('iframe').length, imgBtns: []};
                document.querySelectorAll('button, a').forEach(b => {
                    const c=((b.className||'')+''),
                          d=(b.getAttribute('data-name')||b.getAttribute('aria-label')||''),
                          t=(b.textContent||'').trim().slice(0,10);
                    if(/image|photo|사진|img/i.test(c+' '+d+' '+t))
                        r.imgBtns.push(c.slice(0,45)+'|'+d+'|'+t);
                });
                return r;
            """)
            _dlog(f"[진단] {label} (depth {depth}): {info}")
        except Exception as e:
            _dlog(f"[진단] {label} 평가 실패: {e}")
            return
        if depth >= 4:
            return
        try:
            n = len(self.driver.find_elements(By.CSS_SELECTOR, "iframe"))
        except Exception:
            n = 0
        for i in range(n):
            try:
                frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe")
                if i >= len(frames):
                    break
                self.driver.switch_to.frame(frames[i])
            except Exception:
                continue
            try:
                self._dump_frames_recursive(depth + 1, f"{label}>if[{i}]")
            finally:
                try:
                    self.driver.switch_to.parent_frame()
                except Exception:
                    pass

    def _insert_image(self, image_path: str):
        """이미지 삽입 — 사진 버튼(실제 클릭) 후 생성되는 input[type=file]에 경로 전송.
        파일 input을 mainFrame/최상위 양쪽에서 찾고, 실패하면 DOM 진단을 남긴다."""
        try:
            abs_path = os.path.abspath(image_path)
            if not os.path.exists(abs_path):
                _dlog(f"이미지 파일 없음 — 스킵: {abs_path}")
                return
            _dlog(f"이미지 삽입 시도: {abs_path}")

            _img_btn_selectors = [
                "button[data-name='image']",
                "button.se-toolbar-item-image", ".se-toolbar-item-image button",
                "button[data-log*='photo']", "button[data-log*='image']",
                "button[aria-label*='사진']", "button[title*='사진']",
                ".se-image-toolbar-button", "button[class*='image-toolbar-button']",
                ".se-document-toolbar button[class*='image']",
                "button[class*='image'][class*='toolbar']",
            ]
            sent = False
            for attempt in range(3):
                # 1) 사진 버튼 — 실제 클릭(ActionChains) 우선, 실패 시 JS 클릭
                clicked_sel = None
                for sel in _img_btn_selectors:
                    try:
                        btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                        try:
                            ActionChains(self.driver).move_to_element(btn).pause(0.1).click().perform()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", btn)
                        clicked_sel = sel
                        break
                    except Exception:
                        continue
                _dlog(f"사진 버튼 클릭: {clicked_sel or '못 찾음'} (시도 {attempt+1})")
                self._sleep(0.6)

                # 2) file input 탐색 + 경로 전송 (mainFrame → 최상위)
                if self._try_send_file(abs_path):
                    sent = True
                    break
                self._sleep(0.6)

            if not sent:
                self._dump_image_dom_debug()
                raise Exception("file input에 경로 전송 실패")
            self._sleep(0.5)

            # 업로드 완료 대기 — 이미지가 중첩 프레임에 삽입될 수 있어 비치명적 + 짧게(8s)
            # (못 찾을 때 30초씩 행 걸려 발행이 느려지던 문제 → 8초로 단축)
            try:
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".se-image-resource, .se-module-image, .se-component.se-image"))
                )
                _dlog("이미지 업로드 완료")
            except Exception:
                _dlog("이미지 업로드 확인 요소 못 찾음 — 전송은 성공, 업로드 시간 확보 후 계속")
                self._sleep(1.0)
            self._sleep(0.2)

        except Exception as e:
            _dlog(f"이미지 삽입 실패: {e}")
            print(f"이미지 삽입 실패: {e}")

    def _delete_all_drafts(self):
        """임시저장 목록 팝업을 열고 전체 삭제"""
        try:
            # 툴바 우측 '저장' 카운트 버튼 클릭 (임시저장 목록 팝업 오픈)
            opened = self.driver.execute_script("""
                // 카운트 배지 있는 저장 버튼 찾기
                const btns = document.querySelectorAll('button');
                for (const b of btns) {
                    const cls = (b.className||'').toString().toLowerCase();
                    const txt = (b.textContent||'').trim();
                    if (cls.includes('save_list') || cls.includes('save_btn_count') || cls.includes('saved_list')
                        || (txt.includes('저장') && /\\d+/.test(txt))) {
                        const rect = b.getBoundingClientRect();
                        if (rect.width > 0) {
                            b.click();
                            return 'opened:' + cls.substring(0,40);
                        }
                    }
                }
                return 'no_button';
            """)
            _dlog(f"임시저장 버튼: {opened}")
            if 'opened' not in str(opened):
                return
            self._sleep(0.35)

            # 개별 삭제 버튼(휴지통) 하나씩 클릭
            deleted = 0
            for _ in range(30):
                result = self.driver.execute_script("""
                    // '임시저장 글' 다이얼로그 내 휴지통 버튼
                    const dialog = Array.from(document.querySelectorAll('*')).find(el =>
                        el.textContent && el.textContent.includes('임시저장 글')
                        && el.querySelectorAll('button').length > 0
                    );
                    const scope = dialog || document;
                    const btns = scope.querySelectorAll('button');
                    for (const b of btns) {
                        const cls = (b.className||'').toString().toLowerCase();
                        const aria = (b.getAttribute('aria-label')||'').toLowerCase();
                        const rect = b.getBoundingClientRect();
                        if (rect.width === 0 || rect.width > 100) continue;  // 너무 큰 건 제외
                        // 휴지통 아이콘 버튼: class나 aria-label에 delete/remove/삭제 포함
                        if (cls.includes('delete') || cls.includes('remove') || cls.includes('trash')
                            || aria.includes('삭제') || aria.includes('delete')) {
                            b.click();
                            return 'clicked:' + (cls.substring(0,30) + '|' + aria);
                        }
                        // SVG/아이콘만 있는 작은 버튼 (텍스트 없고 크기 작음)
                        const txt = (b.textContent||'').trim();
                        if (txt === '' && rect.width < 40 && rect.height < 40) {
                            // 부모가 리스트 항목이면 삭제 버튼으로 간주
                            const parent = b.closest('li, [class*="item"], [class*="row"]');
                            if (parent) {
                                b.click();
                                return 'clicked_icon';
                            }
                        }
                    }
                    return 'no_more';
                """)
                if str(result).startswith('clicked') or result == 'clicked_icon':
                    deleted += 1
                    self._sleep(0.2)
                    # 확인 팝업 처리
                    try:
                        self.driver.execute_script("""
                            const btns = document.querySelectorAll('button');
                            for (const b of btns) {
                                const t = (b.textContent||'').trim();
                                if ((t === '확인' || t === '삭제') && b.getBoundingClientRect().width > 0) {
                                    b.click();
                                    return;
                                }
                            }
                        """)
                        self._sleep(0.15)
                    except Exception:
                        pass
                else:
                    break
            _dlog(f"임시저장 글 {deleted}개 삭제")

            # 다이얼로그 닫기
            try:
                self.driver.execute_script("""
                    const btns = document.querySelectorAll('button');
                    for (const b of btns) {
                        const aria = (b.getAttribute('aria-label')||'').toLowerCase();
                        if (aria.includes('close') || aria === '닫기') {
                            b.click();
                            return;
                        }
                    }
                """)
                self._sleep(0.2)
            except Exception:
                pass
        except Exception as e:
            _dlog(f"임시저장 삭제 실패: {e}")

    def peek_reservations(self) -> list:
        """글쓰기 페이지 진입 → 발행 다이얼로그 → 예약 목록 시간 읽기 → 닫기.
        반환: list[datetime]. 호출 전제: 이미 로그인 상태."""
        try:
            write_url = self.BLOG_WRITE_URL.format(blog_id=self.blog_id)
            self.driver.get(write_url)
            self._sleep(2)
            try:
                self.driver.switch_to.alert.dismiss()
                self._sleep(0.2)
            except Exception:
                pass
            try:
                main_iframe = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#mainFrame, iframe[name='mainFrame']"))
                )
                self.driver.switch_to.frame(main_iframe)
            except Exception:
                pass
            self._sleep(0.5)
            # SmartEditor 로딩
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".se-component, .se-title-text"))
                )
            except Exception:
                pass
            # 작성 중인 글 팝업 처리
            try:
                self.driver.execute_script("""
                    document.querySelectorAll('button').forEach(b => {
                        if ((b.textContent||'').trim() === '취소') b.click();
                    });
                """)
                self._sleep(0.2)
            except Exception:
                pass
            # 발행 버튼 클릭 (오버레이 제거)
            try:
                self.driver.execute_script("""
                    document.querySelectorAll('.se-popup-dim, [class*="popup-dim"], [class*="dim"]').forEach(el => el.remove());
                """)
                publish_btn = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button[class*='publish_btn']"))
                )
                self.driver.execute_script("arguments[0].click();", publish_btn)
                self._sleep(1.5)
            except Exception as e:
                _dlog(f"peek 발행 버튼 클릭 실패: {e}")
                return []
            result = self.get_existing_reservations()
            # 상태 리셋 — write_post 재진입 시 충돌 방지
            try:
                self.driver.switch_to.default_content()
                self.driver.get("https://blog.naver.com")
                self._sleep(0.8)
            except Exception:
                pass
            return result
        except Exception as e:
            _dlog(f"peek_reservations 실패: {e}")
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            return []

    def get_existing_reservations(self) -> list:
        """발행 다이얼로그에서 기존 예약 발행 글 목록의 시간을 읽어옴.
        반환: list[datetime] — 빈 리스트면 예약 없음.
        호출 전제: 발행 다이얼로그가 이미 열려있어야 함."""
        import datetime as _dt
        import re as _re
        try:
            # 1) 예약 발행 [N]건 버튼 클릭 — 버튼 라벨의 'N건' 총수도 함께 캡처
            #    (예약 목록 패널은 가상 스크롤이라 날짜 span이 실제 예약 수보다 적게 렌더됨.
            #     'N건' 라벨이 정확한 총 예약 수이므로 99 한도 판정에 사용 — self.reservation_total)
            self.reservation_total = -1
            click_res = self.driver.execute_script(r"""
                const btns = document.querySelectorAll('button[class*="reserve_btn"], button[data-click-area*="schedule"]');
                for (const b of btns) {
                    const r = b.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) {
                        const m = ((b.textContent||'').trim()).match(/(\d+)\s*건/);
                        b.click();
                        return {ok: true, total: m ? parseInt(m[1], 10) : -1};
                    }
                }
                return {ok: false, total: -1};
            """)
            _dlog(f"예약 목록 버튼 클릭: {click_res}")
            try:
                if isinstance(click_res, dict):
                    self.reservation_total = int(click_res.get("total", -1))
            except Exception:
                self.reservation_total = -1
            _dlog(f"예약 총수(N건 라벨): {self.reservation_total}")
            if not (isinstance(click_res, dict) and click_res.get("ok")):
                return []
            # 2) 모달/리스트 뜰 때까지 Python 폴링 — 각 span의 부모 컨텍스트도 같이 캡처
            dates_with_context = []
            for _ in range(20):
                self._sleep(0.15)
                dates_with_context = self.driver.execute_script(r"""
                    const out = [];
                    document.querySelectorAll('span[class*="date__"]').forEach(el => {
                        const t = (el.textContent || '').trim();
                        if (!t) return;
                        // 부모 체인 4단계 클래스
                        const parents = [];
                        let cur = el.parentElement;
                        for (let i = 0; i < 4 && cur; i++) {
                            parents.push((cur.className || '').toString().slice(0, 80));
                            cur = cur.parentElement;
                        }
                        out.push({text: t, parents: parents});
                    });
                    return out;
                """)
                if dates_with_context:
                    break
            _dlog(f"예약 날짜 raw (상세): {dates_with_context}")
            dates = [d.get("text") for d in (dates_with_context or [])]
            _dlog(f"예약 날짜 텍스트만: {dates}")
            # 3) 파싱: "2026.05.05 22:40" 형식
            parsed = []
            for s in (dates or []):
                m = _re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{1,2})", s)
                if m:
                    try:
                        parsed.append(_dt.datetime(
                            int(m.group(1)), int(m.group(2)), int(m.group(3)),
                            int(m.group(4)), int(m.group(5))
                        ))
                    except Exception:
                        pass
            # 4) 패널 닫기 — reserve_btn 다시 클릭으로 토글 (ESC는 발행 다이얼로그까지 닫을 위험)
            try:
                close_res = self.driver.execute_script(r"""
                    const btns = document.querySelectorAll('button[class*="reserve_btn"], button[data-click-area*="schedule"]');
                    for (const b of btns) {
                        const r = b.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) { b.click(); return 'toggled'; }
                    }
                    return 'no_btn';
                """)
                _dlog(f"예약 패널 토글 닫기: {close_res}")
                self._sleep(0.5)
                # 정말 닫혔는지 확인 (date span 0개여야 함)
                still_open = self.driver.execute_script(r"""
                    return document.querySelectorAll('span[class*="date__"]').length;
                """)
                if still_open and still_open > 0:
                    _dlog(f"⚠ 예약 패널이 닫히지 않음 (date span {still_open}개) — 한 번 더 시도")
                    self.driver.execute_script(r"""
                        const btns = document.querySelectorAll('button[class*="reserve_btn"], button[data-click-area*="schedule"]');
                        for (const b of btns) {
                            const r = b.getBoundingClientRect();
                            if (r.width > 0 && r.height > 0) { b.click(); break; }
                        }
                    """)
                    self._sleep(0.5)
            except Exception as _ce:
                _dlog(f"예약 패널 닫기 실패: {_ce}")
            return parsed
        except Exception as e:
            _dlog(f"기존 예약 조회 실패: {e}")
            return []

    def _input_tags(self, tags: list[str]):
        """태그 입력"""
        try:
            tag_input = self.driver.find_element(
                By.CSS_SELECTOR, ".se-tag-input input, #post-tag-input"
            )
            for tag in tags:
                tag_input.send_keys(tag)
                tag_input.send_keys(Keys.ENTER)
                self._sleep(0.2)
        except Exception as e:
            _dlog(f"태그 입력 실패: {e}")

    def _schedule_publish(self, schedule_time: str, category: str = "", tags: list = None,
                          align_after_last: bool = False, align_offset_sec: int = 7200):
        """예약 발행 — schedule_time 형식: 'YYYY-MM-DD HH:MM'.
        align_after_last=True 면 다이얼로그 안에서 기존 예약 목록 읽어서 가장 늦은 시간 + align_offset_sec 로 schedule_time 자동 조정."""
        try:
            # 잔여 팝업 제거
            try:
                self.driver.execute_script("""
                    document.querySelectorAll('.se-popup-dim, [class*="popup-dim"], [class*="placesMap"], [class*="place-popup"]').forEach(el => el.remove());
                """)
            except Exception:
                pass
            self._sleep(0.15)

            # 발행 다이얼로그 열기
            publish_btn = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, "button.publish_btn__m9KHH, button[class*='publish_btn']"
                ))
            )
            self.driver.execute_script("arguments[0].click();", publish_btn)
            _dlog("발행 다이얼로그 오픈")
            self._sleep(0.6)

            # 카테고리
            if category:
                self._select_category_in_dialog(category)
                self._sleep(0.15)

            # 태그칸 입력 제거 — 본문 끝 해시태그(#태그)를 네이버가 자동으로 태그로 변환하므로 중복 불필요
            _dlog("태그칸 입력 생략(본문 해시태그 자동 변환 사용)")

            # align_after_last 인라인 처리 제거 — 다이얼로그 안에서 예약 패널 열면
            # 발행 컨트롤(라디오/datepicker/시간/발행 버튼)이 가려져 발행 자체가 실패함.
            # main.py에서 poster.peek_reservations()로 base_time 잡은 후 schedule_time 계산해서 전달.

            # '예약' 라디오 선택 — label[for="radio_time2"].radio_label__*
            try:
                clicked = self.driver.execute_script("""
                    const lbl = document.querySelector('label[for="radio_time2"]')
                              || Array.from(document.querySelectorAll('label[class*="radio_label"]'))
                                   .find(l => (l.textContent||'').trim() === '예약');
                    if (lbl) { lbl.click(); return 'clicked'; }
                    return 'not_found';
                """)
                _dlog(f"예약 라디오: {clicked}")
                self._sleep(0.35)
            except Exception as e:
                _dlog(f"예약 라디오 선택 실패: {e}")

            # 날짜/시간 파싱
            try:
                date_str, time_str = schedule_time.split(" ")
                year, month, day = date_str.split("-")
                hour, minute = time_str.split(":")
            except (ValueError, AttributeError) as e:
                _dlog(f"예약 시간 형식 오류: '{schedule_time}' — {e}")
                return False
            # 네이버는 10분 단위 예약만 허용 — 10분 단위로 반올림
            minute_int = int(minute)
            minute_int = (minute_int // 10) * 10
            minute = f"{minute_int:02d}"

            # 날짜 input — jQuery UI datepicker 직접 조작 (네이버 발행 다이얼로그가 jQuery UI 사용)
            actual = ""

            def _validate(act: str) -> bool:
                if not act:
                    return False
                import re as _re
                nums = _re.findall(r"\d+", act)
                return (year in nums
                        and month.lstrip("0") in [n.lstrip("0") for n in nums]
                        and day.lstrip("0") in [n.lstrip("0") for n in nums])

            try:
                # 달력 열기 — input 클릭
                self.driver.execute_script("""
                    const inp = document.querySelector('input[class*="input_date"]');
                    if (inp) { inp.removeAttribute('readonly'); inp.focus(); inp.click(); }
                """)
                self._sleep(0.6)

                # JS 작업 단위 — busy-wait 없이 한 가지씩만 (Python에서 sleep 사이에 jQuery 처리 시간 부여)
                _GET_HEADER = r"""
                    const dps = document.querySelectorAll('.ui-datepicker:not(.ui-datepicker-header)');
                    let dp = null;
                    for (const x of dps) {
                        const r = x.getBoundingClientRect();
                        if (r.width > 100 && r.height > 100) { dp = x; break; }
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
                    for (const x of dps) {
                        const r = x.getBoundingClientRect();
                        if (r.width > 100 && r.height > 100) { dp = x; break; }
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
                    for (const sel of sels) {
                        for (const el of dp.querySelectorAll(sel)) {
                            const r = el.getBoundingClientRect();
                            if (r.width === 0 || r.height === 0) continue;
                            if (isOtherMonth(el)) continue;
                            const t = (el.textContent || el.getAttribute('data-date') || '').trim();
                            if (parseInt(t) === d) {
                                el.click();
                                ['mousedown','mouseup','click'].forEach(ev => {
                                    el.dispatchEvent(new MouseEvent(ev, {bubbles:true, cancelable:true, view:window}));
                                });
                                return 'clicked[' + sel + ']:' + d;
                            }
                        }
                    }
                    return 'day_not_found:' + d;
                """

                # Python 쪽에서 nav 루프 (Python sleep으로 jQuery에 처리 시간 부여)
                y_int, m_int, d_int = int(year), int(month), int(day)
                nav_count = 0
                last_err = ""
                for _ in range(36):
                    h = self.driver.execute_script(_GET_HEADER)
                    if not h:
                        last_err = "no_header"
                        break
                    if h.get("year") == y_int and h.get("month") == m_int:
                        break
                    go_next = (h["year"], h["month"]) < (y_int, m_int)
                    nav_sel = ".ui-datepicker-next" if go_next else ".ui-datepicker-prev"
                    before_y, before_m = h["year"], h["month"]
                    res = self.driver.execute_script(_CLICK_NAV, nav_sel)
                    nav_count += 1
                    if res != "clicked":
                        last_err = f"nav_{res}"
                        break
                    # Python sleep — 그 사이에 jQuery가 헤더 갱신
                    changed = False
                    for _ in range(20):
                        self._sleep(0.1)
                        h2 = self.driver.execute_script(_GET_HEADER)
                        if h2 and (h2.get("year") != before_y or h2.get("month") != before_m):
                            changed = True
                            break
                    if not changed:
                        last_err = f"stuck_at_{before_y}-{before_m}"
                        break

                # 일자 클릭
                if not last_err:
                    cal_res = self.driver.execute_script(_CLICK_DAY, d_int)
                else:
                    cal_res = f"skipped:{last_err}"
                cal_res = f"{cal_res},nav={nav_count}"
                self._sleep(0.6)
                actual = self.driver.execute_script(
                    "return document.querySelector('input[class*=\"input_date\"]').value || '';"
                )
                _dlog(f"jQuery UI datepicker 결과: {cal_res}, 실제='{actual}'")
            except Exception as e:
                _dlog(f"jQuery UI datepicker 실패: {e}")
                import traceback as _tb
                _dlog(_tb.format_exc())

            if not _validate(actual):
                _dlog(f"⚠️ 예약 날짜 설정 최종 실패: 모든 시도 실패. 마지막 실제값='{actual}', 목표={year}-{month}-{day}")

            # 시/분 드롭다운 — hour_option__* / minute_option__*
            try:
                set_time = self.driver.execute_script("""
                    const hour = arguments[0];
                    const minute = arguments[1];
                    const hSel = document.querySelector('select[class*="hour_option"]');
                    const mSel = document.querySelector('select[class*="minute_option"]');
                    const setValue = (sel, val) => {
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
                        setter.call(sel, val);
                        sel.dispatchEvent(new Event('input', {bubbles: true}));
                        sel.dispatchEvent(new Event('change', {bubbles: true}));
                    };
                    const out = [];
                    if (hSel) { setValue(hSel, hour); out.push('hour=' + hSel.value); }
                    else out.push('hour_sel_missing');
                    if (mSel) { setValue(mSel, minute); out.push('minute=' + mSel.value); }
                    else out.push('minute_sel_missing');
                    return out.join(', ');
                """, hour, minute)
                _dlog(f"예약 시간 설정: {schedule_time} → {set_time}")
                self._sleep(0.25)
            except Exception as e:
                _dlog(f"예약 시간 설정 실패: {e}")

            # === 최종 발행 직전 상태 캡처 ===
            try:
                pre_state = self.driver.execute_script("""
                    const btn = document.querySelector('button[aria-label*="카테고리"]');
                    const dateInp = document.querySelector('input[class*="input_date"]');
                    const hSel = document.querySelector('select[class*="hour_option"]');
                    const mSel = document.querySelector('select[class*="minute_option"]');
                    const reserveRadio = document.querySelector('input#radio_time2, input[id*="radio_time2"]');
                    return {
                        url: location.href,
                        category: btn ? (btn.textContent||'').trim() : '',
                        date: dateInp ? dateInp.value : '',
                        hour: hSel ? hSel.value : '',
                        minute: mSel ? mSel.value : '',
                        reserve_checked: reserveRadio ? reserveRadio.checked : null,
                    };
                """)
                _dlog(f"제출 직전 상태: {pre_state}")
            except Exception as _e:
                _dlog(f"제출 직전 상태 캡처 실패: {_e}")

            # 최종 발행 버튼 — data-testid="seOnePublishBtn" 또는 class="confirm_btn__*" 정확 매칭
            final_clicked = self.driver.execute_script("""
                let btn = document.querySelector('button[data-testid="seOnePublishBtn"]')
                       || document.querySelector('button[class*="confirm_btn__"]');
                if (btn) {
                    const rect = btn.getBoundingClientRect();
                    const disabled = btn.disabled || btn.getAttribute('aria-disabled') === 'true';
                    if (rect.width > 0 && rect.height > 0 && !disabled) {
                        btn.click();
                        return 'clicked_testid:visible_enabled';
                    } else {
                        return 'btn_found_but_blocked:rect=' + rect.width + 'x' + rect.height + ',disabled=' + disabled;
                    }
                }
                return 'not_found';
            """)
            _dlog(f"예약 발행 최종 클릭: {final_clicked}")
            self._sleep(2)

            # 확인 팝업 처리 (있으면 클릭)
            try:
                confirm_res = self.driver.execute_script("""
                    const btns = document.querySelectorAll('button');
                    for (const b of btns) {
                        const t = (b.textContent||'').trim();
                        if ((t === '확인' || t === '발행' || t === '예약 발행') && b.getBoundingClientRect().width > 0) {
                            b.click();
                            return 'confirm_clicked: ' + t;
                        }
                    }
                    return 'no_confirm';
                """)
                _dlog(f"확인 팝업: {confirm_res}")
                self._sleep(1.2)
            except Exception:
                pass

            # === 제출 결과 상세 진단 ===
            try:
                post_state = self.driver.execute_script(r"""
                    const dialog = document.querySelector('[class*="publish_popup"], [class*="layer_publish"], [class*="PublishPopup"]');
                    const errorMsg = document.querySelector('[class*="error"], [class*="alert"], [class*="warning"]');
                    const toast = document.querySelector('[class*="toast"], [class*="snackbar"]');
                    return {
                        url: location.href,
                        dialog_open: !!dialog,
                        error_text: errorMsg ? (errorMsg.textContent||'').trim().slice(0,200) : '',
                        toast_text: toast ? (toast.textContent||'').trim().slice(0,200) : '',
                        body_snippet: document.body.textContent.slice(0, 200).replace(/\s+/g, ' '),
                    };
                """)
                _dlog(f"제출 후 상태: {post_state}")
                if post_state.get("dialog_open"):
                    _dlog("!!! 발행 다이얼로그가 아직 열려있음 — 제출 실패")
                    return False
                else:
                    _dlog("예약 발행 제출 확인됨 (다이얼로그 닫힘)")
                    return True
            except Exception as _e:
                _dlog(f"제출 후 상태 캡처 실패: {_e}")
                return False

        except Exception as e:
            _dlog(f"예약 발행 실패: {e}")
            import traceback
            _dlog(traceback.format_exc())
            return False

    def _select_category_in_dialog(self, category: str):
        """발행 다이얼로그에서 카테고리 선택.
        해시 클래스 대신 aria/role/data-testid 등 안정적 셀렉터 사용.
        """
        if not category:
            return

        # 카테고리 드롭다운 버튼 찾기 — 해시 클래스 없이 aria/text 기반
        _BTN_JS = r"""
            // aria-label에 카테고리 포함된 버튼
            let btn = document.querySelector('button[aria-label*="카테고리"]');
            if (!btn) {
                // class에 selectbox가 포함된 버튼 중 가시적인 것
                for (const b of document.querySelectorAll('button[class*="selectbox"], button[class*="Selectbox"]')) {
                    const r = b.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) { btn = b; break; }
                }
            }
            if (!btn) {
                // 발행 다이얼로그 내 모든 버튼 중 "카테고리" 텍스트 포함
                for (const b of document.querySelectorAll('button')) {
                    const r = b.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0 && (b.textContent||'').includes('카테고리')) { btn = b; break; }
                }
            }
            if (!btn) return 'no_btn';
            const r = btn.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) return 'btn_hidden';
            if (btn.getAttribute('aria-expanded') === 'true') return 'already_open';
            btn.scrollIntoView({block:'center'});
            btn.focus();
            btn.click();
            ['mousedown','mouseup','click'].forEach(ev => {
                btn.dispatchEvent(new MouseEvent(ev, {
                    bubbles:true, cancelable:true, view:window,
                    clientX: r.left + r.width/2, clientY: r.top + r.height/2,
                }));
            });
            btn.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', bubbles:true}));
            return 'tried';
        """

        def _try_scope(scope_label):
            res = self.driver.execute_script(_BTN_JS)
            _dlog(f"[{scope_label}] 카테고리 드롭다운 시도: {res}")
            return res in ('tried', 'already_open')

        try:
            _dlog(f"카테고리 선택 시도: {category}")
            ok = _try_scope("current")
            if not ok:
                try:
                    self.driver.switch_to.default_content()
                    ok = _try_scope("top")
                except Exception as e:
                    _dlog(f"default_content 전환 실패: {e}")
                if not ok:
                    try: self.driver.switch_to.frame("mainFrame")
                    except Exception: pass
                    return

            # 드롭다운 열릴 때까지 폴링 — aria-expanded 또는 role=option 등장 기준
            for _ in range(15):
                self._sleep(0.2)
                opened = self.driver.execute_script(r"""
                    const exp = document.querySelector('button[aria-expanded="true"]');
                    if (exp) return 'expanded';
                    const opt = document.querySelector('[role="option"], [role="listbox"]');
                    return opt ? 'listbox' : 'wait';
                """)
                if opened in ('expanded', 'listbox'):
                    break

            picked = self.driver.execute_script(r"""
                const target = arguments[0];
                // ㄴ, └, ㄴ류 들여쓰기 prefix와 공백 제거
                const norm = (s) => (s||'').replace(/[ㄴˡ└┗┣\s]+/g, '').trim();
                const targetN = norm(target);
                // React 컨트롤드 input 대응 native setter
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
                    const radio = scope.querySelector('input[type="radio"]') || scope.querySelector('input[type="checkbox"]');
                    if (radio) {
                        setNativeChecked(radio, true);
                        fireEvents(radio);
                    }
                    return true;
                }
                const tried = [];
                // 1순위: li[class*="item"]
                for (const el of document.querySelectorAll('li[class*="item"]')) {
                    const t = (el.textContent||'').trim();
                    tried.push('li:'+t);
                    if (norm(t) === targetN && activate(el))
                        return 'clicked_li_item:' + t;
                }
                // 2순위: label[class*="radio"]
                for (const el of document.querySelectorAll('label[class*="radio"]')) {
                    const t = (el.textContent||'').trim();
                    if (norm(t) === targetN && activate(el))
                        return 'clicked_radio:' + t;
                }
                // 3순위: span[data-testid*="categoryItem"] → 부모 클릭
                for (const el of document.querySelectorAll('span[data-testid*="categoryItem"]')) {
                    const t = (el.textContent||'').trim();
                    if (norm(t) === targetN) {
                        const clickable = el.closest('li') || el.closest('label') || el.parentElement || el;
                        if (activate(clickable)) return 'clicked_testid:' + t;
                    }
                }
                // 4순위: role="option"
                for (const el of document.querySelectorAll('[role="option"]')) {
                    const t = (el.textContent||'').trim();
                    if (norm(t) === targetN && activate(el))
                        return 'clicked_role_option:' + t;
                }
                // 5순위: endsWith fallback (li[class*="item"])
                for (const el of document.querySelectorAll('li[class*="item"]')) {
                    const t = (el.textContent||'').trim();
                    if (t && (t === target || t.endsWith(target) || norm(t).endsWith(targetN)) && activate(el))
                        return 'clicked_endswith_li:' + t;
                }
                const avail = [...document.querySelectorAll('li[class*="item"]')]
                    .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.height < 80; })
                    .map(e => (e.textContent||'').trim())
                    .filter(t => t && t.length < 30);
                return 'not_found|target=' + target + '|targetN=' + targetN + '|available=' + JSON.stringify([...new Set(avail)]);
            """, category)
            _dlog(f"카테고리 '{category}' 선택: {picked}")
            # 검증: 클릭 후 실제 카테고리가 React state에 반영됐는지
            self._sleep(0.5)
            try:
                state = self.driver.execute_script(r"""
                    const btn = document.querySelector('button[aria-label*="카테고리"]');
                    const btnText = btn ? (btn.textContent||'').trim() : '';
                    const checked = Array.from(document.querySelectorAll('input[type="radio"]:checked'))
                        .map(r => (r.closest('label')?.textContent || r.parentElement?.textContent || '').trim().slice(0,30));
                    return {btnText, checked};
                """)
                _dlog(f"카테고리 검증 — btn:{state.get('btnText')!r} / checked:{state.get('checked')}")
                if category not in (state.get('btnText') or '') and not any(category in c for c in (state.get('checked') or [])):
                    _dlog(f"⚠ 카테고리 React state 미반영 — '{category}' 적용 안 됨")
            except Exception as ve:
                _dlog(f"카테고리 검증 실패: {ve}")
            self._sleep(0.2)
        except Exception as e:
            _dlog(f"카테고리 선택 실패: {e}")

    def _publish(self, category: str = "", tags: list = None):
        """즉시 발행 — 1) 발행 버튼 클릭해 다이얼로그 오픈 2) 카테고리/태그 설정 3) 최종 발행"""
        try:
            # 잔여 장소/dim 팝업 제거
            try:
                self.driver.execute_script("""
                    document.querySelectorAll('.se-popup-dim, [class*="popup-dim"], [class*="placesMap"], [class*="place-popup"], [class*="map-popup"]').forEach(el => el.remove());
                """)
            except Exception:
                pass
            self._sleep(0.15)

            # 1차: 발행 버튼 — JS 클릭으로 오버레이 우회
            publish_btn = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, "button.publish_btn__m9KHH, button[class*='publish_btn']"
                ))
            )
            self.driver.execute_script("arguments[0].click();", publish_btn)
            _dlog("1차 발행 버튼 클릭 - 다이얼로그 오픈")
            self._sleep(0.6)

            # 카테고리 선택
            if category:
                self._select_category_in_dialog(category)
                self._sleep(0.25)

            # 태그칸 입력 제거 — 본문 끝 해시태그(#태그)를 네이버가 자동으로 태그로 변환하므로 중복 불필요
            _dlog("태그칸 입력 생략(본문 해시태그 자동 변환 사용)")

            # 2차: 다이얼로그 내부 '발행' 버튼 — data-testid="seOnePublishBtn" 정확 매칭
            final_clicked = self.driver.execute_script("""
                let btn = document.querySelector('button[data-testid="seOnePublishBtn"]')
                       || document.querySelector('button[class*="confirm_btn__"]');
                if (btn) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && !btn.disabled) {
                        btn.click();
                        return 'clicked_testid';
                    }
                }
                return 'not_found';
            """)
            _dlog(f"최종 발행 버튼 클릭: {final_clicked}")
            self._sleep(1.2)

            # 확인 팝업 (있으면 클릭)
            try:
                self.driver.execute_script("""
                    const btns = document.querySelectorAll('button');
                    for (const b of btns) {
                        const t = (b.textContent||'').trim();
                        if ((t === '확인' || t === '발행') && b.getBoundingClientRect().width > 0) {
                            b.click();
                            return;
                        }
                    }
                """)
                self._sleep(0.2)
            except Exception:
                pass

        except Exception as e:
            _dlog(f"발행 실패: {e}")
            print(f"발행 실패: {e}")

    def close(self):
        """브라우저 종료"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                _dlog(f"브라우저 종료 중 오류(무시): {e}")
            self.driver = None
