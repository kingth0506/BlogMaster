# -*- coding: utf-8 -*-
"""댓글·서로이웃 관리 — 로그인된 NaverBlogPoster(드라이버) 재사용.

기능:
  · 서로이웃 받은신청  : list_buddy_requests() 로 목록 조회 → act_on_buddies(선택, accept) 수락/거절
  · 댓글 목록 + 원글삭제: list_comments() 로 어느 글에 무슨 댓글 달렸는지 조회 → delete_post(logno) 원글 삭제
  · 공감 + 자동답글     : like_and_reply_comments() (최대 1000글)

기존 프로그램은 건드리지 않고 이 파일 + main.py 팝업만 사용.
셀렉터가 바뀌면 아래 SEL 만 수정.
"""
import json
import os
import random
import re
import time

ADMIN = "https://admin.blog.naver.com"

SEL = {
    # 서로이웃 받은신청
    "buddy_url":        ADMIN + "/BuddyInviteReceivedManage.naver?blogId={bid}",
    "buddy_frame":      ["allowBothBuddy", "_acceptMultiBuddy", "checkwrap", "name"],
    "buddy_rowcheck":   "input.input_check",          # _checkAll 은 제외
    "buddy_name":       ".name, .nick, strong.ell, a.ell",
    "buddy_both_radio": "input[name='allowBothBuddy']",
    "buddy_accept":     "._acceptMultiBuddy",
    "buddy_reject":     "._denyMultiBuddy",
    # 댓글 목록 (페이지별)
    "cmt_list_url":     ADMIN + "/{bid}/userfilter/commentlist",
    "cmt_page_url":     ADMIN + "/AdminNaverCommentManageView.naver?blogId={bid}&paging.currentPage={page}",
    "cmt_list_frame":   ["_titleContents", "_writerId", "_replyContents"],
    # 원글 삭제 (PC 본문)
    "post_pc_url":      "https://blog.naver.com/{bid}/{logno}",
    "post_overflow":    ".btn_overflow_menu, ._open_overflowmenu",
    "post_delete":      "a._deletePost",
    # 댓글 위젯 (공감/답글) — 모바일
    "post_mobile_url":  "https://m.blog.naver.com/CommentList.naver?blogId={bid}&logNo={logno}",
    "cmt_item":         "li.u_cbox_comment",
    "cmt_content":      ".u_cbox_contents",
    "cmt_like_btn":     "a.u_cbox_btn_recomm",
    "cmt_reply_btn":    "a.u_cbox_btn_reply",
    "cmt_textarea":     "div.u_cbox_text, [contenteditable='true'], textarea",
    "cmt_submit":       "button.u_cbox_btn_upload[class*='reply'], a.u_cbox_btn_upload[class*='reply']",
    "cmt_submit_any":   "button.u_cbox_btn_upload, a.u_cbox_btn_upload",
}


