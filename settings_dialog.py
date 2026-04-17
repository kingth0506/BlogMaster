# -*- coding: utf-8 -*-
"""환경설정 다이얼로그 (PySide6) — 아이디 3개 지원"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QButtonGroup, QFrame, QMessageBox,
    QScrollArea, QWidget, QTabWidget, QTextEdit, QComboBox, QListWidget
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from config import load_config, save_config, get_taken_naver_ids
from prompts import load_prompts, save_prompts


class SettingsDialog(QDialog):
    def __init__(self, parent=None, is_admin=False, app_user="admin"):
        super().__init__(parent)
        self.setWindowTitle("환경설정")
        self.setFixedSize(550, 620)
        self.cfg = load_config()
        self.prompts = load_prompts()
        self.is_admin = is_admin
        self.app_user = app_user
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # 최상위 탭: 설정 / 프롬프트
        self.main_tabs = QTabWidget()
        main_layout.addWidget(self.main_tabs)

        # ── 설정 탭 ──
        settings_tab = QWidget()
        self.main_tabs.addTab(settings_tab, "설정")
        settings_layout = QVBoxLayout(settings_tab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(6)

        BOLD = QFont("맑은 고딕", 13, QFont.Bold)
        LABEL = QFont("맑은 고딕", 11, QFont.Bold)

        # ── AI 설정 ──
        lbl = QLabel("AI 설정")
        lbl.setFont(BOLD)
        layout.addWidget(lbl)

        layout.addWidget(QLabel("사용할 AI 선택"))
        ai_frame = QHBoxLayout()
        self.ai_gemini = QRadioButton("Gemini")
        self.ai_gpt = QRadioButton("GPT")
        self.ai_gemini.setChecked(True)
        self.ai_group = QButtonGroup()
        self.ai_group.addButton(self.ai_gemini)
        self.ai_group.addButton(self.ai_gpt)
        ai_frame.addWidget(self.ai_gemini)
        ai_frame.addWidget(self.ai_gpt)
        ai_frame.addStretch()
        ai_w = QWidget()
        ai_w.setLayout(ai_frame)
        layout.addWidget(ai_w)

        # API 키 입력 (각 3개씩 탭)
        api_configs = [
            ("Gemini API 키", "gemini_key", "키 발급받기", "https://aistudio.google.com/apikey", "#4a6cf7", ""),
            ("GPT API 키", "gpt_key", "키 발급받기 (유료)", "https://platform.openai.com/api-keys", "#1e293b", ""),
            ("Pixabay API 키", "pixabay_key", "키 발급받기", "https://pixabay.com/api/docs/", "#22c55e", ""),
        ]

        self.api_key_fields = {}
        for label, key_prefix, btn_text, url, color, _ in api_configs:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            btn = QPushButton(btn_text)
            btn.setStyleSheet(f"padding: 3px 10px; font-size: 11px; color: {color}; background: transparent; border: 1px solid {color}; border-radius: 4px;")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, u=url: __import__('webbrowser').open(u))
            row.addWidget(btn)
            row.addStretch()
            layout.addLayout(row)

            key_tabs = QTabWidget()
            key_tabs.setFixedHeight(70)
            entries = []
            for i in range(3):
                entry = QLineEdit()
                key_tabs.addTab(entry, f"키 {i+1}")
                entries.append(entry)
            layout.addWidget(key_tabs)
            self.api_key_fields[key_prefix] = {"tabs": key_tabs, "entries": entries}

        self._divider(layout)

        # ── 계정 설정 (탭 3개) ──
        lbl = QLabel("계정 설정")
        lbl.setFont(BOLD)
        layout.addWidget(lbl)

        self.account_tabs = QTabWidget()
        self.account_fields = []

        for i in range(9):
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
                    lock = QLabel("🔒 관리자 전용")
                    lock.setStyleSheet("color: #ef4444; font-size: 10px; font-weight: bold;")
                    row.addStretch()
                    row.addWidget(lock)
                tab_layout.addLayout(row)
                entry = QLineEdit()
                if is_pw:
                    entry.setEchoMode(QLineEdit.Password)
                tab_layout.addWidget(entry)
                fields[key] = entry

            tab_layout.addStretch()
            self.account_tabs.addTab(tab, f"아이디 {i+1}")
            self.account_fields.append(fields)

        layout.addWidget(self.account_tabs)

        self._divider(layout)

        # ── 기타 설정 ──
        lbl = QLabel("기타 설정")
        lbl.setFont(BOLD)
        layout.addWidget(lbl)

        for label_text, attr_name in [
            ("BrandConnect", "brand_entry"),
            ("Connect", "connect_entry"),
            ("Connect Naver", "connect_naver_entry"),
        ]:
            layout.addWidget(QLabel(label_text))
            entry = QLineEdit()
            layout.addWidget(entry)
            setattr(self, attr_name, entry)

        self._divider(layout)


        layout.addStretch()
        scroll.setWidget(scroll_widget)
        settings_layout.addWidget(scroll)

        # ── 프롬프트 탭 ──
        prompt_tab = QWidget()
        self.main_tabs.addTab(prompt_tab, "프롬프트")
        prompt_layout = QVBoxLayout(prompt_tab)

        # 업종 선택
        top_p = QHBoxLayout()
        top_p.addWidget(QLabel("업종:"))
        self.prompt_list = QComboBox()
        self.prompt_list.setMinimumWidth(150)
        self.prompt_list.currentTextChanged.connect(self._on_prompt_selected)
        top_p.addWidget(self.prompt_list)

        btn_add_biz = QPushButton("업종 추가")
        btn_add_biz.setStyleSheet("padding: 5px 12px;")
        btn_add_biz.clicked.connect(self._add_prompt)
        top_p.addWidget(btn_add_biz)

        btn_del_biz = QPushButton("업종 삭제")
        btn_del_biz.setStyleSheet("padding: 5px 12px; background: #ef4444; color: white; border: none; border-radius: 6px;")
        btn_del_biz.clicked.connect(self._delete_prompt)
        top_p.addWidget(btn_del_biz)
        top_p.addStretch()
        prompt_layout.addLayout(top_p)

        # 블로그 글 프롬프트
        prompt_layout.addWidget(QLabel("블로그 글 프롬프트"))
        self.blog_prompt_edit = QTextEdit()
        self.blog_prompt_edit.setFont(QFont("맑은 고딕", 10))
        prompt_layout.addWidget(self.blog_prompt_edit, stretch=3)

        # 제목 프롬프트
        prompt_layout.addWidget(QLabel("제목 마무리 문구 프롬프트"))
        self.title_prompt_edit = QTextEdit()
        self.title_prompt_edit.setFont(QFont("맑은 고딕", 10))
        prompt_layout.addWidget(self.title_prompt_edit, stretch=1)

        # 변수 안내
        info = QLabel("사용 가능 변수: {업체명} {주소} {근처역} {카테고리} {앞키워드} {태그} {업종} {키워드}")
        info.setStyleSheet("color: #666; font-size: 11px;")
        prompt_layout.addWidget(info)

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

    def _divider(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(line)

    def _load_values(self):
        # pixabay는 api_key_fields에서 관리
        provider = self.cfg.get("ai_provider", "Gemini")
        if provider == "GPT":
            self.ai_gpt.setChecked(True)
        else:
            self.ai_gemini.setChecked(True)

        # API 키 로드
        for key_prefix, field_info in self.api_key_fields.items():
            keys = self.cfg.get(f"{key_prefix}_list", [])
            # 구버전 호환
            if not keys:
                old_key = self.cfg.get(f"{key_prefix}_entry", "") or self.cfg.get("gemini_api_key", "") if key_prefix == "gemini_key" else ""
                if not old_key and key_prefix == "pixabay_key":
                    old_key = self.cfg.get("pixabay_api_key", "")
                keys = [old_key, "", ""]
            for i, entry in enumerate(field_info["entries"]):
                if i < len(keys):
                    entry.setText(keys[i])

        accounts = self.cfg.get("accounts", [])
        for i, fields in enumerate(self.account_fields):
            if i < len(accounts):
                acc = accounts[i]
                fields["blog_id"].setText(acc.get("blog_id", ""))
                fields["naver_id"].setText(acc.get("naver_id", ""))
                fields["naver_pw"].setText(acc.get("naver_pw", ""))
                fields["blog_category"].setText(acc.get("blog_category", ""))
            if not self.is_admin:
                fields["naver_id"].setReadOnly(True)
                fields["naver_id"].setStyleSheet("background: #f1f5f9; color: #64748b;")

        active = self.cfg.get("active_account", 0)
        self.account_tabs.setCurrentIndex(active)

        self.brand_entry.setText(self.cfg.get("brand_connect", ""))
        self.connect_entry.setText(self.cfg.get("connect", ""))
        self.connect_naver_entry.setText(self.cfg.get("connect_naver", ""))

        # 프롬프트 로드
        self.prompt_list.clear()
        for key in self.prompts:
            self.prompt_list.addItem(key)
        if self.prompt_list.count() > 0:
            self.prompt_list.setCurrentIndex(0)

    def _on_prompt_selected(self, name):
        # 이전 프롬프트 저장
        self._save_current_prompt()
        if not name or name not in self.prompts:
            return
        p = self.prompts[name]
        self.blog_prompt_edit.setPlainText(p.get("blog", ""))
        self.title_prompt_edit.setPlainText(p.get("title", ""))

    def _save_current_prompt(self):
        name = self.prompt_list.currentText()
        if name:
            self.prompts[name] = {
                "blog": self.blog_prompt_edit.toPlainText(),
                "title": self.title_prompt_edit.toPlainText(),
            }

    def _add_prompt(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "업종 추가", "업종명 입력:")
        if ok and name.strip():
            name = name.strip()
            self.prompts[name] = {"blog": "", "title": ""}
            self.prompt_list.addItem(name)
            self.prompt_list.setCurrentText(name)

    def _delete_prompt(self):
        name = self.prompt_list.currentText()
        if not name:
            return
        if name == "기본":
            QMessageBox.warning(self, "삭제 불가", "기본 프롬프트는 삭제할 수 없습니다.")
            return
        reply = QMessageBox.question(self, "삭제 확인", f"'{name}' 프롬프트를 삭제하시겠습니까?")
        if reply == QMessageBox.Yes:
            del self.prompts[name]
            self.prompt_list.removeItem(self.prompt_list.currentIndex())

    def _save(self):
        # 현재 편집 중인 프롬프트 저장
        self._save_current_prompt()
        # pixabay는 api_key_fields에서 관리
        self.cfg["ai_provider"] = "GPT" if self.ai_gpt.isChecked() else "Gemini"

        # API 키 저장
        for key_prefix, field_info in self.api_key_fields.items():
            keys = [entry.text().strip() for entry in field_info["entries"]]
            self.cfg[f"{key_prefix}_list"] = keys

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
                self.account_tabs.setCurrentIndex(i)
                return
            seen[nid] = i

        # 2) 다른 앱-유저가 이미 등록한 네이버 ID 차단 (전역 유일성)
        taken = get_taken_naver_ids(exclude_user=self.app_user)
        for i, acc in enumerate(accounts):
            nid = acc["naver_id"].lower()
            if not nid:
                continue
            if nid in taken:
                QMessageBox.critical(
                    self, "네이버 ID 등록 불가",
                    f"네이버 ID '{acc['naver_id']}' 는 다른 사용자('{taken[nid]}')가 이미 등록한 계정입니다.\n각 네이버 ID는 한 사용자만 사용할 수 있습니다."
                )
                self.account_tabs.setCurrentIndex(i)
                return

        self.cfg["accounts"] = accounts
        self.cfg["active_account"] = self.account_tabs.currentIndex()

        self.cfg["brand_connect"] = self.brand_entry.text().strip()
        self.cfg["connect"] = self.connect_entry.text().strip()
        self.cfg["connect_naver"] = self.connect_naver_entry.text().strip()

        save_config(self.cfg)
        save_prompts(self.prompts)
        QMessageBox.information(self, "저장 완료", "설정이 저장되었습니다.")
