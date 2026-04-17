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
                 window_x: int = 50, window_y: int = 50):
        self.naver_id = naver_id
        self.naver_pw = naver_pw
        self.blog_id = blog_id
        self.driver = None
        self.headless = headless
        self.window_x = window_x
        self.window_y = window_y

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

        def _build_opts():
            o = uc.ChromeOptions()
            if self.headless:
                o.add_argument("--headless=new")
            o.add_argument("--window-size=900,700")
            o.add_argument("--disable-gpu")
            o.add_argument(f"--user-data-dir={profile_dir}")
            # 비밀번호 저장 팝업 차단
            o.add_experimental_option("prefs", {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.password_manager_leak_detection": False,
            })
            o.add_argument("--disable-features=PasswordManagerOnboarding,AutofillServerCommunication")
            return o

        # Chrome 버전 자동 감지 (version_main 고정 시 미스매치 발생)
        try:
            self.driver = uc.Chrome(options=_build_opts(), use_subprocess=True)
        except Exception as _e:
            _dlog(f"auto 버전 실패, 147 재시도: {_e}")
            self.driver = uc.Chrome(options=_build_opts(), use_subprocess=True, version_main=147)
        try:
            self.driver.set_window_size(900, 700)
            self.driver.set_window_position(self.window_x, self.window_y)
        except Exception:
            pass

        # OS 파일 다이얼로그 전역 차단 (CDP로 모든 페이지에 자동 주입)
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    const origClick = HTMLInputElement.prototype.click;
                    HTMLInputElement.prototype.click = function() {
                        if (this.type === 'file' && !this.hasAttribute('__allow_click')) {
                            return;
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
            time.sleep(0.8)
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
            time.sleep(0.4)

            # ID/PW JS로 직접 값 설정 (React 호환 setter)
            self.driver.execute_script(
                "const idEl=document.getElementById('id'); const pwEl=document.getElementById('pw');"
                "const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
                "s.call(idEl, arguments[0]); idEl.dispatchEvent(new Event('input',{bubbles:true}));"
                "s.call(pwEl, arguments[1]); pwEl.dispatchEvent(new Event('input',{bubbles:true}));",
                self.naver_id, self.naver_pw
            )
            _dlog(f"ID/PW 입력 완료 (id={self.naver_id})")
            time.sleep(0.3)

            # 로그인 버튼 클릭
            login_btn = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "log.login"))
            )
            login_btn.click()
            _dlog("로그인 버튼 클릭")
            time.sleep(1.5)
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

            # 캡챠 등의 경우 대기
            _dlog("로그인 미완료 - 캡챠/추가인증 대기 (60초)")
            print("로그인 확인 대기중... (캡챠가 있으면 수동으로 해결해주세요)")
            try:
                WebDriverWait(self.driver, 60).until(
                    lambda d: "nid.naver.com" not in d.current_url
                )
                _dlog("추가 인증 후 로그인 성공")
                return True
            except Exception:
                _dlog("로그인 확인 시간 초과")
                return False

        except Exception as e:
            print(f"로그인 실패: {e}")
            return False

    def _handle_device_confirm(self):
        """'새로운 기기에서 로그인' 페이지(deviceConfirm)면 '등록' 버튼 클릭"""
        try:
            time.sleep(0.2)
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
            time.sleep(0.35)
        except Exception as e:
            _dlog(f"deviceConfirm 처리 실패: {e}")

    def _skip_passkey_bridge(self):
        """패스키 설정 안내 페이지가 뜨면 '30일 동안 안 보기' 체크 후 스킵"""
        try:
            time.sleep(0.2)
            if "passkey" not in self.driver.current_url:
                return
            _dlog("패스키 안내 페이지 감지 - 스킵 처리")
            # '30일 동안 안 보기' 체크박스 클릭
            try:
                dont_show = self.driver.find_element(
                    By.XPATH, "//*[contains(text(),'30일 동안 안 보기') or contains(text(),'30일동안 안 보기')]"
                )
                dont_show.click()
                time.sleep(0.25)
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
                    time.sleep(0.2)
                    _dlog(f"스킵 버튼 클릭: {xp}")
                    return
                except Exception:
                    continue
            # 대체: 그냥 네이버 메인으로 이동
            self.driver.get("https://www.naver.com")
            time.sleep(0.2)
            _dlog("패스키 페이지 우회 - 메인으로 이동")
        except Exception as e:
            _dlog(f"패스키 스킵 실패: {e}")

    def write_post(self, title: str, body: str, tags: list[str],
                   image_paths: list[str] = None, category: str = "",
                   schedule_time: str = None,
                   place_name: str = "", place_address: str = "") -> bool:
        """블로그 글 작성 및 발행"""
        try:
            _dlog(f"=== write_post 시작: {title[:30]} === (이미지 {len(image_paths or [])}장, 본문 마커 {body.count('[이미지]')}개)")
            # 글쓰기 페이지로 직접 이동
            write_url = self.BLOG_WRITE_URL.format(blog_id=self.blog_id)
            self.driver.get(write_url)
            _dlog(f"URL 이동 완료: {self.driver.current_url}")
            time.sleep(0.35)

            # JS alert 먼저 처리
            try:
                alert = self.driver.switch_to.alert
                _dlog(f"JS alert 감지: {alert.text}")
                alert.dismiss()
                time.sleep(0.2)
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
            time.sleep(0.35)

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
                    time.sleep(0.15)
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
                time.sleep(0.25)
            except Exception:
                pass

            _dlog("제목 입력 시작")
            self._input_title(title)
            _dlog("제목 입력 완료")
            time.sleep(0.2)

            _dlog("본문 입력 시작")
            self._input_body(body, image_paths)
            _dlog("본문 입력 완료")
            time.sleep(0.2)

            if place_name:
                _dlog(f"장소 삽입 시작: {place_name}")
                self._insert_place(place_name, place_address)
                _dlog("장소 삽입 완료")
                time.sleep(0.2)

            if schedule_time:
                _dlog("예약 발행")
                self._schedule_publish(schedule_time, category=category, tags=tags)
            else:
                _dlog("즉시 발행")
                self._publish(category=category, tags=tags)

            time.sleep(1.2)
            _dlog("=== write_post 성공 ===")
            return True

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

    def _input_title(self, title: str):
        """제목 입력 — SmartEditor ONE은 contenteditable이라 클릭→ActionChains로 키 전송"""
        title_area = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".se-title-text"))
        )
        # 클릭해서 포커스 — 에디터가 내부 편집 노드로 포커스 이관
        ActionChains(self.driver).move_to_element(title_area).click().perform()
        time.sleep(0.25)
        self._ac_type(title)

    def _input_body(self, body: str, image_paths: list[str] = None):
        """본문 입력 — 클릭으로 포커스 후 ActionChains로 키 전송"""
        body_area = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".se-component.se-text .se-text-paragraph, .se-main-container"))
        )
        ActionChains(self.driver).move_to_element(body_area).click().perform()
        time.sleep(0.25)

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
        time.sleep(0.15)

        # 본문 영역 재포커스
        try:
            ActionChains(self.driver).move_to_element(body_area).click().perform()
            time.sleep(0.2)
        except Exception:
            pass

        # [이미지] 태그를 기준으로 본문 분리
        parts = body.split("[이미지]")
        img_idx = 0

        for i, part in enumerate(parts):
            # 파트별로 한 번에 타이핑 (줄바꿈은 \n 그대로 전송)
            text_block = part.strip()
            if text_block:
                # [소제목] 태그 제거
                cleaned_lines = []
                for line in text_block.split("\n"):
                    s = line.strip()
                    if s.startswith("[소제목]"):
                        s = s.replace("[소제목]", "").strip()
                    cleaned_lines.append(s)
                combined = "\n".join(cleaned_lines)
                # ActionChains로 전체 블록 전송 (줄바꿈 포함)
                ActionChains(self.driver).send_keys(combined).perform()
                self._ac_key(Keys.ENTER)

            # 이미지 삽입 (마지막 파트 뒤에는 삽입하지 않음)
            if i < len(parts) - 1 and image_paths and img_idx < len(image_paths):
                self._insert_image(image_paths[img_idx])
                img_idx += 1
                time.sleep(0.2)
                # 이미지 캡션에서 빠져나와 문서 끝 본문 영역으로 커서 이동
                try:
                    # Escape로 캡션/이미지 편집 모드 종료
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    time.sleep(0.2)
                    # JS로 문서 마지막 본문 문단 끝에 포커스 설정
                    self.driver.execute_script("""
                        const paragraphs = document.querySelectorAll('.se-main-container .se-text-paragraph:not(.se-caption)');
                        // 캡션이 아닌 마지막 본문 문단 찾기
                        let target = null;
                        for (let i = paragraphs.length - 1; i >= 0; i--) {
                            const p = paragraphs[i];
                            // 이미지 컴포넌트 내부가 아닌 것만
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
                    time.sleep(0.15)
                    # 새 줄 시작
                    ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                    time.sleep(0.2)
                except Exception as e:
                    _dlog(f"커서 이동 실패: {e}")

    def _insert_place(self, place_name: str, place_address: str = ""):
        """툴바의 '장소' 버튼 클릭해서 장소 카드 삽입"""
        try:
            # 장소 버튼 클릭
            place_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".se-map-toolbar-button, button[class*='map-toolbar-button']"))
            )
            place_btn.click()
            time.sleep(0.6)

            # 검색 입력창에 업체명 입력
            search_input = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".se-map-search-input, input[class*='map-search'], input[placeholder*='장소']"))
            )
            search_input.click()
            search_input.clear()
            ActionChains(self.driver).send_keys(place_name).perform()
            time.sleep(0.15)
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            time.sleep(0.35)

            # 검색 결과의 "+ 추가" 버튼 클릭 — 장소 팝업 내에서 '추가' 텍스트 버튼 찾기
            time.sleep(0.6)
            try:
                clicked = self.driver.execute_script("""
                    const placePopup = document.querySelector('[class*="placesMap"], [class*="place-popup"], [class*="map-popup"]');
                    const scope = placePopup || document;
                    const btns = scope.querySelectorAll('button');
                    for (const b of btns) {
                        const txt = (b.textContent||'').trim();
                        if (txt === '추가' || txt === '+ 추가' || txt.startsWith('+ 추가')) {
                            b.click();
                            return 'clicked:' + txt;
                        }
                    }
                    return 'no_add';
                """)
                _dlog(f"장소 '+ 추가' 클릭: {clicked}")
                time.sleep(0.2)
            except Exception as e:
                _dlog(f"추가 버튼 클릭 실패: {e}")

            # 최종 확인 버튼 (지도 + 확인 다이얼로그)
            time.sleep(0.2)
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
                time.sleep(0.35)
            except Exception as e:
                _dlog(f"장소 확인 버튼 클릭 실패: {e}")

        except Exception as e:
            _dlog(f"장소 삽입 실패: {e}")

    def _insert_image(self, image_path: str):
        """이미지 삽입 — 사진 버튼 클릭으로 input 생성 후 send_keys (OS 다이얼로그는 JS 차단됨)"""
        try:
            abs_path = os.path.abspath(image_path)
            _dlog(f"이미지 삽입 시도: {abs_path}")

            # 사진 버튼 클릭 (OS 다이얼로그는 주입된 스크립트로 차단되지만 input 생성은 됨)
            try:
                img_btn = self.driver.find_element(
                    By.CSS_SELECTOR, ".se-image-toolbar-button, button[class*='image-toolbar-button']"
                )
                self.driver.execute_script("arguments[0].click();", img_btn)
                _dlog("사진 버튼 클릭")
            except Exception as e:
                _dlog(f"사진 버튼 클릭 실패: {e}")
            time.sleep(0.25)

            # 파일 input 찾아서 경로 전송
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            _dlog(f"file input 개수: {len(file_inputs)}")
            sent = False
            for fi in file_inputs:
                try:
                    fi.send_keys(abs_path)
                    sent = True
                    _dlog(f"파일 경로 전송 성공")
                    break
                except Exception:
                    continue
            if not sent:
                raise Exception("file input에 경로 전송 실패")
            time.sleep(0.35)

            # 업로드 완료 대기
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".se-image-resource, .se-module-image, .se-component.se-image"))
            )
            _dlog("이미지 업로드 완료")
            time.sleep(0.25)

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
            time.sleep(0.35)

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
                    time.sleep(0.2)
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
                        time.sleep(0.15)
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
                time.sleep(0.2)
            except Exception:
                pass
        except Exception as e:
            _dlog(f"임시저장 삭제 실패: {e}")

    def _input_tags(self, tags: list[str]):
        """태그 입력"""
        try:
            tag_input = self.driver.find_element(
                By.CSS_SELECTOR, ".se-tag-input input, #post-tag-input"
            )
            for tag in tags:
                tag_input.send_keys(tag)
                tag_input.send_keys(Keys.ENTER)
                time.sleep(0.2)
        except Exception as e:
            _dlog(f"태그 입력 실패: {e}")

    def _schedule_publish(self, schedule_time: str, category: str = "", tags: list = None):
        """예약 발행 — schedule_time 형식: 'YYYY-MM-DD HH:MM'"""
        try:
            # 잔여 팝업 제거
            try:
                self.driver.execute_script("""
                    document.querySelectorAll('.se-popup-dim, [class*="popup-dim"], [class*="placesMap"], [class*="place-popup"]').forEach(el => el.remove());
                """)
            except Exception:
                pass
            time.sleep(0.15)

            # 발행 다이얼로그 열기
            publish_btn = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, "button.publish_btn__m9KHH, button[class*='publish_btn']"
                ))
            )
            self.driver.execute_script("arguments[0].click();", publish_btn)
            _dlog("발행 다이얼로그 오픈")
            time.sleep(0.6)

            # 카테고리
            if category:
                self._select_category_in_dialog(category)
                time.sleep(0.15)

            # 태그
            if tags:
                try:
                    tag_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR, "input[placeholder*='태그'], input[id*='tag'], .tag_input__Bw7SQ input"
                        ))
                    )
                    tag_input.click()
                    for tag in tags:
                        tag_input.send_keys(tag)
                        tag_input.send_keys(Keys.ENTER)
                        time.sleep(0.15)
                    _dlog(f"태그 {len(tags)}개 입력")
                except Exception as e:
                    _dlog(f"태그 입력 실패: {e}")

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
                time.sleep(0.35)
            except Exception as e:
                _dlog(f"예약 라디오 선택 실패: {e}")

            # 날짜/시간 파싱
            date_str, time_str = schedule_time.split(" ")
            year, month, day = date_str.split("-")
            hour, minute = time_str.split(":")
            # 네이버는 10분 단위 예약만 허용 — 10분 단위로 반올림
            minute_int = int(minute)
            minute_int = (minute_int // 10) * 10
            minute = f"{minute_int:02d}"

            # 날짜 input[class*="input_date"] — readonly라 value 직접 설정
            try:
                date_value = f"{year}. {month}. {day}"
                set_date = self.driver.execute_script("""
                    const input = document.querySelector('input[class*="input_date"]');
                    if (!input) return 'no_input';
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(input, arguments[0]);
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                    input.dispatchEvent(new Event('change', {bubbles: true}));
                    return 'set:' + input.value;
                """, date_value)
                _dlog(f"예약 날짜 설정: {set_date}")
            except Exception as e:
                _dlog(f"예약 날짜 설정 실패: {e}")

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
                time.sleep(0.25)
            except Exception as e:
                _dlog(f"예약 시간 설정 실패: {e}")

            # 최종 발행 버튼 — data-testid="seOnePublishBtn" 또는 class="confirm_btn__*" 정확 매칭
            final_clicked = self.driver.execute_script("""
                // 1순위: data-testid로 정확 매칭 (다이얼로그 내부 제출 버튼)
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
            _dlog(f"예약 발행 최종 클릭: {final_clicked}")
            time.sleep(2)

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
                time.sleep(1.2)
            except Exception:
                pass

            # 제출 성공 여부 검증: 다이얼로그 사라졌는지 확인
            try:
                still_open = self.driver.execute_script("""
                    return !!document.querySelector('[class*="publish_popup"], [class*="layer_publish"], [class*="PublishPopup"]');
                """)
                if still_open:
                    _dlog("!!! 발행 다이얼로그가 아직 열려있음 — 제출 실패 가능성")
                else:
                    _dlog("예약 발행 제출 확인됨 (다이얼로그 닫힘)")
            except Exception:
                pass

        except Exception as e:
            _dlog(f"예약 발행 실패: {e}")
            import traceback
            _dlog(traceback.format_exc())

    def _select_category_in_dialog(self, category: str):
        """발행 다이얼로그에서 카테고리 선택 — 확인된 실제 DOM:
        버튼: button.selectbox_button__jb1Dt[aria-label='카테고리 목록 버튼']
        항목: label.radio_label__mB6ia[role='button'] > span[data-testid^='categoryItemText']
        """
        if not category:
            return

        def _try_scope(scope_label):
            opened = self.driver.execute_script("""
                // 카테고리 드롭다운 버튼 찾기
                const btns = document.querySelectorAll('button[aria-label*="카테고리"], button[data-click-area*="category"], button.selectbox_button__jb1Dt');
                for (const b of btns) {
                    const rect = b.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        // 이미 열려있으면 (aria-expanded='true') 클릭 안 함
                        if (b.getAttribute('aria-expanded') !== 'true') {
                            b.click();
                        }
                        return 'opened';
                    }
                }
                return 'not_found';
            """)
            _dlog(f"[{scope_label}] 카테고리 드롭다운: {opened}")
            return opened == 'opened'

        try:
            _dlog(f"카테고리 선택 시도: {category}")

            # 현재 프레임에서 먼저 시도
            opened = _try_scope("current")
            if not opened:
                # top 레벨 시도
                try:
                    self.driver.switch_to.default_content()
                    opened = _try_scope("top")
                except Exception as e:
                    _dlog(f"default_content 전환 실패: {e}")
                if not opened:
                    # mainFrame 복귀
                    try:
                        self.driver.switch_to.frame("mainFrame")
                    except Exception:
                        pass
                    return
            time.sleep(0.35)

            # 드롭다운 항목 클릭 — label[role="button"] + span.text__sraQE
            picked = self.driver.execute_script("""
                const target = arguments[0];
                // 드롭다운 내 항목: label.radio_label__* 또는 span.text__sraQE 안의 text
                const items = document.querySelectorAll('label[class*="radio_label"], label[role="button"], span[data-testid^="categoryItemText"]');
                for (const el of items) {
                    const t = (el.textContent||'').trim();
                    const rect = el.getBoundingClientRect();
                    if (t === target && rect.width > 0 && rect.height > 0) {
                        // span이면 부모 label 클릭
                        const clickable = el.closest('label') || el;
                        clickable.click();
                        return 'clicked:' + t;
                    }
                }
                return 'not_found';
            """, category)
            _dlog(f"카테고리 '{category}' 선택: {picked}")
            time.sleep(0.25)
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
            time.sleep(0.15)

            # 1차: 발행 버튼 — JS 클릭으로 오버레이 우회
            publish_btn = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, "button.publish_btn__m9KHH, button[class*='publish_btn']"
                ))
            )
            self.driver.execute_script("arguments[0].click();", publish_btn)
            _dlog("1차 발행 버튼 클릭 - 다이얼로그 오픈")
            time.sleep(0.6)

            # 카테고리 선택
            if category:
                self._select_category_in_dialog(category)
                time.sleep(0.25)

            # 태그 입력 (발행 다이얼로그 내)
            if tags:
                try:
                    tag_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR, "input[placeholder*='태그'], input[id*='tag'], .tag_input__Bw7SQ input"
                        ))
                    )
                    tag_input.click()
                    for tag in tags:
                        tag_input.send_keys(tag)
                        tag_input.send_keys(Keys.ENTER)
                        time.sleep(0.15)
                    _dlog(f"태그 {len(tags)}개 입력 완료")
                    time.sleep(0.15)
                except Exception as e:
                    _dlog(f"태그 입력 실패: {e}")

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
            time.sleep(1.2)

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
                time.sleep(0.2)
            except Exception:
                pass

        except Exception as e:
            _dlog(f"발행 실패: {e}")
            print(f"발행 실패: {e}")

    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None