class CommentBuddyManager:
    def __init__(self, poster, log=None, stop_flag=None):
        self.poster = poster
        self.d = poster.driver
        self.bid = poster.blog_id
        self.log = log or (lambda m: None)
        self.stop_flag = stop_flag or getattr(poster, "stop_flag", lambda: False)

    # ── 공통 ──
    def _sleep(self, s):
        self.poster._sleep(s)

    def _go(self, url):
        self.d.get(url)
        self._sleep(2.5)

    def _find(self, css):
        from selenium.webdriver.common.by import By
        return self.d.find_elements(By.CSS_SELECTOR, css)

    def _disp(self, el):
        try:
            return el.is_displayed()
        except Exception:
            return False

    def _click(self, el):
        try:
            self.d.execute_script("arguments[0].click();", el)
            return True
        except Exception:
            try:
                el.click()
                return True
            except Exception:
                return False

    def _accept_alert(self):
        try:
            al = self.d.switch_to.alert
            txt = al.text
            al.accept()
            self._sleep(0.6)
            return txt
        except Exception:
            return None

    def _enter_frame_with(self, markers, timeout=8.0):
        from selenium.webdriver.common.by import By
        d = self.d
        end = time.time() + timeout
        while time.time() < end:
            try:
                if any(m in d.page_source for m in markers):
                    return True
            except Exception:
                pass
            d.switch_to.default_content()
            try:
                frames = d.find_elements(By.TAG_NAME, "iframe")
            except Exception:
                frames = []
            for fr in frames:
                try:
                    d.switch_to.frame(fr)
                    if any(m in d.page_source for m in markers):
                        return True
                    d.switch_to.default_content()
                except Exception:
                    try:
                        d.switch_to.default_content()
                    except Exception:
                        pass
            self._sleep(0.6)
        d.switch_to.default_content()
        return False

    def _visible(self, css):
        for el in self._find(css):
            if self._disp(el):
                try:
                    if el.is_enabled():
                        return el
                except Exception:
                    return el
        return None

    def _type_into(self, el, text):
        try:
            el.click()
        except Exception:
            pass
        self._sleep(0.2)
        try:
            el.send_keys(text)
            if (el.text or el.get_attribute("value") or el.get_attribute("textContent") or ""):
                return True
        except Exception:
            pass
        try:
            editable = (el.get_attribute("contenteditable") in ("true", "")) or el.tag_name.lower() == "div"
            if editable:
                self.d.execute_script(
                    "arguments[0].focus();"
                    "arguments[0].textContent=arguments[1];"
                    "arguments[0].dispatchEvent(new InputEvent('input',{bubbles:true,data:arguments[1]}));"
                    "arguments[0].dispatchEvent(new KeyboardEvent('keyup',{bubbles:true}));",
                    el, text)
            else:
                self.d.execute_script(
                    "arguments[0].value=arguments[1];"
                    "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));"
                    "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
                    el, text)
            return True
        except Exception:
            return False

    # ════════════════════ 서로이웃 받은신청 ════════════════════
    def _buddy_rowchecks(self):
        return [c for c in self._find(SEL["buddy_rowcheck"])
                if "_checkAll" not in (c.get_attribute("class") or "")]

    def list_buddy_requests(self):
        """받은 서로이웃 신청 목록 → [{idx, nick, id, msg, date}]
        테이블 컬럼: 신청한 사람 | 메시지 | 신청일 | 관리."""
        from selenium.webdriver.common.by import By
        self._go(SEL["buddy_url"].format(bid=self.bid))
        self._enter_frame_with(SEL["buddy_frame"], timeout=8)
        out = []
        idx = 0
        for tr in self._find("table tbody tr"):
            # 체크박스 있는 행만 = 실제 신청 (안내/빈행 제외)
            chks = [c for c in tr.find_elements(By.CSS_SELECTOR, "input.input_check")
                    if "_checkAll" not in (c.get_attribute("class") or "")]
            if not chks:
                continue
            tds = tr.find_elements(By.CSS_SELECTOR, "td")

            def _tdt(i):
                return (tds[i].text or "").strip() if i < len(tds) else ""
            # td[0]=체크박스, td[1]=신청한사람(닉\n아이디), td[2]=메시지, td[3]=신청일
            person = _tdt(1)
            parts = [x.strip() for x in person.split("\n") if x.strip()]
            nick = parts[0] if parts else ""
            bid = self._row_applicant_id(tr)
            if not bid and len(parts) >= 2:
                bid = parts[1]
            msg = _tdt(2)
            date = _tdt(3)
            out.append({"idx": idx, "nick": nick or bid or f"신청 {idx+1}",
                        "id": bid, "msg": msg, "date": date})
            idx += 1
        return out

    def _row_applicant_id(self, row):
        """신청 행에서 신청자 아이디 추출 (링크 GoBlog.naver?userId=... )."""
        from selenium.webdriver.common.by import By
        for a in row.find_elements(By.TAG_NAME, "a"):
            h = a.get_attribute("href") or ""
            m = (re.search(r"userId=([A-Za-z0-9_\-]+)", h)
                 or re.search(r"(?:targetBlogId|blogId)=([A-Za-z0-9_\-]+)", h))
            if m and m.group(1) not in (self.bid, "GoBlog"):
                return m.group(1)
        return ""

    def _find_buddy_row_btn(self, applicant_id, css):
        """applicant_id 신청 행의 버튼(css) 찾기. applicant_id 없으면 첫 표시 버튼."""
        from selenium.webdriver.common.by import By
        btns = [b for b in self._find(css) if self._disp(b)]
        if not applicant_id:
            return btns[0] if btns else None
        for b in btns:
            try:
                row = b.find_element(By.XPATH, "./ancestor::tr[1]")
            except Exception:
                continue
            if self._row_applicant_id(row) == applicant_id:
                return b
        return None

    def _confirm_buddy_popup(self, main_handle):
        """수락 시 열리는 BuddyAccept 팝업창에서 '확인' 클릭 후 닫기."""
        from selenium.webdriver.common.by import By
        self._sleep(0.6)
        pops = [h for h in self.d.window_handles if h != main_handle]
        if not pops:
            return bool(self._accept_alert())
        self.d.switch_to.window(pops[-1])
        self._sleep(0.5)
        clicked = False
        for e in self.d.find_elements(By.XPATH,
                "//input[@type='image' or @type='submit' or @type='button']|//a|//button"):
            try:
                if not e.is_displayed():
                    continue
                t = (e.text or e.get_attribute("value") or e.get_attribute("alt") or "").strip()
                if t in ("확인", "등록", "수락", "신청", "완료"):
                    e.click()
                    clicked = True
                    break
            except Exception:
                continue
        self._sleep(1.0)
        self._accept_alert()
        self._sleep(0.4)
        # 팝업 닫고 메인으로
        try:
            if self.d.current_window_handle != main_handle:
                self.d.close()
        except Exception:
            pass
        try:
            self.d.switch_to.window(main_handle)
        except Exception:
            pass
        self._sleep(0.6)
        return clicked

    def _select_checkbox(self, c):
        """체크박스 실제 선택 (네이티브 클릭 우선, 실패 시 JS+이벤트)."""
        try:
            if c.is_selected():
                return True
        except Exception:
            pass
        try:
            c.click()
            if c.is_selected():
                return True
        except Exception:
            pass
        try:
            self.d.execute_script(
                "arguments[0].checked=true;"
                "arguments[0].dispatchEvent(new Event('click',{bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", c)
            return c.is_selected()
        except Exception:
            return False

    def act_on_buddies(self, applicant_ids, accept=True):
        """선택한 신청자들을 체크박스로 일괄 수락/거절 (한 번에 처리).
        applicant_ids 비어있으면 전체.
        ⚠ 수락 팝업(window.open)은 창이 화면 밖이면 안 열려서, 작업 동안만 창을 화면으로."""
        from selenium.webdriver.common.by import By
        # 창 화면 안으로 복귀 (팝업 허용)
        try:
            self.d.set_window_position(0, 0)
            self.d.set_window_size(1100, 800)
            self._sleep(0.3)
        except Exception:
            pass
        self.d.switch_to.default_content()
        main = self.d.current_window_handle
        self._go(SEL["buddy_url"].format(bid=self.bid))
        self._enter_frame_with(SEL["buddy_frame"], timeout=8)
        rowchecks = self._buddy_rowchecks()
        if not rowchecks:
            self.log("  · 받은 신청 없음")
            return 0
        want = set(x for x in (applicant_ids or []) if x)
        selected = 0
        for c in rowchecks:
            try:
                row = c.find_element(By.XPATH, "./ancestor::tr[1]")
            except Exception:
                row = None
            rid = self._row_applicant_id(row) if row is not None else ""
            if (not want) or (rid and rid in want):
                if self._select_checkbox(c):
                    selected += 1
        if selected == 0:
            self.log("  ⚠ 선택된 신청 없음")
            return 0
        if accept:
            for r in self._find(SEL["buddy_both_radio"]):
                try:
                    r.click()
                except Exception:
                    self._click(r)
                break
        self._sleep(0.4)
        btn = self._visible(SEL["buddy_accept"] if accept else SEL["buddy_reject"])
        if btn is None:
            self.log("  ⚠ 일괄 수락/거절 버튼 못찾음")
            return 0
        self.log(f"  · {selected}건 선택 → {'수락' if accept else '거절'}")
        try:
            btn.click()
        except Exception:
            self._click(btn)
        self._sleep(1.5)
        # 팝업(BothBuddyMultiAcceptForm) 확인 + 알림 처리
        self._confirm_buddy_popup(main)
        self._accept_alert()
        self._sleep(0.8)
        # 작업 끝 → 창 다시 숨김
        try:
            self.d.set_window_position(-32000, -32000)
        except Exception:
            pass
        self.log(f"  ✓ {selected}건 {'수락' if accept else '거절'} 완료")
        return selected

    # ════════════════════ 댓글 목록 + 원글 삭제 ════════════════════
    def _http_session(self):
        import requests
        s = requests.Session()
        for c in self.d.get_cookies():
            try:
                s.cookies.set(c["name"], c["value"], domain=c.get("domain"))
            except Exception:
                pass
        s.headers["User-Agent"] = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")
        return s

    def filter_deleted(self, rows, drop=True):
        """각 글이 실제 존재하는지 확인 → 삭제/없는 글 표시(또는 제거).
        삭제·없는 글: HTTP 404 또는 빈 페이지 / 삭제 안내문구."""
        s = self._http_session()
        cache = {}
        out = []
        dn = 0
        for r in rows:
            lg = r.get("logno")
            alive = True
            if lg:
                if lg not in cache:
                    try:
                        resp = s.get(f"https://m.blog.naver.com/{self.bid}/{lg}", timeout=8)
                        body = resp.text or ""
                        cache[lg] = (resp.status_code == 200 and len(body) > 3000
                                     and "삭제되었거나" not in body and "존재하지 않" not in body)
                    except Exception:
                        cache[lg] = True  # 확인 실패 시 살아있다고 간주(안전)
                alive = cache[lg]
            r["deleted"] = not alive
            if not alive:
                dn += 1
            if alive or not drop:
                out.append(r)
        if dn:
            self.log(f"  · 삭제된 글 {dn}건 제외")
        return out

    def _scrape_comment_page(self):
        """현재 DOM(한 페이지)의 댓글 행들을 [{logno,title,writer,content}] 로."""
        from selenium.webdriver.common.by import By
        rows = []
        for c in self._find("._replyContents"):
            try:
                row = c.find_element(By.XPATH,
                    "./ancestor::*[self::li or self::tr or self::div][.//*[contains(@class,'_titleContents')]][1]")
            except Exception:
                row = None
            title, writer, logno, content = "", "", "", ""
            # 전체 내용 — 숨겨진 _replyRealContents 의 textContent (없으면 잘린 표시본)
            try:
                real = c.find_element(By.XPATH,
                    "following-sibling::*[contains(@class,'_replyRealContents')]")
                content = (real.get_attribute("textContent") or "").strip()
            except Exception:
                pass
            if not content and row is not None:
                try:
                    content = (row.find_element(By.CSS_SELECTOR, "._replyRealContents")
                               .get_attribute("textContent") or "").strip()
                except Exception:
                    pass
            if not content:
                content = (c.text or "").strip()
            if row is not None:
                try:
                    title = row.find_element(By.CSS_SELECTOR, "._titleContents").text.strip()
                except Exception:
                    pass
                for wsel in ("._writerNickname", "._writerId", ".nickname"):
                    try:
                        w = row.find_element(By.CSS_SELECTOR, wsel).text.strip()
                        if w:
                            writer = w
                            break
                    except Exception:
                        pass
                for a in row.find_elements(By.TAG_NAME, "a"):
                    h = a.get_attribute("href") or ""
                    m = re.search(r"blog\.naver\.com/%s/(\d+)" % re.escape(self.bid), h)
                    if m:
                        logno = m.group(1)
                        break
            rows.append({
                "logno": logno,
                "title": re.sub(r"^\[글\]\s*", "", title),
                "writer": writer,
                "content": content,
            })
        return rows

    def list_comments(self, limit=2000, check_deleted=False, exclude_engaged=False):
        """받은 댓글 전체(모든 페이지) → [{logno,title,writer,content}].
        check_deleted=True: 삭제된 글 댓글 제외 / exclude_engaged=True: 내가 공감·답글 단 댓글 제외."""
        all_rows = []
        for page in range(1, 100):  # 안전 상한 (페이지당 20개)
            if self.stop_flag():
                break
            # d.get은 로드 완료까지 블록하므로 고정 2.5초 대기 제거 → enter_frame이 필요한 만큼만 폴링
            self.d.get(SEL["cmt_page_url"].format(bid=self.bid, page=page))
            self._enter_frame_with(SEL["cmt_list_frame"], timeout=8)
            page_rows = self._scrape_comment_page()
            if not page_rows:
                break
            all_rows.extend(page_rows)
            self.log(f"  · 댓글 {len(all_rows)}개 수집 (page {page})")
            if len(all_rows) >= limit or len(page_rows) < 20:
                break
        all_rows = all_rows[:limit]
        if exclude_engaged:
            seen = self._load_seen()
            before = len(all_rows)
            all_rows = [r for r in all_rows
                        if self._cmt_key(r.get("logno", ""), r.get("content", "")) not in seen]
            if before - len(all_rows) > 0:
                self.log(f"  · 내가 공감/답글 단 댓글 {before - len(all_rows)}개 제외")
        if check_deleted:
            all_rows = self.filter_deleted(all_rows, drop=True)
        return all_rows

    def delete_post(self, logno):
        """원글 삭제 — PC 본문에서 '삭제' 클릭 후 확인."""
        from selenium.webdriver.common.by import By
        self.d.switch_to.default_content()
        self._go(SEL["post_pc_url"].format(bid=self.bid, logno=logno))
        # mainFrame 진입
        for fr in self.d.find_elements(By.TAG_NAME, "iframe"):
            if (fr.get_attribute("id") or "") == "mainFrame":
                self.d.switch_to.frame(fr)
                break
        self._sleep(1.2)
        # 본문 기타기능(더보기) 메뉴 열기
        ov = self._visible(SEL["post_overflow"])
        if ov is not None:
            self._click(ov)
            self._sleep(0.8)
        # 삭제 클릭
        dele = None
        for e in self._find(SEL["post_delete"]):
            dele = e
            break
        if dele is None:
            self.log(f"  ⚠ [{logno}] 삭제 버튼 못찾음")
            return False
        self._click(dele)
        self._sleep(1.0)
        # 확인 — JS alert 또는 레이어 확인 버튼
        if self._accept_alert() is None:
            # 레이어 팝업의 '삭제/확인' 버튼
            for b in self.d.find_elements(By.XPATH,
                    "//a[normalize-space()='삭제' or normalize-space()='확인']"
                    "|//button[normalize-space()='삭제' or normalize-space()='확인']"):
                if self._disp(b):
                    self._click(b)
                    self._sleep(0.6)
                    self._accept_alert()
                    break
        self._sleep(1.2)
        self.log(f"  ✓ [{logno}] 원글 삭제 시도 완료")
        return True

    def delete_posts(self, lognos):
        n = 0
        for lg in lognos:
            if self.stop_flag():
                break
            try:
                if self.delete_post(lg):
                    n += 1
            except Exception as e:
                self.log(f"  · [{lg}] 삭제 실패: {str(e)[:40]}")
        return n

    # ════════════════════ 공감 + 자동답글 ════════════════════
    @staticmethod
    def _cmt_key(logno, content):
        """저장/필터 공용 키 — 공백 제거 + 앞 50자 (출처 달라도 매칭되게)."""
        return f"{logno}:{re.sub(r'\\s+', '', content or '')[:50]}"

    def _seen_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "engaged_comments.json")

    def _load_seen(self):
        try:
            from app_paths import safe_load_json as _slj
            return set((_slj(self._seen_path(), default={}, max_mb=20) or {}).get(self.bid, []))
        except Exception:
            return set()

    def _save_seen(self, seen):
        try:
            from app_paths import safe_load_json as _slj
            p = self._seen_path()
            data = _slj(p, default={}, max_mb=20) or {}
            data[self.bid] = sorted(seen)[-5000:]
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def _recent_comment_lognos(self):
        # 전체 페이지 댓글에서 글 logNo 수집 (중복 제거)
        rows = self.list_comments(limit=2000)
        return list(dict.fromkeys(r["logno"] for r in rows if r.get("logno")))

    def _write_reply(self, phrase):
        from selenium.webdriver.common.by import By
        sb = self._visible(SEL["cmt_submit"]) or self._visible(SEL["cmt_submit_any"])
        if sb is None:
            return False
        try:
            box = sb.find_element(By.XPATH,
                "./ancestor::*[self::div or self::form]"
                "[.//textarea or .//*[@contenteditable='true' or @contenteditable=''] ][1]")
        except Exception:
            box = None
        ta = None
        if box is not None:
            for t in box.find_elements(By.CSS_SELECTOR,
                    "div.u_cbox_text, [contenteditable='true'], [contenteditable=''], textarea"):
                if self._disp(t):
                    ta = t
                    break
        if ta is None:
            cands = [e for e in self._find(SEL["cmt_textarea"]) if self._disp(e)]
            ta = cands[-1] if cands else None
        if ta is None:
            return False
        if not self._type_into(ta, phrase):
            return False
        self._sleep(0.6)
        sb = self._visible(SEL["cmt_submit"]) or self._visible(SEL["cmt_submit_any"]) or sb
        self._click(sb)
        self._sleep(0.9)
        self._accept_alert()
        return True

    def like_and_reply_comments(self, phrases, do_like=True, do_reply=True, max_posts=1000):
        self.log("▶ 댓글 공감 + 자동답글 시작")
        lognos = self._recent_comment_lognos()
        if not lognos:
            self.log("  · 최근 댓글이 달린 글 없음")
            return 0
        self.log(f"  · 댓글 달린 글 {len(lognos)}개 → 처리(최대 {max_posts})")
        seen = self._load_seen()
        done = 0
        for logno in lognos[:max_posts]:
            if self.stop_flag():
                break
            done += self._engage_post(logno, phrases, do_like, do_reply, seen)
        self._save_seen(seen)
        self.log(f"  ✓ 댓글 처리 완료 (답글 {done}건)")
        return done

    def _engage_post(self, logno, phrases, do_like, do_reply, seen):
        from selenium.webdriver.common.by import By
        self.d.switch_to.default_content()
        self.d.get(SEL["post_mobile_url"].format(bid=self.bid, logno=logno))
        # 고정 대기(2.5+2.0초) 제거 → 댓글 목록이 뜨면 즉시 진행 (속도↑)
        items = []
        for _ in range(16):
            self._sleep(0.2)
            try:
                self.d.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            except Exception:
                pass
            items = self._find(SEL["cmt_item"])
            if items:
                break
        if not items:
            return 0
        cnt = 0
        for li in items:
            if self.stop_flag():
                break
            try:
                content = ""
                try:
                    content = li.find_element(By.CSS_SELECTOR, SEL["cmt_content"]).text.strip()
                except Exception:
                    pass
                key = self._cmt_key(logno, content)
                engaged_now = False

                if do_like:
                    likes = li.find_elements(By.CSS_SELECTOR, SEL["cmt_like_btn"]) or \
                            li.find_elements(By.XPATH, ".//a[contains(.,'공감') or contains(.,'추천')]")
                    for b in likes:
                        if " on" not in (" " + (b.get_attribute("class") or "")):
                            self._click(b)
                            self._sleep(0.4)
                            engaged_now = True
                            break

                if do_reply and phrases and key not in seen:
                    rb = li.find_elements(By.CSS_SELECTOR, SEL["cmt_reply_btn"]) or \
                         li.find_elements(By.XPATH, ".//a[contains(.,'답글')]")
                    if rb:
                        self._click(rb[0])
                        self._sleep(0.6)
                        phrase = random.choice(phrases)
                        if self._write_reply(phrase):
                            cnt += 1
                            engaged_now = True
                            self.log(f"  ✓ [{logno}] 답글: {phrase[:18]}…")

                # 공감/답글 중 하나라도 했으면 기록 (다음에 목록에서 제외)
                if engaged_now:
                    seen.add(key)
            except Exception as e:
                self.log(f"  · 댓글 처리 실패: {str(e)[:40]}")
                continue
        return cnt


def load_reply_phrases():
    fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reply_phrases.json")
    try:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            return [str(x) for x in data if str(x).strip()]
    except Exception:
        pass
    return ["방문 감사합니다! 좋은 하루 되세요 :)", "댓글 감사해요~ 자주 들러주세요!"]
