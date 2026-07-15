# -*- coding: utf-8 -*-
"""환경설정 다이얼로그 (PySide6) — 아이디 3개 지원"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QButtonGroup, QCheckBox, QFrame, QMessageBox,
    QScrollArea, QWidget, QTabWidget, QTextEdit, QComboBox, QListWidget
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, Slot, QMetaObject, QTimer
from PySide6.QtWidgets import QApplication
from config import load_config, save_config, get_taken_naver_ids


class SettingsDialog(QDialog):
    def __init__(self, parent=None, is_admin=False, app_user="admin"):
        super().__init__(parent)
        self.setWindowTitle("환경설정")
        self.setMinimumWidth(550)
        self.resize(560, 640)
        # 라이트 팔레트 강제 (Windows 다크모드 대응)
        self.setStyleSheet(
            "QDialog { background: #ffffff; color: #1e293b; }"
            "QWidget { background: #ffffff; color: #1e293b; }"
            "QLabel { background: transparent; color: #1e293b; }"
            "QLineEdit { background: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px; }"
            "QTabBar::tab { background: #f1f5f9; color: #1e293b; padding: 6px 12px; }"
            "QTabBar::tab:selected { background: #ffffff; color: #1e293b; font-weight: bold; }"
            "QScrollArea { background: #ffffff; border: none; }"
            "QRadioButton { background: transparent; color: #1e293b; }"
        )
        self.cfg = load_config()
        self.is_admin = is_admin
        self.app_user = app_user
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 8)

        # ── 상단 탭 ──
        self.top_tabs = QTabWidget()
        self.top_tabs.setStyleSheet(
            "QTabBar::tab { background: #f1f5f9; color: #1e293b; padding: 8px 22px; font-size: 12px; }"
            "QTabBar::tab:selected { background: #ffffff; color: #4a6cf7; font-weight: bold; }"
        )
        main_layout.addWidget(self.top_tabs, 1)

        # ── 설정 탭 ──
        settings_tab = QWidget()
        self.top_tabs.addTab(settings_tab, "⚙️ 설정")
        settings_layout = QVBoxLayout(settings_tab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(6)

        BOLD = QFont("맑은 고딕", 13, QFont.Bold)
        LABEL = QFont("맑은 고딕", 11, QFont.Bold)

        # ── AI 설정 ──
        ai_hdr = QHBoxLayout()
        lbl = QLabel("AI 설정")
        lbl.setFont(BOLD)
        ai_hdr.addWidget(lbl)
        btn_ai_refresh = QPushButton("🔄 새로고침")
        btn_ai_refresh.setStyleSheet("padding: 3px 10px; font-size: 11px; color: #4a6cf7; background: transparent; border: 1px solid #4a6cf7; border-radius: 4px;")
        btn_ai_refresh.setCursor(Qt.PointingHandCursor)
        btn_ai_refresh.clicked.connect(self._refresh_ai_section)
        ai_hdr.addWidget(btn_ai_refresh)
        ai_hdr.addStretch()
        layout.addLayout(ai_hdr)

        # AI는 GPT 전용 — 선택 UI 제거
        ai_frame = QHBoxLayout()
        ai_info = QLabel("AI: 자동 글쓰기")
        ai_info.setStyleSheet("font-weight: bold; color: #1e293b;")
        ai_frame.addWidget(ai_info)
        # 내부 호환용 더미 (저장/로드 로직에서 참조됨, 화면엔 안 보임)
        self.ai_gpt = QCheckBox()
        self.ai_gpt.setVisible(False)
        self.ai_gpt.setChecked(True)
        self.ai_gemini = QCheckBox()
        self.ai_gemini.setVisible(False)
        self.ai_gemini.setChecked(False)
        btn_lazy = QPushButton("(발급받기 귀찮으신분들 클릭)")
        btn_lazy.setStyleSheet("padding: 3px 10px; font-size: 11px; color: #ef4444; background: transparent; border: 1px solid #ef4444; border-radius: 4px;")
        btn_lazy.setCursor(Qt.PointingHandCursor)
        btn_lazy.clicked.connect(lambda: __import__('webbrowser').open("https://n-jobs.kr/payment.html"))
        ai_frame.addWidget(btn_lazy)
        ai_frame.addStretch()
        ai_w = QWidget()
        ai_w.setLayout(ai_frame)
        layout.addWidget(ai_w)

        # 본인 API 키 입력 — 글쓰기 엔진(딥시크/GPT/제미나이) + 이미지(Pixabay)
        api_configs = [
            ("딥시크 API 키", "deepseek_key", "키 발급방법", "https://shared-rise-9e5.notion.site/API-37df3feefb738025bce3e3e47d61fd71", "#7c3aed", ""),
            ("챗GPT API 키", "gpt_key", "키 발급방법", "https://shared-rise-9e5.notion.site/API-37df3feefb738025bce3e3e47d61fd71", "#1e293b", ""),
            ("제미나이 API 키", "gemini_key", "키 발급방법", "https://shared-rise-9e5.notion.site/API-37df3feefb738025bce3e3e47d61fd71", "#4285f4", ""),
            ("Pixabay API 키", "pixabay_key", "키 발급방법", "https://shared-rise-9e5.notion.site/API-37df3feefb7380e18179d4dedc5714db", "#22c55e", ""),
        ]

        self.api_key_fields = {}

        def _test_key(key_prefix, entry):
            from PySide6.QtWidgets import QMessageBox, QApplication
            import requests as _rq
            key = (entry.text() or "").strip()
            if not key:
                QMessageBox.warning(self, "API 키 테스트", "키를 먼저 입력한 뒤 테스트하세요.")
                return
            QApplication.setOverrideCursor(Qt.WaitCursor)
            ok = False
            detail = ""
            try:
                if key_prefix == "pixabay_key":
                    r = _rq.get("https://pixabay.com/api/",
                                params={"key": key, "q": "test", "per_page": 3}, timeout=10)
                    ok = (r.status_code == 200)
                    detail = "정상 작동하는 키입니다." if ok else f"무효한 키입니다. (HTTP {r.status_code})\n{r.text[:120]}"
                elif key_prefix == "gpt_key":
                    r = _rq.get("https://api.openai.com/v1/models",
                                headers={"Authorization": f"Bearer {key}"}, timeout=10)
                    ok = (r.status_code == 200)
                    if ok:
                        detail = "정상 작동하는 키입니다."
                    elif r.status_code == 401:
                        detail = "무효한 키입니다. (인증 실패 401)"
                    else:
                        detail = f"사용할 수 없습니다. (HTTP {r.status_code}) — 결제/권한/한도 확인 필요"
                elif key_prefix == "deepseek_key":
                    r = _rq.get("https://api.deepseek.com/user/balance",
                                headers={"Authorization": f"Bearer {key}"}, timeout=10)
                    ok = (r.status_code == 200)
                    if ok:
                        detail = "정상 작동하는 키입니다."
                    elif r.status_code == 401:
                        detail = "무효한 키입니다. (인증 실패 401)"
                    else:
                        detail = f"사용할 수 없습니다. (HTTP {r.status_code}) — 결제/충전 확인 필요"
                elif key_prefix == "gemini_key":
                    r = _rq.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=10)
                    ok = (r.status_code == 200)
                    if ok:
                        detail = "정상 작동하는 키입니다."
                    elif r.status_code in (400, 403):
                        detail = "무효한 키입니다. (인증 실패)"
                    else:
                        detail = f"사용할 수 없습니다. (HTTP {r.status_code})"
                else:
                    detail = "지원하지 않는 키 종류입니다."
            except Exception as e:
                detail = f"네트워크 오류: {e}"
            finally:
                QApplication.restoreOverrideCursor()
            if ok:
                QMessageBox.information(self, "API 키 테스트", f"✅ {detail}")
            else:
                QMessageBox.critical(self, "API 키 테스트", f"❌ {detail}")

        # ── 글쓰기 엔진 선택 (딥시크 / 챗GPT / 제미나이 중 택1) ──
        _eng_row = QHBoxLayout()
        _eng_lbl = QLabel("글쓰기 엔진:")
        _eng_lbl.setMinimumWidth(110)
        _eng_row.addWidget(_eng_lbl)
        self.rb_eng_deepseek = QRadioButton("딥시크")
        self.rb_eng_gpt = QRadioButton("챗GPT")
        self.rb_eng_gemini = QRadioButton("제미나이")
        self._eng_grp = QButtonGroup(self)
        for _rb in (self.rb_eng_deepseek, self.rb_eng_gpt, self.rb_eng_gemini):
            self._eng_grp.addButton(_rb)
            _eng_row.addWidget(_rb)
        _eng_row.addStretch()
        self.rb_eng_deepseek.setChecked(True)
        layout.addLayout(_eng_row)
        _eng_help = QLabel("선택한 엔진의 API 키가 있어야 글이 생성됩니다. (제미나이는 무료 한도가 있어 대량 생성 시 느릴 수 있어요)")
        _eng_help.setStyleSheet("color:#64748b; font-size:11px; padding:2px 0 6px 0;")
        _eng_help.setWordWrap(True)
        layout.addWidget(_eng_help)

        for label, key_prefix, btn_text, url, color, _ in api_configs:
            row_w = QWidget()
            row = QHBoxLayout(row_w)
            row.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setMinimumWidth(110)
            row.addWidget(lbl)
            entry = QLineEdit()
            entry.setPlaceholderText("(무료api 작동안함)")
            entry.setStyleSheet("padding: 5px;")
            entry.setEchoMode(QLineEdit.Password)
            row.addWidget(entry, stretch=1)
            # 보기/숨김 토글
            btn_show = QPushButton("👁")
            btn_show.setCheckable(True)
            btn_show.setFixedWidth(30)
            btn_show.setCursor(Qt.PointingHandCursor)
            btn_show.setStyleSheet("padding: 3px; font-size: 12px; background: transparent; border: 1px solid #94a3b8; border-radius: 4px;")
            btn_show.toggled.connect(lambda on, e=entry: e.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
            row.addWidget(btn_show)
            btn = QPushButton(btn_text)
            btn.setStyleSheet(f"padding: 3px 10px; font-size: 11px; color: {color}; background: transparent; border: 1px solid {color}; border-radius: 4px;")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, u=url: __import__('webbrowser').open(u))
            row.addWidget(btn)
            # 키 테스트 버튼 — 입력한 키가 실제로 작동하는지 즉시 확인
            btn_test = QPushButton("테스트")
            btn_test.setCursor(Qt.PointingHandCursor)
            btn_test.setStyleSheet("padding: 3px 10px; font-size: 11px; color: #2563eb; background: transparent; border: 1px solid #2563eb; border-radius: 4px;")
            btn_test.clicked.connect(lambda checked, kp=key_prefix, e=entry: _test_key(kp, e))
            row.addWidget(btn_test)
            layout.addWidget(row_w)
            self.api_key_fields[key_prefix] = {"entry": entry, "row": row_w}

        # 모든 키칸(딥시크·GPT·제미나이·픽사베이)은 항상 표시 — 각자 본인 키 직접 입력
        for _kp in ("deepseek_key", "gpt_key", "gemini_key", "pixabay_key"):
            _fi = self.api_key_fields.get(_kp)
            if _fi and _fi.get("row"):
                _fi["row"].setVisible(True)

        self._divider(layout)

        # ── 계정 설정 (탭 3개) ──
        acc_hdr = QHBoxLayout()
        lbl = QLabel("계정 설정")
        lbl.setFont(BOLD)
        acc_hdr.addWidget(lbl)
        btn_acc_refresh = QPushButton("🔄 새로고침")
        btn_acc_refresh.setStyleSheet("padding: 3px 10px; font-size: 11px; color: #4a6cf7; background: transparent; border: 1px solid #4a6cf7; border-radius: 4px;")
        btn_acc_refresh.setCursor(Qt.PointingHandCursor)
        btn_acc_refresh.clicked.connect(self._refresh_accounts_section)
        acc_hdr.addWidget(btn_acc_refresh)
        acc_hdr.addStretch()
        layout.addLayout(acc_hdr)

        self.account_tabs = QTabWidget()
        self.account_fields = []
        self.myeong_sub_tabs = []
        self.myeong_expires_labels = []

        for mi in range(3):
            myeong_widget = QWidget()
            myeong_layout = QVBoxLayout(myeong_widget)
            myeong_layout.setContentsMargins(0, 4, 0, 0)
            myeong_layout.setSpacing(4)

            exp_lbl = QLabel("구독 정보 로딩 중...")
            exp_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #64748b; padding: 2px 4px;")
            myeong_layout.addWidget(exp_lbl)
            self.myeong_expires_labels.append(exp_lbl)

            sub_tabs = QTabWidget()
            self.myeong_sub_tabs.append(sub_tabs)

            for ai in range(3):
                tab = QWidget()
                tab_layout = QVBoxLayout(tab)
                fields = {}
                for label_text, key, is_pw in [
                    ("블로그 ID", "blog_id", False),
                    ("네이버 ID", "naver_id", False),
                    ("네이버 비밀번호", "naver_pw", True),
                    ("블로그 카테고리", "blog_category", False),
                ]:
                    row = QHBoxLayout()
                    row.addWidget(QLabel(label_text))
                    if key == "naver_id" and not self.is_admin:
                        note = QLabel("(한번 입력 후 변경 불가능합니다.)")
                        note.setStyleSheet("color: #ef4444; font-size: 10px; font-weight: bold; margin-left: 6px;")
                        row.addWidget(note)
                    tab_layout.addLayout(row)
                    entry = QLineEdit()
                    if is_pw:
                        entry.setEchoMode(QLineEdit.Password)
                        pw_row = QHBoxLayout()
                        pw_row.addWidget(entry, stretch=1)
                        btn_eye = QPushButton("👁")
                        btn_eye.setCheckable(True)
                        btn_eye.setFixedWidth(30)
                        btn_eye.setCursor(Qt.PointingHandCursor)
                        btn_eye.setStyleSheet("padding: 3px; font-size: 12px; background: transparent; border: 1px solid #94a3b8; border-radius: 4px;")
                        btn_eye.toggled.connect(lambda on, e=entry: e.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
                        pw_row.addWidget(btn_eye)
                        tab_layout.addLayout(pw_row)
                    else:
                        tab_layout.addWidget(entry)
                    fields[key] = entry

                tab_layout.addStretch()
                sub_tabs.addTab(tab, f"아이디 {ai + 1}")
                self.account_fields.append(fields)

            myeong_layout.addWidget(sub_tabs)
            self.account_tabs.addTab(myeong_widget, f"명의 {mi + 1}")

        layout.addWidget(self.account_tabs)

        self._divider(layout)

        # ── 비밀번호 변경 ──
        pw_hdr = QLabel("비밀번호 변경")
        pw_hdr.setFont(BOLD)
        layout.addWidget(pw_hdr)

        for placeholder, attr, is_pw in [
            ("현재 비밀번호", "pw_cur", True),
            ("새 비밀번호", "pw_new", True),
            ("새 비밀번호 확인", "pw_new2", True),
        ]:
            e = QLineEdit()
            e.setPlaceholderText(placeholder)
            e.setEchoMode(QLineEdit.Password)
            e.setStyleSheet("padding: 5px;")
            row_pw = QHBoxLayout()
            row_pw.addWidget(e, stretch=1)
            btn_eye = QPushButton("👁")
            btn_eye.setCheckable(True)
            btn_eye.setFixedWidth(30)
            btn_eye.setCursor(Qt.PointingHandCursor)
            btn_eye.setStyleSheet("padding: 3px; font-size: 12px; background: transparent; border: 1px solid #94a3b8; border-radius: 4px;")
            btn_eye.toggled.connect(lambda on, ed=e: ed.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
            row_pw.addWidget(btn_eye)
            layout.addLayout(row_pw)
            setattr(self, attr, e)

        self.pw_msg = QLabel("")
        self.pw_msg.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.pw_msg)

        btn_pw_change = QPushButton("비밀번호 변경")
        btn_pw_change.setStyleSheet("background: #0ea5e9; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-weight: bold; max-width: 140px;")
        btn_pw_change.setCursor(Qt.PointingHandCursor)
        btn_pw_change.clicked.connect(self._change_password)
        layout.addWidget(btn_pw_change)

        self._divider(layout)

        # ── 이메일 발송 설정 (관리자 전용) ──
        if self.is_admin:
            smtp_hdr = QLabel("이메일 발송 설정 (비밀번호 찾기용)")
            smtp_hdr.setFont(BOLD)
            layout.addWidget(smtp_hdr)

            smtp_note = QLabel("Gmail 앱 비밀번호를 사용하세요 (2단계 인증 후 발급)")
            smtp_note.setStyleSheet("font-size: 11px; color: #64748b;")
            layout.addWidget(smtp_note)

            smtp_email_row = QHBoxLayout()
            smtp_email_row.addWidget(QLabel("발송 이메일"))
            self.smtp_email_edit = QLineEdit()
            self.smtp_email_edit.setPlaceholderText("example@gmail.com")
            self.smtp_email_edit.setStyleSheet("padding: 5px;")
            smtp_email_row.addWidget(self.smtp_email_edit, 1)
            layout.addLayout(smtp_email_row)

            smtp_pw_row = QHBoxLayout()
            smtp_pw_row.addWidget(QLabel("앱 비밀번호"))
            self.smtp_pw_edit = QLineEdit()
            self.smtp_pw_edit.setPlaceholderText("앱 비밀번호 (16자리)")
            self.smtp_pw_edit.setEchoMode(QLineEdit.Password)
            self.smtp_pw_edit.setStyleSheet("padding: 5px;")
            smtp_pw_row.addWidget(self.smtp_pw_edit, 1)
            layout.addLayout(smtp_pw_row)

            self._divider(layout)

        layout.addStretch()
        scroll.setWidget(scroll_widget)
        settings_layout.addWidget(scroll)

        # ── 구독 현황 탭 ──
        sub_tab = QWidget()
        sub_layout = QVBoxLayout(sub_tab)
        sub_layout.setContentsMargins(16, 12, 16, 12)
        sub_layout.setSpacing(10)
        self.top_tabs.addTab(sub_tab, "💳 구독 현황")
        self._build_subscription_tab(sub_layout)

        # ── 버튼 ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_close = QPushButton("닫기")
        btn_close.setFixedSize(100, 38)
        btn_close.setStyleSheet("QPushButton { background: #94a3b8; color: white; border: none; border-radius: 8px; font-size: 13px; } QPushButton:hover { background: #7c8da0; }")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)

        btn_save = QPushButton("설정 저장")
        btn_save.setFixedSize(120, 38)
        btn_save.setStyleSheet("QPushButton { background: #4a6cf7; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #3b5de7; }")
        btn_save.clicked.connect(self._save)
        btn_layout.addWidget(btn_save)

        main_layout.addLayout(btn_layout)

    def _refresh_ai_section(self):
        """관리자 부여 키 재반영 — users.json + config.json 다시 읽어서 API 입력칸 갱신"""
        from users import load_users as _lu
        user_entry = _lu().get(self.app_user, {}) if self.app_user else {}
        try:
            import json as _json, os as _os
            from config import CONFIG_FILE as _CF
            raw = {}
            if _os.path.exists(_CF):
                try:
                    with open(_CF, encoding="utf-8") as _f:
                        raw = _json.load(_f)
                except Exception:
                    raw = {}
        except Exception:
            raw = {}
        own_bucket = (raw.get("api_keys_by_user") or {}).get(self.app_user, {})
        firebase_keys = user_entry.get("api_keys", {}) or {}
        for key_prefix, field_info in self.api_key_fields.items():
            entry = field_info["entry"]
            own_list = [k for k in own_bucket.get(f"{key_prefix}_list", []) if k]
            if not own_list:
                own_list = [k for k in firebase_keys.get(f"{key_prefix}_list", []) if k]
            shared_list = [k for k in user_entry.get("shared_api_keys", {}).get(f"{key_prefix}_list", []) if k]
            has_key = bool(own_list) or bool(shared_list)
            if self.is_admin:
                own_val = own_list[0] if own_list else ""
                entry.setText(own_val)
                entry.setReadOnly(False)
                entry.setStyleSheet("padding: 5px;")
            else:
                # 일반 유저도 본인 키 직접 입력 가능. 본인 키 있으면 평문, shared만 있으면 가림 표시, 둘 다 없으면 빈칸 — 모두 편집 가능
                if own_list:
                    entry.setText(own_list[0])
                    entry.setReadOnly(False)
                    entry.setStyleSheet("padding: 5px;")
                elif shared_list:
                    entry.setText("●●●● 관리자 부여됨 ●●●●")
                    entry.setReadOnly(False)
                    entry.setStyleSheet("padding: 5px; background: #fef3c7; color: #92400e;")
                else:
                    entry.setText("")
                    entry.setReadOnly(False)
                    entry.setStyleSheet("padding: 5px;")
        self._sync_key_mode_radio()
        # 부모 윈도우의 잔여기간(남은일수) 라벨도 갱신
        try:
            parent = self.parent()
            if parent and hasattr(parent, "_update_expires_label"):
                if self.app_user:
                    user_entry = {"username": self.app_user, **user_entry}
                parent.current_user = user_entry
                parent._update_expires_label()
        except Exception:
            pass
        QMessageBox.information(self, "새로고침 완료", "AI 키 정보를 다시 불러왔습니다.")

    def _refresh_accounts_section(self):
        """관리자가 변경한 계정 수(max_accounts) 즉시 반영 + 대시보드 콤보박스 갱신"""
        from users import load_users as _lu
        user_entry = _lu().get(self.app_user, {}) if self.app_user else {}
        max_acc = int(user_entry.get("max_accounts", 3))
        # 잠금 상태 다시 적용
        for i, fields in enumerate(self.account_fields):
            naver = fields.get("naver_id")
            if not naver:
                continue
            if not self.is_admin and i >= max_acc:
                naver.setReadOnly(True)
                naver.setStyleSheet("background: #f1f5f9; color: #64748b;")
            else:
                # 이미 값이 있는 naver_id는 잠금 유지 (관리자 제외)
                cur_nid = (naver.text() or "").strip()
                if cur_nid and not self.is_admin:
                    naver.setReadOnly(True)
                    naver.setStyleSheet("background: #fee2e2; color: #991b1b;")
                else:
                    naver.setReadOnly(False)
                    naver.setStyleSheet("")
        # 부모 윈도우(MainWindow) 콤보박스 갱신
        try:
            parent = self.parent()
            if parent and hasattr(parent, "apply_user_session"):
                if self.app_user:
                    user_entry = {"username": self.app_user, **user_entry}
                parent.current_user = user_entry
                parent._refresh_account_combo()
                parent.apply_user_session(user_entry)
        except Exception:
            pass
        QMessageBox.information(self, "새로고침 완료", f"계정 수: {max_acc}개로 갱신했습니다.")

    def _jump_to_account(self, idx):
        self.account_tabs.setCurrentIndex(idx // 3)
        if idx // 3 < len(self.myeong_sub_tabs):
            self.myeong_sub_tabs[idx // 3].setCurrentIndex(idx % 3)

    def _update_myeong_expires_labels(self):
        import datetime as _dt
        today = _dt.date.today()
        parent = self.parent()
        cu = getattr(parent, "current_user", {}) if parent else {}
        if cu.get("role") == "admin" or self.is_admin:
            for lbl in self.myeong_expires_labels:
                lbl.setText("📌 관리자 계정  —  무제한")
                lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #22c55e; padding: 2px 4px;")
            return
        # 아이디 1개 = 명의 1개 구조 — 빈 명의2/3 라벨은 숨김 (분할 전 구계정 호환용으로 로직은 유지)
        keys = ["expires", "expires_2", "expires_3"]
        names = ["구독 (네이버 아이디 3개)", "2명의 (아이디 4-6)", "3명의 (아이디 7-9)"]
        for i, (lbl, key, name) in enumerate(zip(self.myeong_expires_labels, keys, names)):
            exp = (cu.get(key) or "").strip()
            if i > 0 and not exp:
                lbl.setVisible(False)
                continue
            lbl.setVisible(True)
            if not exp:
                lbl.setText(f"📌 {name}  —  무료 체험 중")
                lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #22c55e; padding: 2px 4px;")
            else:
                try:
                    y, m, d = map(int, exp.split("-"))
                    days = (_dt.date(y, m, d) - today).days
                    if days < 0:
                        lbl.setText(f"📌 {name}  —  만료됨 ({exp})")
                        lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #ef4444; padding: 2px 4px;")
                    else:
                        color = "#22c55e" if days >= 31 else "#f59e0b" if days >= 8 else "#ef4444"
                        lbl.setText(f"📌 {name}  —  잔여 {days}일 ({exp} 만료)")
                        lbl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color}; padding: 2px 4px;")
                except Exception:
                    lbl.setText(f"📌 {name}  —  알 수 없음")
                    lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #94a3b8; padding: 2px 4px;")

    def _show_paid_api_info(self):
        QMessageBox.information(
            self,
            "API 키 부여 안내",
            "홈페이지에서 월 9,900원 추가 결제하시면\n관리자가 API 키를 부여해드립니다."
        )

    def _divider(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(line)

    def _sync_key_mode_radio(self):
        """저장된 글쓰기 엔진 선택(ai_engine)을 라디오에 복원."""
        try:
            eng = (self.cfg.get("ai_engine") or "deepseek").strip().lower()
            if eng == "gpt":
                self.rb_eng_gpt.setChecked(True)
            elif eng == "gemini":
                self.rb_eng_gemini.setChecked(True)
            else:
                self.rb_eng_deepseek.setChecked(True)
        except Exception:
            pass

    def _load_values(self):
        # AI 제공자는 GPT 전용 고정
        self.ai_gpt.setChecked(True)

        # API 키 로드 — 본인 버킷(api_keys_by_user[현재 유저])에서만 직접 읽기
        from users import load_users as _lu
        user_entry = _lu().get(self.app_user, {}) if self.app_user else {}
        try:
            import json as _json, os as _os
            from config import CONFIG_FILE as _CF
            raw = {}
            if _os.path.exists(_CF):
                try:
                    with open(_CF, encoding="utf-8") as _f:
                        raw = _json.load(_f)
                except Exception:
                    raw = {}
        except Exception:
            raw = {}
        own_bucket = (raw.get("api_keys_by_user") or {}).get(self.app_user, {})
        firebase_keys = user_entry.get("api_keys", {}) or {}
        for key_prefix, field_info in self.api_key_fields.items():
            entry = field_info["entry"]
            own_list = [k for k in own_bucket.get(f"{key_prefix}_list", []) if k]
            if not own_list:
                own_list = [k for k in firebase_keys.get(f"{key_prefix}_list", []) if k]
            shared_list = [k for k in user_entry.get("shared_api_keys", {}).get(f"{key_prefix}_list", []) if k]
            has_key = bool(own_list) or bool(shared_list)
            if self.is_admin:
                own_val = own_list[0] if own_list else ""
                entry.setText(own_val)
                entry.setReadOnly(False)
                entry.setStyleSheet("padding: 5px;")
            else:
                # 일반 유저도 본인 키 직접 입력 가능. 본인 키 있으면 평문, shared만 있으면 가림 표시, 둘 다 없으면 빈칸 — 모두 편집 가능
                if own_list:
                    entry.setText(own_list[0])
                    entry.setReadOnly(False)
                    entry.setStyleSheet("padding: 5px;")
                elif shared_list:
                    entry.setText("●●●● 관리자 부여됨 ●●●●")
                    entry.setReadOnly(False)
                    entry.setStyleSheet("padding: 5px; background: #fef3c7; color: #92400e;")
                else:
                    entry.setText("")
                    entry.setReadOnly(False)
                    entry.setStyleSheet("padding: 5px;")

        self._sync_key_mode_radio()
        accounts = self.cfg.get("accounts", [])
        # 잠긴 네이버 ID 목록 (한 번 사용한 ID는 본인도 변경 불가)
        locked_set = set((s or "").strip().lower() for s in user_entry.get("locked_naver_ids", []))

        # 명의별 구독 활성화 여부 (parent의 current_user에서 expires 읽기)
        import datetime as _dt
        _today = _dt.date.today()
        def _exp_active(s):
            try:
                y, m, d = map(int, (s or "").strip().split("-"))
                return (_dt.date(y, m, d) - _today).days >= 0
            except Exception:
                return False
        _pu = getattr(self.parent(), "current_user", {}) if self.parent() else {}
        _m2_active = _exp_active(_pu.get("expires_2", ""))
        _m3_active = _exp_active(_pu.get("expires_3", ""))

        for i, fields in enumerate(self.account_fields):
            if i < len(accounts):
                acc = accounts[i]
                fields["blog_id"].setText(acc.get("blog_id", ""))
                fields["naver_id"].setText(acc.get("naver_id", ""))
                fields["naver_pw"].setText(acc.get("naver_pw", ""))
                fields["blog_category"].setText(acc.get("blog_category", ""))
            # 명의2/3 미구독 시 잠금
            if not self.is_admin:
                if i >= 6 and not _m3_active:
                    fields["naver_id"].setReadOnly(True)
                    fields["naver_id"].setStyleSheet("background: #f1f5f9; color: #64748b;")
                elif 3 <= i < 6 and not _m2_active:
                    fields["naver_id"].setReadOnly(True)
                    fields["naver_id"].setStyleSheet("background: #f1f5f9; color: #64748b;")
            # 네이버 ID가 이미 저장돼 있으면 자동 잠금 (관리자 제외)
            cur_nid = (fields["naver_id"].text() or "").strip()
            if cur_nid and not self.is_admin:
                fields["naver_id"].setReadOnly(True)
                fields["naver_id"].setStyleSheet("background: #fee2e2; color: #991b1b;")

        active = self.cfg.get("active_account", 0)
        self.account_tabs.setCurrentIndex(active // 3)
        if active // 3 < len(self.myeong_sub_tabs):
            self.myeong_sub_tabs[active // 3].setCurrentIndex(active % 3)
        self._update_myeong_expires_labels()
        self._update_subscription_status()

        # SMTP 설정 로드 (관리자)
        if self.is_admin:
            self.smtp_email_edit.setText(self.cfg.get("smtp_email", ""))
            self.smtp_pw_edit.setText(self.cfg.get("smtp_password", ""))

    def _change_password(self):
        from users import verify, update_user
        cur = self.pw_cur.text()
        new1 = self.pw_new.text()
        new2 = self.pw_new2.text()
        if not cur or not new1 or not new2:
            self.pw_msg.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.pw_msg.setText("모든 항목을 입력하세요.")
            return
        if new1 != new2:
            self.pw_msg.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.pw_msg.setText("새 비밀번호가 일치하지 않습니다.")
            return
        if len(new1) < 4:
            self.pw_msg.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.pw_msg.setText("새 비밀번호는 4자 이상이어야 합니다.")
            return
        user = verify(self.app_user, cur)
        if not user:
            self.pw_msg.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.pw_msg.setText("현재 비밀번호가 올바르지 않습니다.")
            return
        update_user(self.app_user, password=new1)
        self.pw_cur.clear(); self.pw_new.clear(); self.pw_new2.clear()
        self.pw_msg.setStyleSheet("color: #22c55e; font-size: 11px;")
        self.pw_msg.setText("비밀번호가 변경되었습니다.")

    def _save(self):
        self.cfg["ai_provider"] = "GPT"  # 하위호환
        # 글쓰기 엔진 선택 저장 (deepseek / gpt / gemini)
        try:
            if self.rb_eng_gpt.isChecked():
                self.cfg["ai_engine"] = "gpt"
            elif self.rb_eng_gemini.isChecked():
                self.cfg["ai_engine"] = "gemini"
            else:
                self.cfg["ai_engine"] = "deepseek"
        except Exception:
            self.cfg["ai_engine"] = "deepseek"

        # API 키 저장 — 관리자만 api_keys_by_user/Firebase api_keys에 저장.
        # 비관리자는 본인 버킷을 절대 건드리지 않음 (shared 키 leak 방지).
        import json as _json, os as _os
        from config import CONFIG_FILE as _CF
        self.cfg.pop("_has_shared_keys", None)
        if self.is_admin:
            raw = {}
            if _os.path.exists(_CF):
                try:
                    raw = _json.load(open(_CF, encoding="utf-8"))
                except Exception:
                    raw = {}
            own_bucket = dict((raw.get("api_keys_by_user") or {}).get(self.app_user, {}))
            for key_prefix, field_info in self.api_key_fields.items():
                val = field_info["entry"].text().strip()
                if val.startswith("●"):
                    continue
                own_bucket[f"{key_prefix}_list"] = [val] if val else []
                self.cfg[f"{key_prefix}_list"] = [val] if val else []
            # save_config가 이번 유저 본인 버킷을 갱신하도록 플래그
            self.cfg["_persist_api_keys_for_user"] = self.app_user
            # Firebase users.api_keys 동기화 (관리자 크로스 PC)
            try:
                from users import update_user as _upd
                _upd(self.app_user, api_keys={k: v for k, v in own_bucket.items() if v})
            except Exception:
                pass
        else:
            # 비관리자도 본인 버킷(api_keys_by_user[username])에 API 키 저장 가능
            raw = {}
            if _os.path.exists(_CF):
                try:
                    raw = _json.load(open(_CF, encoding="utf-8"))
                except Exception:
                    raw = {}
            own_bucket = dict((raw.get("api_keys_by_user") or {}).get(self.app_user, {}))
            for key_prefix, field_info in self.api_key_fields.items():
                val = field_info["entry"].text().strip()
                if val.startswith("●"):
                    continue
                own_bucket[f"{key_prefix}_list"] = [val] if val else []
                self.cfg[f"{key_prefix}_list"] = [val] if val else []
            self.cfg["_persist_api_keys_for_user"] = self.app_user
            # Firebase 동기화 (크로스 PC)
            try:
                from users import update_user as _upd
                _upd(self.app_user, api_keys={k: v for k, v in own_bucket.items() if v})
            except Exception:
                pass

        accounts = []
        for fields in self.account_fields:
            accounts.append({
                "blog_id": fields["blog_id"].text().strip(),
                "naver_id": fields["naver_id"].text().strip(),
                "naver_pw": fields["naver_pw"].text().strip(),
                "blog_category": fields["blog_category"].text().strip(),
            })

        # 1) 같은 유저 내 슬롯 중복 검사
        seen = {}
        for i, acc in enumerate(accounts):
            nid = acc["naver_id"].lower()
            if not nid:
                continue
            if nid in seen:
                QMessageBox.critical(
                    self, "중복 네이버 ID",
                    f"네이버 ID '{acc['naver_id']}' 가 아이디 {seen[nid]+1}번과 {i+1}번에 중복 등록되어 있습니다.\n각 네이버 ID는 하나의 슬롯에만 등록할 수 있습니다."
                )
                self._jump_to_account(i)
                return
            seen[nid] = i

        # 2) 다른 앱-유저가 이미 등록한 네이버 ID 차단 (전역 유일성)
        # 단, 자신이 이미 잠근 ID는 비밀번호/카테고리 수정으로 간주 → 체크 스킵
        from users import load_users as _lu_s
        _ue_s = _lu_s().get(self.app_user, {}) if self.app_user else {}
        locked_set = set((s or "").strip().lower() for s in _ue_s.get("locked_naver_ids", []))
        taken = get_taken_naver_ids(exclude_user=self.app_user)
        for i, acc in enumerate(accounts):
            nid = acc["naver_id"].lower()
            if not nid:
                continue
            if nid in locked_set:
                continue
            if nid in taken:
                QMessageBox.critical(
                    self, "네이버 ID 등록 불가",
                    f"네이버 ID '{acc['naver_id']}' 는 다른 사용자('{taken[nid]}')가 이미 등록한 계정입니다.\n각 네이버 ID는 한 사용자만 사용할 수 있습니다.\n\n관리자에게 문의하세요."
                )
                self._jump_to_account(i)
                return

        self.cfg["accounts"] = accounts
        _mi = self.account_tabs.currentIndex()
        _ai = self.myeong_sub_tabs[_mi].currentIndex() if _mi < len(self.myeong_sub_tabs) else 0
        self.cfg["active_account"] = _mi * 3 + _ai

        # SMTP 설정 저장 (관리자)
        if self.is_admin:
            self.cfg["smtp_email"] = self.smtp_email_edit.text().strip()
            self.cfg["smtp_password"] = self.smtp_pw_edit.text().strip()

        save_config(self.cfg)

        # 네이버 ID 잠금: 저장 시 locked_naver_ids에 추가 + 즉시 readonly (관리자 제외)
        if not self.is_admin:
            try:
                from users import load_users as _lu, update_user as _upd
                ue = _lu().get(self.app_user, {})
                locked = set((s or "").strip().lower() for s in ue.get("locked_naver_ids", []))
                for acc in accounts:
                    nid = (acc.get("naver_id") or "").strip().lower()
                    if nid:
                        locked.add(nid)
                _upd(self.app_user, locked_naver_ids=sorted(locked))
            except Exception:
                pass

            try:
                for fields in self.account_fields:
                    nid = (fields["naver_id"].text() or "").strip()
                    if nid:
                        fields["naver_id"].setReadOnly(True)
                        fields["naver_id"].setStyleSheet("background: #fee2e2; color: #991b1b;")
            except Exception:
                pass

        QMessageBox.information(self, "저장 완료", "설정이 저장되었습니다.")

    # ─────────────────────────────────────────
    # 구독 현황 탭
    # ─────────────────────────────────────────
    def _build_subscription_tab(self, layout):
        if self.is_admin:
            self._build_admin_subscription(layout)
        else:
            self._build_user_subscription(layout)

    def _build_user_subscription(self, layout):
        BOLD = QFont("맑은 고딕", 13, QFont.Bold)
        hdr = QLabel("내 구독 현황")
        hdr.setFont(BOLD)
        hdr.setStyleSheet("color: #1e293b; margin-bottom: 4px;")
        layout.addWidget(hdr)

        self.sub_status_labels = []
        SLOT_NAMES = ["명의 1 (아이디 1~3)", "명의 2 (아이디 4~6)", "명의 3 (아이디 7~9)"]

        for i, name in enumerate(SLOT_NAMES):
            frame = QFrame()
            frame.setObjectName("subCard")
            frame.setStyleSheet(
                "QFrame#subCard { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }"
            )
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(14, 10, 14, 10)
            fl.setSpacing(6)

            name_lbl = QLabel(f"<b>{name}</b>")
            name_lbl.setStyleSheet("background: transparent; border: none; font-size: 13px; color: #1e293b;")
            fl.addWidget(name_lbl)

            row1 = QHBoxLayout()
            base_lbl = QLabel("기본 구독: 로딩 중...")
            base_lbl.setStyleSheet("background: transparent; border: none; font-size: 12px;")
            row1.addWidget(base_lbl, 1)
            btn_base = QPushButton("갱신")
            btn_base.setFixedHeight(26)
            btn_base.setStyleSheet("padding: 2px 12px; font-size: 11px; color: #6366f1; background: transparent; border: 1px solid #6366f1; border-radius: 4px;")
            btn_base.setCursor(Qt.PointingHandCursor)
            btn_base.clicked.connect(self._open_payment)
            row1.addWidget(btn_base)
            fl.addLayout(row1)

            row2 = QHBoxLayout()
            api_lbl = QLabel("API 구독: 로딩 중...")
            api_lbl.setStyleSheet("background: transparent; border: none; font-size: 12px;")
            row2.addWidget(api_lbl, 1)
            btn_api = QPushButton("갱신")
            btn_api.setFixedHeight(26)
            btn_api.setStyleSheet("padding: 2px 12px; font-size: 11px; color: #6366f1; background: transparent; border: 1px solid #6366f1; border-radius: 4px;")
            btn_api.setCursor(Qt.PointingHandCursor)
            btn_api.clicked.connect(self._open_payment)
            row2.addWidget(btn_api)
            fl.addLayout(row2)

            self.sub_status_labels.append((base_lbl, api_lbl))
            layout.addWidget(frame)

        layout.addStretch()

        btn_refresh = QPushButton("🔄 구독 현황 새로고침")
        btn_refresh.setStyleSheet(
            "QPushButton { padding: 6px 20px; font-size: 12px; color: #4a6cf7; background: transparent; border: 1px solid #4a6cf7; border-radius: 6px; }"
            "QPushButton:hover { background: #eff3ff; }"
        )
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self._refresh_subscription)
        layout.addWidget(btn_refresh, alignment=Qt.AlignCenter)

    def _build_admin_subscription(self, layout):
        BOLD = QFont("맑은 고딕", 13, QFont.Bold)
        hdr = QLabel("구독 관리 (관리자)")
        hdr.setFont(BOLD)
        hdr.setStyleSheet("color: #1e293b; margin-bottom: 4px;")
        layout.addWidget(hdr)

        user_row = QHBoxLayout()
        user_row.addWidget(QLabel("사용자:"))
        self.sub_user_combo = QComboBox()
        self.sub_user_combo.setStyleSheet("padding: 4px; min-height: 28px;")
        user_row.addWidget(self.sub_user_combo, 1)
        btn_load = QPushButton("불러오기")
        btn_load.setStyleSheet(
            "QPushButton { padding: 4px 14px; font-size: 12px; color: #4a6cf7; border: 1px solid #4a6cf7; border-radius: 4px; background: transparent; }"
            "QPushButton:hover { background: #eff3ff; }"
        )
        btn_load.setCursor(Qt.PointingHandCursor)
        btn_load.clicked.connect(self._admin_load_user_sub)
        user_row.addWidget(btn_load)
        layout.addLayout(user_row)

        # 아이디 1개 = 명의 1개 — 관리자 부여도 명의1(expires)만 사용 (명의2/3 입력 제거)
        FIELDS = [
            ("기본 구독", "expires"),
            ("API 구독",  "api_expires"),
        ]
        self.admin_sub_fields = {}
        for label, key in FIELDS:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(130)
            row.addWidget(lbl)
            e = QLineEdit()
            e.setPlaceholderText("YYYY-MM-DD  (빈칸=미구독)")
            e.setStyleSheet("padding: 5px;")
            row.addWidget(e, 1)
            layout.addLayout(row)
            self.admin_sub_fields[key] = e

        btn_save = QPushButton("💾 구독 정보 저장")
        btn_save.setStyleSheet(
            "QPushButton { background: #4a6cf7; color: white; border: none; border-radius: 6px; padding: 8px 24px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: #3b5de7; }"
        )
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._admin_save_user_sub)
        layout.addWidget(btn_save, alignment=Qt.AlignCenter)

        layout.addStretch()
        self._admin_fill_user_combo()

    def _admin_fill_user_combo(self):
        from users import load_users as _lu
        users = _lu()
        self.sub_user_combo.clear()
        for uid in sorted(users.keys()):
            if uid == "admin":
                continue
            u = users[uid]
            name = (u.get("name") or "").strip()
            display = f"{uid}  ({name})" if name else uid
            self.sub_user_combo.addItem(display, userData=uid)

    def _admin_load_user_sub(self):
        from users import load_users as _lu
        uid = self.sub_user_combo.currentData()
        if not uid:
            QMessageBox.warning(self, "선택 오류", "사용자를 선택하세요.")
            return
        u = _lu().get(uid, {})
        for key, e in self.admin_sub_fields.items():
            e.setText((u.get(key) or "").strip())

    def _admin_save_user_sub(self):
        from users import update_user as _upd
        uid = self.sub_user_combo.currentData()
        if not uid:
            QMessageBox.warning(self, "선택 오류", "사용자를 선택하세요.")
            return
        kwargs = {key: e.text().strip() for key, e in self.admin_sub_fields.items()}
        try:
            _upd(uid, **kwargs)
            QMessageBox.information(self, "저장 완료", f"{uid}의 구독 정보가 저장되었습니다.")
        except Exception as ex:
            QMessageBox.critical(self, "저장 실패", str(ex))

    def _open_payment(self):
        parent = self.parent()
        if parent and hasattr(parent, "_open_payment_dialog"):
            parent._open_payment_dialog()
        else:
            QMessageBox.information(self, "안내", "메인 화면에서 '구독 연장' 버튼을 이용하세요.")

    def _refresh_subscription(self):
        from users import load_users as _lu
        u = _lu().get(self.app_user, {})
        parent = self.parent()
        if parent:
            cu = dict(getattr(parent, "current_user", {}))
            for k in ["expires", "expires_2", "expires_3", "api_expires", "api_expires_2", "api_expires_3"]:
                cu[k] = u.get(k, "")
            parent.current_user = cu
        self._update_subscription_status(u)

    def _update_subscription_status(self, user=None):
        if not hasattr(self, "sub_status_labels"):
            return
        import datetime as _dt
        if user is None:
            parent = self.parent()
            user = getattr(parent, "current_user", {}) if parent else {}
        today = _dt.date.today()
        BASE_FIELDS = ["expires", "expires_2", "expires_3"]
        API_FIELDS  = ["api_expires", "api_expires_2", "api_expires_3"]

        def _fmt(exp_str):
            s = (exp_str or "").strip()
            if not s:
                return "❌ 미구독", "#ef4444"
            try:
                d = _dt.date.fromisoformat(s)
                days = (d - today).days
                if days < 0:
                    return f"❌ 만료됨 ({s})", "#ef4444"
                color = "#22c55e" if days >= 31 else "#f59e0b" if days >= 8 else "#ef4444"
                return f"✅ {days}일 남음 ({s})", color
            except Exception:
                return "? 알 수 없음", "#94a3b8"

        is_admin_user = (user.get("role") == "admin" or self.is_admin)
        for i, (base_lbl, api_lbl) in enumerate(self.sub_status_labels):
            if is_admin_user:
                base_lbl.setText("기본 구독: ♾️ 무제한")
                base_lbl.setStyleSheet("background: transparent; border: none; font-size: 12px; color: #22c55e;")
                api_lbl.setText("API 구독: ♾️ 무제한")
                api_lbl.setStyleSheet("background: transparent; border: none; font-size: 12px; color: #22c55e;")
            else:
                # 1명의 구조 — 값 없는 명의2/3 상태 라벨은 숨김
                if i > 0 and not (user.get(BASE_FIELDS[i]) or user.get(API_FIELDS[i])):
                    base_lbl.setVisible(False)
                    api_lbl.setVisible(False)
                    continue
                base_lbl.setVisible(True)
                api_lbl.setVisible(True)
                b_txt, b_col = _fmt(user.get(BASE_FIELDS[i], ""))
                a_txt, a_col = _fmt(user.get(API_FIELDS[i], ""))
                base_lbl.setText(f"기본 구독: {b_txt}")
                base_lbl.setStyleSheet(f"background: transparent; border: none; font-size: 12px; color: {b_col};")
                api_lbl.setText(f"API 구독: {a_txt}")
                api_lbl.setStyleSheet(f"background: transparent; border: none; font-size: 12px; color: {a_col};")
