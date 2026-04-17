# -*- coding: utf-8 -*-
"""네이버 플레이스 블로그 자동 포스팅 — PySide6 GUI"""
import os
import sys

if sys.platform == "win32":
    os.environ["PYTHONUTF8"] = "1"

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton, QComboBox, QTextEdit,
    QFrame, QMessageBox, QDialog, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QCheckBox,
    QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QObject
from PySide6.QtGui import QFont, QColor, QTextCursor, QShortcut, QKeySequence

import threading
import datetime
import json

from config import load_config, save_config
from content_generator import generate_content
from image_handler import download_images
from places_crawler import crawl_places, save_results, load_results
from naver_poster import NaverBlogPoster
from usage_tracker import get_remaining, add_usage, add_post


STYLE = """
QMainWindow { background: #f0f2f5; }
QLabel { color: #1e293b; }

#header { background: #4a6cf7; }
#header QLabel { color: white; font-size: 18px; font-weight: bold; }
#header QPushButton {
    background: #3b5de7; color: white; border: none; border-radius: 6px;
    padding: 6px 18px; font-weight: bold; font-size: 12px;
}
#header QPushButton:hover { background: #2d4ed8; }

#leftPanel {
    background: white; border: 1px solid #e2e8f0; border-radius: 10px;
}

#sectionLabel { font-size: 13px; font-weight: bold; color: #1e293b; }
#subLabel { font-size: 11px; color: #64748b; }

QLineEdit, QSpinBox {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
    padding: 8px 12px; font-size: 13px; color: #1e293b;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #94a3b8;
}

QComboBox {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
    padding: 6px 10px; font-size: 12px;
}

#btnCrawl {
    background: #4a6cf7; color: white; border: none; border-radius: 8px;
    font-size: 13px; font-weight: bold; padding: 10px;
}
#btnCrawl:hover { background: #3b5de7; }

#btnStop {
    background: #94a3b8; color: white; border: none; border-radius: 8px;
    font-size: 12px; padding: 8px;
}
#btnStop:hover { background: #7c8da0; }

#btnPost {
    background: #8b5cf6; color: white; border: none; border-radius: 8px;
    font-size: 14px; font-weight: bold; padding: 12px;
}
#btnPost:hover { background: #7c3aed; }

#btnResult {
    background: transparent; color: #333; border: 1px solid #ccc; border-radius: 8px;
    font-size: 12px; padding: 8px;
}
#btnResult:hover { background: #e8e8e8; }

#logPanel {
    background: white; border: 1px solid #e2e8f0; border-radius: 10px;
}

#logHeader { font-size: 13px; font-weight: bold; }

QTextEdit {
    background: white; border: none; font-size: 12px; color: #334155;
    padding: 10px;
}
"""


class MainWindow(QMainWindow):
    log_signal = Signal(str)
    status_signal = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("플레이스 블로그 자동화")
        self.setMinimumSize(1000, 700)
        self.resize(1600, 1000)

        self.cfg = load_config()
        self.crawled_data = []
        self.is_crawling = False
        self.is_posting = False
        self.stop_flag = False
        self.result_file = ""
        self.last_keyword = self.cfg.get("last_keyword", "")

        self.log_signal.connect(self._append_log)
        self.status_signal.connect(self._update_status)

        self._build_ui()
        self._migrate_legacy_logs()

        # 단축키
        QShortcut(QKeySequence("F5"), self).activated.connect(self._start_crawl)
        QShortcut(QKeySequence("F6"), self).activated.connect(self._stop)
        QShortcut(QKeySequence("F7"), self).activated.connect(self._generate_posts)
        QShortcut(QKeySequence("F8"), self).activated.connect(self._view_generated_posts)

        self._emit_log("프로그램 시작됨")
        self._emit_log("설정에서 API키와 계정 정보를 먼저 입력해주세요")

    def closeEvent(self, event):
        reply = QMessageBox.question(self, "종료 확인", "프로그램을 종료하시겠습니까?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 헤더 ──
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(55)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(25, 0, 20, 0)

        title = QLabel("플레이스 블로그 자동화")
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_prompts = QPushButton("프롬프트")
        btn_prompts.setCursor(Qt.PointingHandCursor)
        btn_prompts.clicked.connect(self._open_prompt_editor)
        h_layout.addWidget(btn_prompts)

        self.btn_admin = QPushButton("관리자")
        self.btn_admin.setStyleSheet("background: #f59e0b; color: white; border: none; border-radius: 6px; padding: 6px 14px;")
        self.btn_admin.setCursor(Qt.PointingHandCursor)
        self.btn_admin.clicked.connect(self._open_admin_dialog)
        self.btn_admin.setVisible(False)  # 기본 숨김, admin 로그인 시 노출
        h_layout.addWidget(self.btn_admin)

        btn_settings = QPushButton("설정")
        btn_settings.setCursor(Qt.PointingHandCursor)
        btn_settings.clicked.connect(self._open_settings)
        h_layout.addWidget(btn_settings)

        root_layout.addWidget(header)

        # ── 메인 ──
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # ── 좌측 패널 ──
        left = QFrame()
        left.setObjectName("leftPanel")
        left.setFixedWidth(310)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(5)

        # 키워드 (히스토리 드롭다운)
        lbl = QLabel("키워드 입력")
        lbl.setObjectName("sectionLabel")
        left_layout.addWidget(lbl)

        self.keyword_input = QComboBox()
        self.keyword_input.setEditable(True)
        self.keyword_input.setInsertPolicy(QComboBox.NoInsert)
        self.keyword_input.lineEdit().setPlaceholderText("키워드를 입력하세요")
        self.keyword_input.lineEdit().returnPressed.connect(self._start_crawl)
        self._load_keyword_history()
        left_layout.addWidget(self.keyword_input)

        left_layout.addSpacing(5)
        self._add_divider(left_layout)

        # 크롤링 설정
        lbl = QLabel("크롤링 설정")
        lbl.setObjectName("sectionLabel")
        left_layout.addWidget(lbl)

        sub = QLabel("수집 개수")
        sub.setObjectName("subLabel")
        left_layout.addWidget(sub)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 500)
        self.count_spin.setValue(100)
        left_layout.addWidget(self.count_spin)

        btn_start = QPushButton("크롤링 시작 (F5)")
        btn_start.setObjectName("btnCrawl")
        btn_start.setCursor(Qt.PointingHandCursor)
        btn_start.clicked.connect(self._start_crawl)
        left_layout.addWidget(btn_start)

        btn_stop = QPushButton("중단 (F6)")
        btn_stop.setObjectName("btnStop")
        btn_stop.setCursor(Qt.PointingHandCursor)
        btn_stop.clicked.connect(self._stop)
        left_layout.addWidget(btn_stop)

        left_layout.addSpacing(5)
        self._add_divider(left_layout)

        # 포스팅 설정
        lbl = QLabel("포스팅 설정")
        lbl.setObjectName("sectionLabel")
        left_layout.addWidget(lbl)

        sub = QLabel("발행 간격")
        sub.setObjectName("subLabel")
        left_layout.addWidget(sub)

        iv_widget = QWidget()
        iv_layout = QHBoxLayout(iv_widget)
        iv_layout.setContentsMargins(0, 0, 0, 0)

        self.interval_hour = QComboBox()
        self.interval_hour.addItems([str(h) for h in range(25)])
        self.interval_hour.setCurrentText("2")
        iv_layout.addWidget(self.interval_hour)
        iv_layout.addWidget(QLabel("시간"))

        self.interval_min = QComboBox()
        self.interval_min.addItems([str(m) for m in range(0, 60, 3)])
        self.interval_min.setCurrentText("0")
        iv_layout.addWidget(self.interval_min)
        iv_layout.addWidget(QLabel("분"))
        iv_layout.addStretch()

        left_layout.addWidget(iv_widget)

        left_layout.addSpacing(8)

        btn_generate = QPushButton("포스트 생성 (F7)")
        btn_generate.setObjectName("btnPost")
        btn_generate.setCursor(Qt.PointingHandCursor)
        btn_generate.clicked.connect(self._generate_posts)
        left_layout.addWidget(btn_generate)

        btn_view_posts = QPushButton("생성된 포스트 보기 및 포스팅 (F8)")
        btn_view_posts.setStyleSheet(
            "background: #3b82f6; color: white; border: none; border-radius: 8px; "
            "font-size: 14px; font-weight: bold; padding: 10px; "
        )
        btn_view_posts.setCursor(Qt.PointingHandCursor)
        btn_view_posts.clicked.connect(self._view_generated_posts)
        left_layout.addWidget(btn_view_posts)

        btn_result = QPushButton("크롤링 결과보기")
        btn_result.setObjectName("btnResult")
        btn_result.setCursor(Qt.PointingHandCursor)
        btn_result.clicked.connect(self._show_results)
        left_layout.addWidget(btn_result)

        left_layout.addStretch()
        main_layout.addWidget(left)

        # ── 우측 패널 ──
        right = QFrame()
        right.setObjectName("logPanel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(15, 12, 15, 15)
        right_layout.setSpacing(5)

        # 대시보드
        dash = QFrame()
        dash.setStyleSheet("background: transparent; border: none;")
        dash_layout = QHBoxLayout(dash)
        dash_layout.setContentsMargins(4, 4, 4, 4)

        from PySide6.QtWidgets import QSizePolicy
        from PySide6.QtGui import QPixmap, QPainter, QPolygon
        from PySide6.QtCore import QPoint
        # 드롭다운 화살표 이미지 생성 (1회)
        _arrow_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_down_arrow.png").replace("\\", "/")
        if not os.path.exists(_arrow_path):
            pm = QPixmap(10, 6)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setBrush(Qt.black)
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygon([QPoint(0, 0), QPoint(10, 0), QPoint(5, 6)]))
            p.end()
            pm.save(_arrow_path)

        self.account_combo = QComboBox()
        self.account_combo.setCursor(Qt.PointingHandCursor)
        self.account_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.account_combo.setMinimumContentsLength(6)
        self.account_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.account_combo.setMaximumWidth(260)
        self.account_combo.setStyleSheet(f"""
            QComboBox {{
                font-size: 12px;
                color: #000;
                background-color: #ffffff;
                padding: 1px 4px;
                border: 1px solid #7f9db9;
                border-radius: 0px;
                min-height: 20px;
            }}
            QComboBox:hover {{
                background-color: #f0f8ff;
            }}
            QComboBox:focus {{
                border: 1px solid #316ac5;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #7f9db9;
                background-color: #ece9d8;
            }}
            QComboBox::down-arrow {{
                image: url({_arrow_path});
                width: 10px;
                height: 6px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #7f9db9;
                background-color: #ffffff;
                color: #000;
                selection-background-color: #316ac5;
                selection-color: #ffffff;
                font-size: 12px;
                padding: 0px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 20px;
                padding: 2px 6px;
                color: #000;
                background-color: #ffffff;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #316ac5;
                color: #ffffff;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #ffffff;
                color: #000;
            }}
            QComboBox QAbstractItemView::item:selected:hover {{
                background-color: #316ac5;
                color: #ffffff;
            }}
        """)
        self._refresh_account_combo()
        self.account_combo.currentIndexChanged.connect(self._on_account_changed)

        self.dash_posts = QLabel("오늘 작성: 0개")
        self.dash_posts.setStyleSheet("font-weight: bold; font-size: 12px; color: #1e293b;")
        self.dash_remaining = QLabel("작성 가능: 750개")
        self.dash_remaining.setStyleSheet("font-weight: bold; font-size: 12px; color: #22c55e;")
        self.dash_ai = QLabel("AI: 0/1500")
        self.dash_ai.setStyleSheet("font-size: 11px; color: #64748b;")
        self.dash_pix = QLabel("Pixabay: 0/2400")
        self.dash_pix.setStyleSheet("font-size: 11px; color: #64748b;")

        dash_layout.addWidget(QLabel("계정:"))
        dash_layout.addWidget(self.account_combo)
        dash_layout.addSpacing(10)
        dash_layout.addWidget(self.dash_posts)
        dash_layout.addWidget(self.dash_remaining)
        dash_layout.addStretch()
        dash_layout.addWidget(self.dash_ai)
        dash_layout.addWidget(self.dash_pix)
        right_layout.addWidget(dash)

        self._update_dashboard()

        # 로그 헤더
        log_hdr = QWidget()
        log_hdr_layout = QHBoxLayout(log_hdr)
        log_hdr_layout.setContentsMargins(0, 0, 0, 0)

        self.indicator = QLabel("●")
        self.indicator.setStyleSheet("color: #22c55e; font-size: 14px;")
        log_hdr_layout.addWidget(self.indicator)

        lbl = QLabel("실행 로그")
        lbl.setObjectName("logHeader")
        log_hdr_layout.addWidget(lbl)
        log_hdr_layout.addStretch()

        self.status_label = QLabel("준비")
        self.status_label.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 12px;")
        log_hdr_layout.addWidget(self.status_label)

        right_layout.addWidget(log_hdr)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        right_layout.addWidget(self.log_text)

        main_layout.addWidget(right, stretch=1)
        root_layout.addWidget(main_widget, stretch=1)

    def _add_divider(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e2e8f0;")
        layout.addWidget(line)
        layout.addSpacing(5)

    # ── 대시보드 ──
    def _update_dashboard(self):
        cfg = load_config()
        provider = cfg.get("ai_provider", "gemini").lower()
        info = get_remaining(provider)
        self.dash_posts.setText(f"오늘 작성: {info['posts_today']}개")
        self.dash_remaining.setText(f"작성 가능: {info['posts_remaining']}개")
        color = "#22c55e" if info['posts_remaining'] > 50 else "#f59e0b" if info['posts_remaining'] > 10 else "#ef4444"
        self.dash_remaining.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {color};")
        self.dash_ai.setText(f"AI: {info['ai_used']}/{info['ai_limit']}")
        self.dash_pix.setText(f"Pixabay: {info['pix_used']}/{info['pix_limit']}")

    # ── 로그 ──
    def _emit_log(self, msg):
        self.log_signal.emit(msg)

    def _append_log(self, msg):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"<span style='color:#9ca3af'>[{now}]</span>  {msg}")
        self.log_text.moveCursor(QTextCursor.End)

    def _emit_status(self, text, color="#22c55e"):
        self.status_signal.emit(text, color)

    def _update_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        self.indicator.setStyleSheet(f"color: {color}; font-size: 14px;")

    def _get_interval_seconds(self):
        return int(self.interval_hour.currentText()) * 3600 + int(self.interval_min.currentText()) * 60

    # ── 계정 선택 ──
    def _refresh_account_combo(self):
        accounts = self.cfg.get("accounts", [])
        active = self.cfg.get("active_account", 0)
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        for i in range(9):
            acc = accounts[i] if i < len(accounts) else {}
            bid = (acc.get("blog_id") or "").strip()
            label = f"{i+1}. {bid}" if bid else f"{i+1}. (미설정)"
            self.account_combo.addItem(label)
        if 0 <= active < self.account_combo.count():
            self.account_combo.setCurrentIndex(active)
        self.account_combo.blockSignals(False)

    def _on_account_changed(self, idx):
        if idx < 0:
            return
        cfg = load_config()
        cfg["active_account"] = idx
        save_config(cfg)
        self.cfg = cfg
        # 계정 전환 시 메모리 상태 초기화 (크롤/생성 데이터는 계정별 파일에서 다시 로드됨)
        self.crawled_data = []
        self._generated_posts = []
        self.result_file = ""
        self.keyword_input.clear()
        self._load_keyword_history()
        bid = cfg.get('accounts', [{}])[idx].get('blog_id', '') or '(미설정)'
        self._emit_log(f"계정 전환: {idx+1}번 ({bid})")

    def _current_blog_id(self) -> str:
        try:
            idx = self.cfg.get("active_account", 0)
            return self.cfg.get("accounts", [])[idx].get("blog_id", "") or f"acc{idx}"
        except Exception:
            return "default"

    # ── 키워드 히스토리 (엑셀 저장, 계정별) ──
    def _get_history_file(self):
        bid = self._current_blog_id() or "default"
        safe = "".join(c for c in bid if c.isalnum() or c in "-_") or "default"
        return os.path.join(os.path.dirname(__file__), f"search_history_{safe}.xlsx")

    def _load_keyword_history(self):
        import openpyxl
        filepath = self._get_history_file()
        try:
            wb = openpyxl.load_workbook(filepath)
            ws = wb.active
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0]:
                    self.keyword_input.addItem(str(row[0]))
            wb.close()
        except Exception:
            pass
        # 입력칸은 비우고 드롭다운에만 히스토리 유지
        self.keyword_input.setCurrentText("")

    def _save_keyword_history(self, keyword: str):
        import openpyxl
        filepath = self._get_history_file()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            wb = openpyxl.load_workbook(filepath)
            ws = wb.active
        except Exception:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "검색 히스토리"
            ws.append(["키워드", "검색일시", "수집 결과수"])

        ws.append([keyword, now, ""])
        wb.save(filepath)
        wb.close()

        # 드롭다운 갱신 (중복 제거)
        existing = set()
        items = []
        for i in range(self.keyword_input.count()):
            items.append(self.keyword_input.itemText(i))
            existing.add(self.keyword_input.itemText(i))
        if keyword not in existing:
            self.keyword_input.insertItem(0, keyword)
        self.keyword_input.setCurrentText(keyword)

    def _update_history_result_count(self, keyword: str, count: int):
        import openpyxl
        filepath = self._get_history_file()
        try:
            wb = openpyxl.load_workbook(filepath)
            ws = wb.active
            # 마지막 행에서 해당 키워드 찾아서 결과수 업데이트
            for row in reversed(list(ws.iter_rows(min_row=2))):
                if row[0].value == keyword and not row[2].value:
                    row[2].value = count
                    break
            wb.save(filepath)
            wb.close()
        except Exception:
            pass

    # ── 관리자 메뉴 ──
    def _open_admin_dialog(self):
        dlg = AdminDialog(self)
        dlg.exec()

    def apply_user_session(self, user: dict):
        """로그인 성공 후 호출 — 역할에 따라 관리자 버튼 노출"""
        self.current_user = user
        try:
            self.btn_admin.setVisible(user.get("role") == "admin")
        except Exception:
            pass

    # ── 설정 ──
    def _open_settings(self):
        from settings_dialog import SettingsDialog
        cu = getattr(self, "current_user", {}) or {}
        is_admin = cu.get("role") == "admin"
        username = cu.get("username", "admin")
        dlg = SettingsDialog(self, is_admin=is_admin, app_user=username)
        dlg.exec()
        self.cfg = load_config()
        self._refresh_account_combo()

    # ── 한영 번역 캐시 (Pixabay 검색어용) ──
    def _get_translation_cache_file(self):
        return os.path.join(os.path.dirname(__file__), "translation_cache.json")

    def _load_translation_cache(self) -> dict:
        fp = self._get_translation_cache_file()
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_translation_cache(self, cache: dict):
        fp = self._get_translation_cache_file()
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _translate_ko_to_en(self, text: str) -> str:
        """한글 검색어를 영어로 번역 (AI 사용, 결과 캐싱)"""
        text = (text or "").strip()
        if not text:
            return ""
        # 이미 영어면 그대로
        if not any(0xAC00 <= ord(c) <= 0xD7A3 for c in text):
            return text
        cache = self._load_translation_cache()
        if text in cache:
            return cache[text]
        # AI로 번역
        try:
            cfg = self.cfg
            provider = cfg.get("ai_provider", "Gemini")
            key_list_name = "gemini_key_list" if provider == "Gemini" else "gpt_key_list"
            api_keys = [k for k in cfg.get(key_list_name, []) if k]
            if not api_keys:
                return text
            prompt = (
                f"Translate this Korean search term to a concise English keyword (max 3 words) suitable for Pixabay image search. "
                f"Output ONLY the English term, no explanation, no quotes.\n\n"
                f"Korean: {text}\nEnglish:"
            )
            if provider == "Gemini":
                import google.generativeai as genai
                genai.configure(api_key=api_keys[0])
                model = genai.GenerativeModel("gemini-2.0-flash-exp")
                resp = model.generate_content(prompt)
                en = (resp.text or "").strip()
            else:
                from openai import OpenAI
                client = OpenAI(api_key=api_keys[0])
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=20,
                )
                en = (resp.choices[0].message.content or "").strip()
            # 정제: 따옴표/마침표 제거, 한 줄로
            en = en.split("\n")[0].strip().strip('"\'`.')
            if en:
                cache[text] = en
                self._save_translation_cache(cache)
                return en
        except Exception as _e:
            self._emit_log(f"번역 실패 ('{text}'): {_e}")
        return text

    # ── 프롬프트 편집 ──
    def _open_prompt_editor(self):
        prompts_path = os.path.join(os.path.dirname(__file__), "prompts.json")
        try:
            with open(prompts_path, "r", encoding="utf-8") as f:
                prompts = json.load(f)
        except Exception:
            prompts = {}
        if not prompts:
            prompts = {"기본": {"blog": "", "title": ""}}

        dlg = QDialog(self)
        dlg.setWindowTitle("프롬프트 편집")
        dlg.resize(900, 700)
        layout = QVBoxLayout(dlg)

        top = QHBoxLayout()
        top.addWidget(QLabel("업종 선택:"))
        type_combo = QComboBox()
        type_combo.addItems(list(prompts.keys()))
        top.addWidget(type_combo, 1)

        btn_add = QPushButton("+ 업종 추가")
        btn_auto = QPushButton("AI 자동 생성")
        btn_auto.setStyleSheet("background: #22c55e; color: white; border-radius: 6px; padding: 4px 10px;")
        btn_del = QPushButton("삭제")
        btn_del.setStyleSheet("background: #ef4444; color: white; border-radius: 6px; padding: 4px 10px;")
        top.addWidget(btn_add)
        top.addWidget(btn_auto)
        top.addWidget(btn_del)
        layout.addLayout(top)

        layout.addWidget(QLabel("블로그 본문 프롬프트:"))
        blog_edit = QTextEdit()
        blog_edit.setAcceptRichText(False)
        layout.addWidget(blog_edit, 3)

        layout.addWidget(QLabel("제목 프롬프트:"))
        title_edit = QTextEdit()
        title_edit.setAcceptRichText(False)
        layout.addWidget(title_edit, 1)

        # 제목 키워드 형식 선택 (업종별)
        prefix_row = QHBoxLayout()
        prefix_row.addWidget(QLabel("제목 키워드 형식:"))
        prefix_combo = QComboBox()
        prefix_combo.addItems(["XX동 + 업종", "XX역 + 업종", "XX구 + 업종"])
        prefix_row.addWidget(prefix_combo, 1)
        layout.addLayout(prefix_row)

        # Pixabay 검색어 입력 (3개 슬롯, 생성 시 랜덤 선택 / 전부 비면 자동)
        pix_row = QHBoxLayout()
        pix_row.addWidget(QLabel("Pixabay 검색어 (1/2/3 중 랜덤):"))
        pix_edit = QLineEdit()
        pix_edit.setPlaceholderText("1번 (예: fitness)")
        pix_edit2 = QLineEdit()
        pix_edit2.setPlaceholderText("2번 (예: workout)")
        pix_edit3 = QLineEdit()
        pix_edit3.setPlaceholderText("3번 (예: dumbbell)")
        pix_row.addWidget(pix_edit, 1)
        pix_row.addWidget(pix_edit2, 1)
        pix_row.addWidget(pix_edit3, 1)
        layout.addLayout(pix_row)

        current = {"key": type_combo.currentText()}

        def load_current():
            key = type_combo.currentText()
            data = prompts.get(key, {"blog": "", "title": "", "pixabay_list": []})
            blog_edit.blockSignals(True); title_edit.blockSignals(True)
            pix_edit.blockSignals(True); pix_edit2.blockSignals(True); pix_edit3.blockSignals(True)
            blog_edit.setPlainText(data.get("blog", ""))
            title_edit.setPlainText(data.get("title", ""))
            # 제목 키워드 형식
            tp = (data.get("title_prefix") or "dong").strip().lower()
            if tp == "station":
                prefix_combo.setCurrentIndex(1)
            elif tp == "gu":
                prefix_combo.setCurrentIndex(2)
            else:
                prefix_combo.setCurrentIndex(0)
            # 구버전 호환: pixabay (단일) + pixabay_list (3개) 둘 다 지원
            pix_list = data.get("pixabay_list") or []
            if not pix_list and data.get("pixabay"):
                pix_list = [data.get("pixabay", "")]
            pix_list = (pix_list + ["", "", ""])[:3]
            pix_edit.setText(pix_list[0])
            pix_edit2.setText(pix_list[1])
            pix_edit3.setText(pix_list[2])
            blog_edit.blockSignals(False); title_edit.blockSignals(False)
            pix_edit.blockSignals(False); pix_edit2.blockSignals(False); pix_edit3.blockSignals(False)
            current["key"] = key

        def save_current_to_memory():
            if current["key"] in prompts:
                _tp_map = {0: "dong", 1: "station", 2: "gu"}
                prompts[current["key"]] = {
                    "blog": blog_edit.toPlainText(),
                    "title": title_edit.toPlainText(),
                    "title_prefix": _tp_map.get(prefix_combo.currentIndex(), "dong"),
                    "pixabay_list": [pix_edit.text().strip(), pix_edit2.text().strip(), pix_edit3.text().strip()],
                }

        def on_type_changed():
            save_current_to_memory()
            load_current()

        type_combo.currentIndexChanged.connect(lambda _i: on_type_changed())

        def add_type():
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(dlg, "업종 추가", "업종명:")
            name = (name or "").strip()
            if ok and name and name not in prompts:
                save_current_to_memory()
                prompts[name] = {"blog": "", "title": "", "pixabay_list": ["", "", ""]}
                type_combo.addItem(name)
                type_combo.setCurrentText(name)

        def del_type():
            key = type_combo.currentText()
            if not key:
                return
            if len(prompts) <= 1:
                QMessageBox.warning(dlg, "경고", "최소 1개는 남겨야 합니다.")
                return
            if QMessageBox.question(dlg, "확인", f"'{key}' 업종을 삭제할까요?") != QMessageBox.Yes:
                return
            prompts.pop(key, None)
            type_combo.removeItem(type_combo.currentIndex())
            load_current()

        # AI 응답 수신 시그널 (워커 스레드에서 GUI로 전달)
        class _AISignal(QObject):
            done = Signal(str, str)  # text, error
        ai_sig = _AISignal()

        def _on_ai_done(text, error):
            btn_auto.setEnabled(True)
            btn_auto.setText("AI 자동 생성")
            if error:
                QMessageBox.critical(dlg, "오류", f"AI 호출 실패: {error}")
                return
            import re
            m_blog = re.search(r"===\s*BLOG\s*===\s*(.*?)\s*===\s*TITLE\s*===", text, re.S)
            m_title = re.search(r"===\s*TITLE\s*===\s*(.*)", text, re.S)
            blog_p = (m_blog.group(1).strip() if m_blog else "")
            title_p = (m_title.group(1).strip() if m_title else "")
            if not blog_p and not title_p:
                QMessageBox.warning(dlg, "경고", f"응답 파싱 실패. 전체 응답:\n{text[:500]}")
                return
            if blog_p:
                blog_edit.setPlainText(blog_p)
            if title_p:
                title_edit.setPlainText(title_p)
            QMessageBox.information(dlg, "완료", "프롬프트 자동 생성 완료. 확인 후 '저장'을 눌러주세요.")

        ai_sig.done.connect(_on_ai_done)

        def auto_generate():
            key = type_combo.currentText()
            if not key:
                return
            cfg2 = load_config()
            provider = cfg2.get("ai_provider", "Gemini")
            key_list_name = "gemini_key_list" if provider == "Gemini" else "gpt_key_list"
            api_keys = [k for k in cfg2.get(key_list_name, []) if k]
            if not api_keys:
                QMessageBox.critical(dlg, "오류", f"{provider} API 키를 설정해주세요.")
                return
            base = prompts.get("기본", {"blog": "", "title": ""})
            ref_example = """# 역할
너는 부모님을 직접 모시지 못한다는 무거운 마음을 안고 수개월간 요양원을 찾아 헤맸던 **'현실적인 효자/효녀 블로거'**다. 단순한 정보 나열이 아니라, 같은 처지에 놓인 자녀들이 밤잠 설치며 고민하는 지점을 정확히 짚어주고, 그들의 죄책감을 덜어주면서도 **'전문적인 사람'**으로서의 선택임을 강조하는 따뜻한 조언자다
글은 광고 느낌이 아니라, 실제로 부모님을 맡길 요양원을 고르면서 고민했던 사람이 지인에게 조용히 털어놓는 이야기처럼 진심 있게 작성한다.
기본은 존댓말을 사용하고, **1인칭(저, 우리 가족)** 을 자연스럽게 사용해도 된다.
※ 이 프롬프트에서 가장 중요한 규칙은 **'분량'과 '문장 수'**이다. 다른 어떤 규칙보다 **글자 수·문장 수 조건을 우선해서** 지킨다. 글이 짧다고 느껴지면, 이미 쓴 내용을 더 구체적인 장면·감정·예시로 풀어 써서라도 분량을 반드시 채운다.

# 작업 지시
아래에 제공된 '입력 데이터'를 활용하여 **부모님 요양원 선택 과정과 실제 이용 후기**를 블로그 본문 형식으로 작성한다.
* 전체 글자 수는 한글 기준 **공백 포함 1500자 안팎**으로 맞춘다.
* **1450자 이상 1650자 이하** 범위에서 작성하고, **1400자 미만이 되지 않도록** 충분히 내용을 확장한다.
글의 전체적인 흐름은 다음 구조를 따른다.
1. **서론** — 방문 계기/동기, 처음의 감정(죄책감·불안 등)
2. **본론** — 검색·상담·방문 과정 / 비교 기준 / 최종 선택 요양원의 위치·접근성 / 시설·프로그램·돌봄 환경 / 부모님의 변화, 가족의 심리 변화
3. **결론** — 만족도·느낀 점 / "나도 이렇게 선택했다" 식의 부드러운 상담/방문 권유

# 입력 데이터
* 요양원명(업체명): {업체명}
* 주소: {주소}
* 근처역/교통: {근처역}
* 카테고리: {카테고리}
* 앞 키워드: {앞키워드}
* 태그: {태그}
(앞 키워드와 태그는 글의 주제와 분위기를 파악하기 위한 참고용이다.)

# 준수 사항
## 1. 형식 및 문장 구성
* **문장마다 줄바꿈**한다. 한 문장은 한 줄, 문장 끝마다 줄바꿈.
* 서론 → 본론 → 결론 흐름에 맞춰 배치한다.
* 전체 문장 수는 **최소 40문장 이상**.
* 각 문장은 너무 짧지 않게, **대략 25자 이상**이 되도록 상황·감정·설명을 충분히 풀어 쓴다.

## 2. 분량
* 공백 포함 1500자 안팎(1450~1650자). 1400자 미만 금지.
* 부족하면 구체적 예시·상황·대화·표정·몸짓 묘사로 늘린다.

## 3. 내용 구성 (각 파트 최소 문장 수)
1) 서론 — 처음 상황과 감정 (최소 8문장)
2) 검색·상담·방문 과정 (최소 10문장, 실제 상담 질문 3가지 이상 풀어쓰기)
3) 여러 곳 비교 + 최종 선택 기준 (최소 7문장)
4) 위치·접근성·주변 환경 (최소 5문장)
5) 시설·프로그램·돌봄 세부 묘사 (최소 8문장)
6) 부모님 변화·가족 심리 변화 (최소 6문장, 시간 흐름 단계적 서술)
7) 장점/아쉬운 점 + 결론 (최소 8문장)

## 4. 어조
* 일상 대화체 + 진심 담은 후기체.
* "솔직히 처음에는…", "막상 다녀와 보니까…" 같은 표현 적절히.
* 자극·과장 없이 담담하지만 진심 있는 톤.

## 5. 금지 사항
* 이모티콘 금지.
* '카테고리', '앞 키워드', '태그'라는 단어 본문 언급 금지.
* **광고·홍보·이벤트·할인·"무조건 여기로 오세요" 식 문구 절대 금지.**
* 가격·비용·금액 구체 언급 금지(간접 언급만 가능).

## 6. 정보 출처 표현
* '크롤링', '검색 엔진', '데이터 수집' 같은 단어 본문 사용 금지.
* 본인이 직접 상담·방문해서 느낀 후기처럼 자연스럽게 표현.

## 이미지 배치
* 본문 흐름상 사진이 들어가면 좋을 위치에 '[이미지]' 마커를 해당 줄 단독으로 2~4개 삽입.
"""
            ref_title = """# 역할
너는 대한민국의 블로그 포스팅 전문가다. 너의 임무는 주어진 키워드에 대해 사용자의 클릭을 유발하는 매력적인 블로그 제목의 '마무리 문구'를 생성하는 것이다.

# 작업 설명
1. '핵심 키워드'의 특성을 분석한다.
2. 분석한 내용을 바탕으로, 블로그 제목의 마지막 부분에 위치할 '마무리 문구'를 생성한다.
3. 생성되는 문구는 아래 '카테고리'를 참고하여 다양하게 구성한다.
4. 최종 결과물은 리스트 형태로, '마무리 문구'만 간결하게 제공한다.

# 블로그 제목 구조
[핵심 키워드] + [업체명] + [생성된 마무리 문구]

# 카테고리
- 정보성: 가격, 위치, 영업시간, 주차, 예약 방법 등 사실 정보
- 장점 및 특징: 시설, 전문성, 특별한 메뉴나 서비스, 분위기
- 경험 및 후기: 솔직 후기, 내돈내산, 방문 경험, 추천 이유
- 질문 및 호기심 유발: ~방법?, ~후기, ~꿀팁, ~총정리

# 예시
- 핵심 키워드: "강남역 파스타 맛집"
- 결과물 예시:
  데이트 코스로 강력 추천
  내돈내산 솔직 후기
  메뉴와 가격 총정리
  웨이팅 없이 즐기는 꿀팁
  분위기 좋은 곳 찾는다면


# 지시
아래 '핵심 키워드'에 대한 '마무리 문구' 10개를 생성해라.
마무리 문구는 20자 이내, 지역명/구/동/역/업종명/업체명은 절대 포함하지 않는다.
숫자나 번호 없이 한 줄씩 10개.

핵심 키워드: {키워드}
"""
            meta_prompt = (
                f"아래는 블로그 방문 후기 자동 생성용 프롬프트 템플릿을 만드는 작업이다.\n"
                f"'{key}' 업종에 맞는 **블로그 본문 프롬프트**와 **제목 프롬프트**를 생성한다.\n\n"
                f"★★ 절대 규칙 ★★\n"
                f"1) '{{업종}}', '{{업체명}}', '{{주소}}', '{{근처역}}', '{{카테고리}}', '{{앞키워드}}', '{{태그}}', '{{키워드}}' 같은 "
                f"중괄호 플레이스홀더는 반드시 그대로 유지한다 (한글명이든 영문이든 기존 그대로).\n"
                f"2) **그 시설을 검색해서 방문할 만한 사람의 관점·페르소나**로 후기를 쓰도록 프롬프트를 구성한다.\n"
                f"   - 예: 헬스장 → 운동하러 가려는 본인 입장 (체력/근력/감량 목표, 첫 등록 고민, 운동 초보 관점 등)\n"
                f"   - 예: 요양원/요양센터/요양병원 → 부모님/가족을 모시려는 자녀 입장 (시설 안전, 직원 태도, 어르신 편의, 면회 환경)\n"
                f"   - 예: 학원 → 자녀 보낼 학부모 또는 본인 수강생 입장\n"
                f"   - 예: 병원/치과 → 본인이나 가족 진료 받으러 간 입장\n"
                f"   - 예: 카페/식당 → 방문해서 먹고 즐긴 본인 입장\n"
                f"   - 예: 미용실/네일 → 서비스 받으러 간 본인 입장\n"
                f"   - 예: 산후조리원 → 출산한 본인 또는 배우자 입장\n"
                f"3) 기본 템플릿이 가진 제약(사실 기반 작성 / 지어내기 금지 / 이모티콘 금지 등)은 유지한다.\n\n"
                f"★ 아래 '참고 스타일(요양원 예시)'의 구조·디테일 수준·섹션 구성·최소 문장 수 형식을 그대로 본떠라.\n"
                f"단, 요양원 고유의 고민(부모님 모시기 죄책감 등)은 '{key}' 업종의 고민/기대 포인트로 **전면 교체**한다.\n"
                f"분량 기준(공백 포함 1500자 안팎, 1400자 미만 금지, 최소 40문장)은 그대로 유지한다.\n\n"
                f"=== 참고 스타일 — 본문 (요양원 예시) ===\n{ref_example}\n\n"
                f"=== 참고 스타일 — 제목 (공통 템플릿) ===\n{ref_title}\n"
                f"★ 제목 프롬프트는 위 템플릿의 구조·섹션·카테고리 4종 설명·지시를 **그대로 유지**한다.\n"
                f"★ 단, '# 예시' 섹션의 '핵심 키워드'만 '{key}' 업종에 맞는 대표 키워드(예: 헬스장이면 '강서구 헬스장', 요양원이면 '은평구 요양원')로 바꾸고,\n"
                f"   '결과물 예시'의 5개 문구도 '{key}' 업종 검색자가 클릭할 만한 마무리 문구로 자연스럽게 교체한다.\n"
                f"★ 단, 예시로 쓰는 5개 문구에도 **지역명/구/동/역이름/업종명({key})/업체명은 절대 포함하지 않는다.** "
                f"예: 헬스장용 예시에 '헬스장'이라는 단어가 들어가면 안 됨. '운동', '다닐 곳', '다녀봤어요' 같은 간접 표현으로.\n"
                f"★ 출력은 '프롬프트 템플릿'이지 10개 문구 자체가 아니다. '핵심 키워드: {{키워드}}' 플레이스홀더는 그대로 둘 것.\n\n"
                f"=== 기존 기본 템플릿 (필요 제약 참고용) ===\n[BLOG]\n{base.get('blog','')}\n\n[TITLE]\n{base.get('title','')}\n\n"
                f"=== 출력 형식 (반드시 이 구분자 사용) ===\n"
                f"===BLOG===\n(여기에 '{key}' 업종용 블로그 본문 프롬프트 전문)\n"
                f"===TITLE===\n(여기에 '{key}' 업종용 제목 프롬프트 전문 — 위 제목 공통 골격 유지)\n"
            )

            btn_auto.setEnabled(False)
            btn_auto.setText("생성 중...")

            def _worker():
                try:
                    if provider == "Gemini":
                        import google.generativeai as genai
                        genai.configure(api_key=api_keys[0])
                        model = genai.GenerativeModel("gemini-2.0-flash-exp")
                        resp = model.generate_content(meta_prompt)
                        text = resp.text or ""
                    else:
                        from openai import OpenAI
                        client = OpenAI(api_key=api_keys[0])
                        resp = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": meta_prompt}],
                        )
                        text = resp.choices[0].message.content or ""
                    ai_sig.done.emit(text, "")
                except Exception as e:
                    ai_sig.done.emit("", str(e))

            threading.Thread(target=_worker, daemon=True).start()

        btn_add.clicked.connect(add_type)
        btn_auto.clicked.connect(auto_generate)
        btn_del.clicked.connect(del_type)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = QPushButton("저장")
        btn_save.setStyleSheet("background: #4a6cf7; color: white; border-radius: 8px; padding: 8px 20px; font-weight: bold;")
        btn_cancel = QPushButton("취소")
        btn_cancel.setStyleSheet("padding: 8px 20px;")
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        def do_save():
            save_current_to_memory()
            try:
                with open(prompts_path, "w", encoding="utf-8") as f:
                    json.dump(prompts, f, ensure_ascii=False, indent=2)
                QMessageBox.information(dlg, "완료", "프롬프트를 저장했습니다.")
                dlg.accept()
            except Exception as e:
                QMessageBox.critical(dlg, "오류", f"저장 실패: {e}")

        btn_save.clicked.connect(do_save)
        btn_cancel.clicked.connect(dlg.reject)

        load_current()
        dlg.exec()

    # ── 크롤링 ──
    def _start_crawl(self):
        keyword = self.keyword_input.currentText().strip()
        if not keyword:
            QMessageBox.warning(self, "경고", "키워드를 입력해주세요.")
            return
        if self.is_crawling:
            return

        self._save_keyword_history(keyword)
        self.last_keyword = keyword
        # 설정에도 저장 (계정별, 재시작해도 유지)
        try:
            _c = load_config()
            _c["last_keyword"] = keyword  # 호환용
            lkm = _c.get("last_keyword_by_account", {}) or {}
            lkm[self._current_blog_id()] = keyword
            _c["last_keyword_by_account"] = lkm
            save_config(_c)
        except Exception:
            pass
        count = self.count_spin.value()
        self.is_crawling = True
        self.stop_flag = False
        self.crawled_data = []

        log_dir = self._get_logs_dir()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.result_file = os.path.join(log_dir, f"places_{timestamp}.json")

        self._emit_status("크롤링 중...", "#f59e0b")
        self._emit_log(f"크롤링 시작: '{keyword}' (검색 지역 일치 항목만 수집)")

        def _worker():
            try:
                def on_progress(current, scanned, name):
                    if self.stop_flag:
                        raise InterruptedError("중단됨")
                    self._emit_log(f"  [수집 {current}개 / 스캔 {scanned}개] {name}")
                    self._emit_status(f"수집 {current}개", "#f59e0b")

                results = crawl_places(keyword, count, on_progress)
                self.crawled_data = results
                save_results(results, self.result_file, keyword)

                self._emit_log(f"크롤링 완료! {len(results)}개 수집")
                self._emit_status("완료", "#22c55e")
                self._update_history_result_count(keyword, len(results))

            except InterruptedError:
                self._emit_log("크롤링 중단됨")
                self._emit_status("중단됨", "#ef4444")
            except Exception as e:
                self._emit_log(f"크롤링 오류: {e}")
                self._emit_status("오류", "#ef4444")
            finally:
                self.is_crawling = False

        threading.Thread(target=_worker, daemon=True).start()

    def _stop(self):
        if self.is_crawling or self.is_posting or getattr(self, 'is_generating', False):
            self.stop_flag = True
            self._emit_log("중단 요청...")

    # ── 결과보기 ──
    def _show_results(self):
        if not self.crawled_data:
            log_dir = self._get_logs_dir()
            if os.path.exists(log_dir):
                files = sorted(
                    [f for f in os.listdir(log_dir) if f.endswith(".json")],
                    reverse=True
                )
                if files:
                    filepath = os.path.join(log_dir, files[0])
                    raw = load_results(filepath)
                    self.crawled_data = raw.get("items", []) if isinstance(raw, dict) else raw
                    self._emit_log(f"결과 불러옴: {files[0]}")

        if not self.crawled_data:
            QMessageBox.information(self, "결과", "크롤링 결과가 없습니다.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"크롤링 결과 — 총 {len(self.crawled_data)}건")
        dlg.resize(1300, 600)

        layout = QVBoxLayout(dlg)
        table = QTableWidget()
        table.verticalHeader().setVisible(False)
        headers = ["인덱스", "업체명", "업체주소", "카테고리", "근처역", "앞 키워드", "태그", "픽사베이 키워드"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(self.crawled_data))

        widths = [50, 160, 250, 130, 160, 200, 140, 200]
        for col, w in enumerate(widths):
            table.setColumnWidth(col, w)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("alternate-background-color: #f5f5f5;")

        for i, p in enumerate(self.crawled_data):
            # 업체주소: 동 주소 + 지번 합침
            addr = p.get("address", "")
            jibun = p.get("jibun_address", "")
            if jibun:
                full_addr = f"{addr} {jibun}" if addr else jibun
            else:
                full_addr = addr

            table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            table.setItem(i, 1, QTableWidgetItem(p.get("name", "")))
            table.setItem(i, 2, QTableWidgetItem(full_addr))
            table.setItem(i, 3, QTableWidgetItem(p.get("category", "")))
            table.setItem(i, 4, QTableWidgetItem(p.get("nearby_station", "")))
            table.setItem(i, 5, QTableWidgetItem(p.get("front_keywords", "")))
            table.setItem(i, 6, QTableWidgetItem(p.get("tags", "")))
            table.setItem(i, 7, QTableWidgetItem(p.get("pixabay_keywords", "")))

        table.setSelectionMode(QTableWidget.ContiguousSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setStyleSheet("""
            alternate-background-color: #f5f5f5;
            selection-background-color: #e0e0e0;
            selection-color: #000000;
        """)

        # 엑셀 복사 버튼 — 인덱스/업체명 헤더 제외, 데이터만 복사
        def copy_to_clipboard():
            rows = table.rowCount()
            cols = table.columnCount()
            lines = []
            for r in range(rows):
                row_data = []
                for c in range(cols):
                    item = table.item(r, c)
                    row_data.append(item.text() if item else "")
                lines.append("\t".join(row_data))
            QApplication.clipboard().setText("\n".join(lines))
            QMessageBox.information(dlg, "복사 완료", "엑셀에 붙여넣기(Ctrl+V) 하세요.")

        btn_copy = QPushButton("엑셀용 복사")
        btn_copy.setStyleSheet("background: #4a6cf7; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; padding: 10px;")
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.clicked.connect(copy_to_clipboard)

        layout.addWidget(table)
        layout.addWidget(btn_copy)
        dlg.exec()

    # ── 생성된 포스트 보기 (크롤 업체 목록 + 생성여부 표시) ──
    def _view_generated_posts(self):
        # 저장된 포스트 로드 + 삭제된 키 필터
        _deleted = self._load_deleted_keys()
        posts = [p for p in self._load_generated_posts() if self._place_key(p.get("place", {})) not in _deleted]
        self._generated_posts = posts

        # (업체명+주소) → content 매핑
        post_map = {}
        for p in posts:
            pl = p.get("place", {})
            key = (pl.get("name", ""), pl.get("address", "") or pl.get("jibun_address", ""))
            post_map[key] = p

        # 크롤 결과 로드 (포스팅 업체 선택과 동일)
        all_groups = self._load_all_crawl_results()
        if self.crawled_data:
            all_groups["현재 크롤링 결과 (" + str(len(self.crawled_data)) + "개)"] = self.crawled_data

        if not all_groups and not posts:
            QMessageBox.information(self, "결과", "크롤링/생성된 포스트가 없습니다.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("생성된 포스트 보기")
        dlg.resize(1000, 650)
        layout = QVBoxLayout(dlg)

        # 상단: 전체 선택/해제
        top_row = QHBoxLayout()
        btn_all_sel = QPushButton("전체 선택")
        btn_all_sel.setStyleSheet("padding: 6px 15px;")
        btn_all_none = QPushButton("전체 해제")
        btn_all_none.setStyleSheet("padding: 6px 15px;")
        top_row.addWidget(btn_all_sel)
        top_row.addWidget(btn_all_none)
        top_row.addStretch()
        layout.addLayout(top_row)

        info = QLabel("● 초록: 생성됨 (더블클릭해서 내용 확인 / 체크 후 삭제 가능)  ● 빨강: 미생성")
        info.setStyleSheet("font-size: 12px; color: #475569; padding: 5px;")
        layout.addWidget(info)

        tree = QTreeWidget()
        tree.setHeaderLabels(["업체명", "업체주소", "카테고리", "근처역", "앞 키워드", "태그"])
        tree.setColumnWidth(0, 260)
        tree.setColumnWidth(1, 240)
        tree.setColumnWidth(2, 100)
        tree.setColumnWidth(3, 100)
        tree.setColumnWidth(4, 160)
        tree.setAlternatingRowColors(True)

        # 더블클릭 시 포스트 내용 보기를 위한 매핑
        item_to_post = {}
        all_children = []  # (child_item, place) — 전체 선택/삭제용

        for group_name, places in all_groups.items():
            # 삭제된 키 필터
            places = [p for p in places if self._place_key(p) not in _deleted]
            if not places:
                continue
            parent = QTreeWidgetItem(tree)
            parent.setText(0, group_name)
            parent.setFlags(parent.flags() | Qt.ItemIsUserCheckable)
            parent.setCheckState(0, Qt.Unchecked)
            parent.setExpanded(False)

            gen_count = 0
            for p in places:
                addr = p.get("address", "")
                jibun = p.get("jibun_address", "")
                full_addr = f"{addr} {jibun}" if addr and jibun else (jibun or addr)

                key = (p.get("name", ""), p.get("address", "") or p.get("jibun_address", ""))
                generated_post = post_map.get(key)

                child = QTreeWidgetItem(parent)
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked)
                is_posted = bool(generated_post and generated_post.get("posted", False))
                if is_posted:
                    child.setText(0, "[완] " + p.get("name", ""))
                    child.setForeground(0, QColor("#3b82f6"))
                    gen_count += 1
                    item_to_post[id(child)] = generated_post
                elif generated_post:
                    child.setText(0, "●  " + p.get("name", ""))
                    child.setForeground(0, QColor("#22c55e"))
                    gen_count += 1
                    item_to_post[id(child)] = generated_post
                else:
                    child.setText(0, "●  " + p.get("name", ""))
                    child.setForeground(0, QColor("#ef4444"))
                child.setText(1, full_addr)
                child.setText(2, p.get("category", ""))
                child.setText(3, p.get("nearby_station", ""))
                child.setText(4, p.get("front_keywords", ""))
                child.setText(5, p.get("tags", ""))
                all_children.append((child, p))

            # 폴더 색
            if len(places) > 0:
                if gen_count == len(places):
                    parent.setForeground(0, QColor("#22c55e"))
                elif gen_count == 0:
                    parent.setForeground(0, QColor("#ef4444"))
                else:
                    parent.setForeground(0, QColor("#f59e0b"))
                parent.setText(0, f"●  {group_name}  ({gen_count}/{len(places)} 생성)")

        layout.addWidget(tree)

        def on_double_click(item, col):
            post = item_to_post.get(id(item))
            if not post:
                return
            self._show_single_post_view(post)

        tree.itemDoubleClicked.connect(on_double_click)

        # 부모 체크 시 하위 전체 토글
        def on_item_changed(item, col):
            if col != 0:
                return
            tree.blockSignals(True)
            state = item.checkState(0)
            if item.childCount() > 0:
                for i in range(item.childCount()):
                    item.child(i).setCheckState(0, state)
            tree.blockSignals(False)

        tree.itemChanged.connect(on_item_changed)

        def delete_selected():
            # F8 선택 삭제: 업체 + 생성된 포스트 모두 제거 (크롤링 목록에서도 사라짐)
            checked_places = [p for (c, p) in all_children if c.checkState(0) == Qt.Checked]
            if not checked_places:
                QMessageBox.information(dlg, "안내", "선택된 항목이 없습니다.")
                return
            reply = QMessageBox.question(dlg, "삭제 확인", f"{len(checked_places)}개 항목을 완전 삭제할까요?\n(업체 + 생성된 포스트 모두 제거, F7에서도 사라짐)")
            if reply != QMessageBox.Yes:
                return
            deleted = self._load_deleted_keys()
            keys = {self._place_key(p) for p in checked_places}
            deleted.update(keys)
            self._save_deleted_keys(deleted)
            self._generated_posts = [gp for gp in self._generated_posts if self._place_key(gp.get("place", {})) not in keys]
            self._save_generated_posts()
            QMessageBox.information(dlg, "완료", f"{len(checked_places)}개 완전 삭제됨.")
            dlg.accept()

        def delete_all():
            # F8 전체 삭제: 표시된 모든 항목(업체+포스트) 완전 제거
            all_places = [p for (_c, p) in all_children]
            if not all_places:
                return
            reply = QMessageBox.question(dlg, "전체 삭제 확인", f"표시된 전체 {len(all_places)}개 항목을 완전 삭제할까요?\n(업체 + 생성된 포스트 모두 제거)")
            if reply != QMessageBox.Yes:
                return
            deleted = self._load_deleted_keys()
            keys = {self._place_key(p) for p in all_places}
            deleted.update(keys)
            self._save_deleted_keys(deleted)
            self._generated_posts = [gp for gp in self._generated_posts if self._place_key(gp.get("place", {})) not in keys]
            self._save_generated_posts()
            QMessageBox.information(dlg, "완료", f"{len(all_places)}개 완전 삭제됨.")
            dlg.accept()

        def select_all_f8():
            tree.blockSignals(True)
            for i in range(tree.topLevelItemCount()):
                p = tree.topLevelItem(i)
                p.setCheckState(0, Qt.Checked)
                for j in range(p.childCount()):
                    p.child(j).setCheckState(0, Qt.Checked)
            tree.blockSignals(False)

        def select_none_f8():
            tree.blockSignals(True)
            for i in range(tree.topLevelItemCount()):
                p = tree.topLevelItem(i)
                p.setCheckState(0, Qt.Unchecked)
                for j in range(p.childCount()):
                    p.child(j).setCheckState(0, Qt.Unchecked)
            tree.blockSignals(False)

        btn_all_sel.clicked.connect(select_all_f8)
        btn_all_none.clicked.connect(select_none_f8)

        # 첫 포스팅 즉시/대기 옵션
        opt_row = QHBoxLayout()
        first_immediate_cb = QCheckBox("첫 포스팅을 지금 바로 시작 (체크 해제 시 설정 간격만큼 대기 후 시작)")
        first_immediate_cb.setChecked(True)
        first_immediate_cb.setStyleSheet("font-size: 12px; color: #334155;")
        opt_row.addWidget(first_immediate_cb)
        opt_row.addStretch()
        layout.addLayout(opt_row)

        def post_selected():
            targets = []
            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                for j in range(parent.childCount()):
                    child = parent.child(j)
                    if child.checkState(0) == Qt.Checked:
                        post = item_to_post.get(id(child))
                        if post:
                            targets.append(post)
            if not targets:
                QMessageBox.information(dlg, "안내", "포스팅할 생성된 포스트를 선택해주세요.")
                return
            self.posting_targets = targets
            self.first_post_immediate = first_immediate_cb.isChecked()
            dlg.accept()
            self._post_generated()

        btn_row = QHBoxLayout()
        btn_delete = QPushButton("선택 삭제")
        btn_delete.setStyleSheet("background: #ef4444; color: white; border: none; border-radius: 8px; padding: 8px 20px;")
        btn_delete.setCursor(Qt.PointingHandCursor)
        btn_delete.clicked.connect(delete_selected)
        btn_del_all = QPushButton("전체 삭제")
        btn_del_all.setStyleSheet("background: #dc2626; color: white; border: none; border-radius: 8px; padding: 8px 20px;")
        btn_del_all.setCursor(Qt.PointingHandCursor)
        btn_del_all.clicked.connect(delete_all)
        btn_post = QPushButton("자동 포스팅")
        btn_post.setStyleSheet("background: #3b82f6; color: white; border: none; border-radius: 8px; font-weight: bold; padding: 8px 24px;")
        btn_post.setCursor(Qt.PointingHandCursor)
        btn_post.clicked.connect(post_selected)
        btn_close = QPushButton("닫기")
        btn_close.setStyleSheet("padding: 8px 20px;")
        btn_close.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_delete)
        btn_row.addWidget(btn_del_all)
        btn_row.addStretch()
        btn_row.addWidget(btn_post)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        dlg.exec()

    def _show_single_post_view(self, post: dict):
        """단일 포스트 내용 보기"""
        from PySide6.QtWidgets import QTextEdit, QLineEdit
        place = post.get("place", {})
        content = post.get("content", {})

        dlg = QDialog(self)
        dlg.setWindowTitle(place.get("name", "포스트"))
        dlg.resize(900, 700)
        layout = QVBoxLayout(dlg)

        title_edit = QLineEdit(content.get("title", ""))
        title_edit.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;")
        layout.addWidget(title_edit)

        body_edit = QTextEdit()
        body_edit.setPlainText(content.get("body", ""))
        layout.addWidget(body_edit)

        meta = QLabel(
            f"주소: {place.get('address','')} {place.get('jibun_address','')}  |  "
            f"카테고리: {place.get('category','')}  |  "
            f"근처역: {place.get('nearby_station','')}  |  "
            f"태그: {','.join(content.get('tags', [])) if isinstance(content.get('tags'), list) else content.get('tags', '')}"
        )
        meta.setStyleSheet("color: #475569; padding: 5px; font-size: 12px;")
        meta.setWordWrap(True)
        layout.addWidget(meta)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("저장")
        btn_save.setStyleSheet("background: #22c55e; color: white; border: none; border-radius: 6px; padding: 8px 20px;")
        def save():
            content["title"] = title_edit.text()
            content["body"] = body_edit.toPlainText()
            self._save_generated_posts()
            QMessageBox.information(dlg, "저장", "저장되었습니다.")
        btn_save.clicked.connect(save)
        btn_close = QPushButton("닫기")
        btn_close.setStyleSheet("padding: 8px 20px;")
        btn_close.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_save)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        dlg.exec()

    # ── 포스트 생성 ──
    def _account_key(self) -> str:
        bid = self._current_blog_id() or "default"
        return "".join(c for c in bid if c.isalnum() or c in "-_") or "default"

    # ── 삭제된 항목 키 관리 (F7/F8 연동) ──
    def _get_deleted_keys_file(self):
        return os.path.join(os.path.dirname(__file__), f"deleted_keys_{self._account_key()}.json")

    def _load_deleted_keys(self) -> set:
        fp = self._get_deleted_keys_file()
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return set(tuple(x) for x in data)
            except Exception:
                pass
        return set()

    def _save_deleted_keys(self, keys: set):
        fp = self._get_deleted_keys_file()
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump([list(k) for k in keys], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _place_key(self, place: dict) -> tuple:
        return (place.get("name", ""), place.get("address", "") or place.get("jibun_address", ""))

    def _get_posts_file(self):
        # 계정별로 분리 저장
        per_acc = os.path.join(os.path.dirname(__file__), f"generated_posts_{self._account_key()}.json")
        legacy = os.path.join(os.path.dirname(__file__), "generated_posts.json")
        # 최초 전환 시 공용 파일 → 현재 계정 파일로 자동 승격 (1회)
        if not os.path.exists(per_acc) and os.path.exists(legacy):
            try:
                import shutil
                shutil.copyfile(legacy, per_acc)
            except Exception:
                pass
        return per_acc

    def _get_logs_dir(self) -> str:
        d = os.path.join(os.path.dirname(__file__), "logs", self._account_key())
        os.makedirs(d, exist_ok=True)
        return d

    def _migrate_legacy_logs(self):
        """logs/*.json 을 1번 계정 폴더로 1회 이동 (구버전 데이터 복구용)"""
        import shutil
        base = os.path.join(os.path.dirname(__file__), "logs")
        if not os.path.isdir(base):
            return
        legacy = [f for f in os.listdir(base) if f.endswith(".json") and os.path.isfile(os.path.join(base, f))]
        if not legacy:
            return
        accounts = self.cfg.get("accounts", [])
        target_idx = 0
        for i, acc in enumerate(accounts):
            if (acc.get("blog_id") or "").strip():
                target_idx = i
                break
        bid = (accounts[target_idx].get("blog_id") if target_idx < len(accounts) else "") or f"acc{target_idx}"
        safe = "".join(c for c in bid if c.isalnum() or c in "-_") or "default"
        target_dir = os.path.join(base, safe)
        os.makedirs(target_dir, exist_ok=True)
        moved = 0
        for f in legacy:
            src = os.path.join(base, f)
            dst = os.path.join(target_dir, f)
            if os.path.exists(dst):
                continue
            try:
                shutil.move(src, dst)
                moved += 1
            except Exception:
                pass
        if moved:
            self._emit_log(f"기존 크롤 결과 {moved}개를 '{bid}' 계정으로 이동했습니다")

    def _save_generated_posts(self):
        data = []
        for item in self._generated_posts:
            data.append({
                "place": item["place"],
                "content": item["content"],
                "posted": item.get("posted", False),
            })
        with open(self._get_posts_file(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_generated_posts(self) -> list:
        filepath = self._get_posts_file()
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _generate_posts(self):
        # 업체 선택
        selected = self._show_posting_selector()
        if not selected:
            return

        cfg = load_config()
        provider = cfg.get("ai_provider", "Gemini")
        key_list_name = "gemini_key_list" if provider == "Gemini" else "gpt_key_list"
        api_keys = [k for k in cfg.get(key_list_name, []) if k]
        if not api_keys:
            QMessageBox.critical(self, "오류", f"{provider} API 키를 설정해주세요.")
            return

        api_key = api_keys[0]
        _lkm = self.cfg.get("last_keyword_by_account", {}) or {}
        keyword = self.keyword_input.currentText().strip() or getattr(self, 'last_keyword', '') or _lkm.get(self._current_blog_id(), "") or self.cfg.get("last_keyword", "")
        # 크롤된 데이터에서 키워드 자동 복원 (앞키워드 첫 항목이 "{지역}{업종}" 형식)
        if not keyword and selected:
            first = selected[0]
            fk = first.get("front_keywords", "")
            if fk:
                keyword = fk.split(",")[0].strip()
                self._emit_log(f"크롤 데이터에서 키워드 복원: '{keyword}'")
        total = len(selected)

        self._emit_status("포스트 생성 중...", "#8b5cf6")
        self._emit_log(f"포스트 생성 시작: {total}개 업체")

        self._generating_data = {"selected": selected, "keyword": keyword, "api_key": api_key, "provider": provider}
        self._generated_posts = self._load_generated_posts()

        self.is_generating = True
        self.stop_flag = False

        def _worker():
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading
            lock = threading.Lock()
            done_count = [0]
            new_posts = []

            pix_keys = [k for k in cfg.get("pixabay_key_list", []) if k]

            def _gen_one(idx, place):
                if self.stop_flag:
                    return
                name = place.get("name", "")
                try:
                    content = generate_content(
                        provider=provider,
                        api_key=api_key,
                        place=place,
                        keyword=keyword
                    )
                    if self.stop_flag:
                        return

                    # 이미지도 생성 시점에 같이 다운받아 영구 저장
                    img_paths = []
                    if pix_keys:
                        try:
                            biz = (place.get("category") or "").strip() or keyword
                            # 업종별 Pixabay 검색어 오버라이드 (prompts.json 의 pixabay_list 3개 중 랜덤)
                            try:
                                import random as _rnd
                                _pp = os.path.join(os.path.dirname(__file__), "prompts.json")
                                with open(_pp, "r", encoding="utf-8") as _pf:
                                    _prompts = json.load(_pf)
                                _entry = _prompts.get(biz, {}) or {}
                                _plist = _entry.get("pixabay_list") or []
                                if not _plist and _entry.get("pixabay"):
                                    _plist = [_entry.get("pixabay", "")]
                                _plist = [s.strip() for s in _plist if s and s.strip()]
                                if _plist:
                                    _picked = _rnd.choice(_plist)
                                    # 한글이면 영어로 자동 번역
                                    _picked_en = self._translate_ko_to_en(_picked)
                                    if _picked_en != _picked:
                                        self._emit_log(f"Pixabay 검색어 번역: '{_picked}' → '{_picked_en}'")
                                    biz = _picked_en
                                    self._emit_log(f"Pixabay 검색어 선택: '{biz}' (후보 {len(_plist)}개)")
                            except Exception:
                                pass
                            img_count = content.get("image_count", 3)
                            tmp_paths = download_images(pix_keys[0], biz, img_count)
                            # 영구 저장 위치로 이동 (place key별 폴더)
                            pkey = self._place_key(place)
                            safe_name = "".join(c for c in (pkey[0] + "_" + pkey[1]) if c.isalnum() or c in "-_")[:80] or "unknown"
                            persist_dir = os.path.join(
                                os.path.dirname(__file__), "saved_images",
                                self._account_key(), safe_name
                            )
                            os.makedirs(persist_dir, exist_ok=True)
                            # 기존 파일 제거 (재생성 시 깨끗이)
                            for _f in os.listdir(persist_dir):
                                try: os.remove(os.path.join(persist_dir, _f))
                                except: pass
                            import shutil
                            for _i, _p in enumerate(tmp_paths):
                                dst = os.path.join(persist_dir, f"image_{_i+1}.jpg")
                                try:
                                    shutil.copyfile(_p, dst)
                                    img_paths.append(dst)
                                except Exception:
                                    pass
                        except Exception as _ie:
                            self._emit_log(f"이미지 저장 실패 ({name}): {_ie}")

                    content["image_paths"] = img_paths

                    with lock:
                        new_posts.append({"place": place, "content": content, "posted": False})
                        done_count[0] += 1
                        self._emit_log(f"[{done_count[0]}/{total}] '{name}' 생성 완료 (이미지 {len(img_paths)}장)")
                        self._emit_status(f"생성 {done_count[0]}/{total}", "#8b5cf6")
                except Exception as e:
                    with lock:
                        done_count[0] += 1
                        self._emit_log(f"[{done_count[0]}/{total}] '{name}' 생성 실패: {e}")

            max_workers = 5 if provider == "GPT" else 2
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futures = [ex.submit(_gen_one, i, p) for i, p in enumerate(selected, 1)]
                for f in as_completed(futures):
                    if self.stop_flag:
                        for fu in futures:
                            fu.cancel()
                        break

            # 병합 + 중복 제거 (같은 업체명+주소는 새 것으로 교체, 1개만 유지)
            def _k(p):
                pl = p.get("place", {})
                return (pl.get("name", ""), pl.get("address", "") or pl.get("jibun_address", ""))
            merged_map = {}  # key → post
            # 1) 기존 포스트 먼저 (오래된 것)
            for p in self._generated_posts:
                merged_map[_k(p)] = p
            # 2) 새로 생성한 것으로 덮어쓰기
            for p in new_posts:
                merged_map[_k(p)] = p
            self._generated_posts = list(merged_map.values())
            self.is_generating = False

            if self.stop_flag:
                self._emit_log(f"포스트 생성 중단됨 ({len(new_posts)}/{total}개 완료)")
                self._emit_status("중단됨", "#ef4444")
            else:
                self._emit_status("생성 완료", "#22c55e")
                self._emit_log(f"포스트 생성 완료: {len(self._generated_posts)}/{total}개")
            self._save_generated_posts()

            # 메인 스레드에서 미리보기 열기
            from PySide6.QtCore import QMetaObject, Q_ARG
            QMetaObject.invokeMethod(self, "_show_post_preview", Qt.QueuedConnection)

        threading.Thread(target=_worker, daemon=True).start()

    @Slot()
    def _show_post_preview(self):
        """생성된 포스트 미리보기"""
        if not self._generated_posts:
            QMessageBox.information(self, "결과", "생성된 포스트가 없습니다.")
            return

        from PySide6.QtWidgets import QTextEdit, QLineEdit

        dlg = QDialog(self)
        dlg.setWindowTitle("생성된 포스트 미리보기")
        dlg.resize(1000, 700)

        layout = QVBoxLayout(dlg)

        # 상단
        top = QHBoxLayout()
        select_all_cb = QCheckBox("전체 선택")
        count_label = QLabel(f"0 / {len(self._generated_posts)}개 선택됨")
        count_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        top.addWidget(select_all_cb)
        top.addStretch()
        top.addWidget(count_label)

        btn_delete = QPushButton("선택 삭제")
        btn_delete.setStyleSheet("background: #ef4444; color: white; border: none; border-radius: 8px; font-size: 13px; padding: 8px 15px;")
        btn_delete.setCursor(Qt.PointingHandCursor)
        btn_post_selected = QPushButton("선택 포스트 생성")
        btn_post_selected.setStyleSheet("background: #4a6cf7; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; padding: 8px 20px;")
        btn_post_selected.setCursor(Qt.PointingHandCursor)
        btn_close = QPushButton("닫기")
        btn_close.setStyleSheet("padding: 8px 20px;")
        btn_close.clicked.connect(dlg.reject)
        top.addWidget(btn_delete)
        top.addWidget(btn_post_selected)
        top.addWidget(btn_close)
        layout.addLayout(top)

        # 첫 발행 타이밍 선택 체크박스
        first_row = QHBoxLayout()
        first_immediate_cb = QCheckBox("첫 포스팅을 지금 바로 시작 (체크 해제 시 설정한 간격만큼 대기 후 시작)")
        first_immediate_cb.setChecked(True)
        first_immediate_cb.setStyleSheet("font-size: 12px; color: #334155;")
        first_row.addWidget(first_immediate_cb)
        first_row.addStretch()
        layout.addLayout(first_row)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        post_checkboxes = []
        post_editors = []
        title_editors = []

        for idx, item in enumerate(self._generated_posts):
            place = item["place"]
            content = item["content"]

            # 카드
            card = QFrame()
            card.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin-bottom: 5px;")
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(5)

            # 헤더: 체크박스 + 업체명 + 저장 버튼
            hdr = QHBoxLayout()
            cb = QCheckBox(place.get("name", ""))
            cb.setStyleSheet("font-weight: bold; font-size: 13px;")
            post_checkboxes.append(cb)
            hdr.addWidget(cb)
            hdr.addStretch()

            btn_save = QPushButton("저장")
            btn_save.setStyleSheet("background: #22c55e; color: white; border: none; border-radius: 6px; padding: 5px 15px;")
            btn_save.setCursor(Qt.PointingHandCursor)
            hdr.addWidget(btn_save)
            card_layout.addLayout(hdr)

            # 제목 (편집 가능)
            title_edit = QLineEdit()
            title_edit.setText(content.get("title", ""))
            title_edit.setStyleSheet("color: #4a6cf7; font-size: 12px; padding: 5px; border: 1px solid #e2e8f0; border-radius: 4px;")
            title_editors.append(title_edit)
            card_layout.addWidget(title_edit)

            # 본문 (편집 가능)
            editor = QTextEdit()
            editor.setPlainText(content.get("body", ""))
            editor.setMaximumHeight(200)
            editor.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 4px; padding: 5px; font-size: 11px;")
            post_editors.append(editor)
            card_layout.addWidget(editor)

            # 수집 데이터 표시
            addr = place.get("address", "")
            jibun = place.get("jibun_address", "")
            if jibun:
                full_addr = f"{addr} {jibun}" if addr else jibun
            else:
                full_addr = addr
            info_text = f"주소: {full_addr}  |  카테고리: {place.get('category', '')}  |  근처역: {place.get('nearby_station', '')}  |  태그: {', '.join(content.get('tags', []))}"
            info_label = QLabel(info_text)
            info_label.setStyleSheet("color: #64748b; font-size: 10px; padding: 3px 0; background: #f8fafc; border-radius: 4px; padding: 5px;")
            info_label.setWordWrap(True)
            card_layout.addWidget(info_label)

            # 저장 버튼 기능
            def make_save(i, te, ed):
                def save():
                    self._generated_posts[i]["content"]["title"] = te.text()
                    self._generated_posts[i]["content"]["body"] = ed.toPlainText()
                    self._save_generated_posts()
                    QMessageBox.information(dlg, "저장", "저장되었습니다.")
                return save

            btn_save.clicked.connect(make_save(idx, title_edit, editor))

            scroll_layout.addWidget(card)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # 선택 카운트 업데이트
        def update_count():
            cnt = sum(1 for cb in post_checkboxes if cb.isChecked())
            count_label.setText(f"{cnt} / {len(self._generated_posts)}개 선택됨")

        for cb in post_checkboxes:
            cb.stateChanged.connect(lambda: update_count())

        # 선택 삭제
        def delete_selected():
            reply = QMessageBox.question(dlg, "삭제 확인", "선택된 포스트를 삭제하시겠습니까?",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            # 역순으로 삭제
            cards = [scroll_layout.itemAt(i).widget() for i in range(scroll_layout.count()) if scroll_layout.itemAt(i).widget()]
            for i in range(len(post_checkboxes) - 1, -1, -1):
                if post_checkboxes[i].isChecked():
                    self._generated_posts.pop(i)
                    post_checkboxes.pop(i)
                    post_editors.pop(i)
                    title_editors.pop(i)
                    widget = cards[i]
                    scroll_layout.removeWidget(widget)
                    widget.deleteLater()
            self._save_generated_posts()
            update_count()
            count_label.setText(f"0 / {len(self._generated_posts)}개 선택됨")

        btn_delete.clicked.connect(delete_selected)

        # 전체 선택
        def toggle_all(state):
            checked = select_all_cb.isChecked()
            for cb in post_checkboxes:
                cb.setChecked(checked)
            update_count()
        select_all_cb.stateChanged.connect(toggle_all)

        # 선택 포스팅
        def post_selected():
            self.posting_targets = []
            for i, cb in enumerate(post_checkboxes):
                if cb.isChecked():
                    self._generated_posts[i]["content"]["title"] = title_editors[i].text()
                    self._generated_posts[i]["content"]["body"] = post_editors[i].toPlainText()
                    self.posting_targets.append(self._generated_posts[i])
            if not self.posting_targets:
                QMessageBox.warning(dlg, "경고", "선택된 포스트가 없습니다.")
                return
            self.first_post_immediate = first_immediate_cb.isChecked()
            dlg.accept()
            self._post_generated()

        btn_post_selected.clicked.connect(post_selected)
        dlg.exec()

    def _post_generated(self):
        """미리보기에서 선택된 포스트를 블로그에 포스팅"""
        if not self.posting_targets:
            return

        cfg = load_config()
        from config import get_active_account
        account = get_active_account(cfg)
        if not account.get("naver_id") or not account.get("naver_pw"):
            QMessageBox.critical(self, "오류", "네이버 계정 정보를 설정해주세요.")
            return

        total = len(self.posting_targets)
        interval_sec = self._get_interval_seconds()
        h = int(self.interval_hour.currentText())
        m = int(self.interval_min.currentText())
        acc_idx = cfg.get("active_account", 0) + 1

        reply = QMessageBox.question(self, "포스팅 확인",
            f"[아이디 {acc_idx}] {account['naver_id']}\n{total}개 포스팅\n간격: {h}시간 {m}분\n\n시작할까요?")
        if reply != QMessageBox.Yes:
            return

        keyword = self.keyword_input.currentText().strip()
        pix_keys = [k for k in cfg.get("pixabay_key_list", []) if k]
        self.is_posting = True
        self.stop_flag = False

        def _worker():
            poster = None
            try:
                self._emit_status("포스팅 중...", "#8b5cf6")
                # 메인 프로그램 창 위치에 브라우저 띄우기
                _g = self.geometry()
                poster = NaverBlogPoster(
                    naver_id=account["naver_id"],
                    naver_pw=account["naver_pw"],
                    blog_id=account["blog_id"],
                    window_x=_g.x(),
                    window_y=_g.y(),
                )
                self._emit_log("브라우저 시작...")
                poster.start_browser()
                self._emit_log("네이버 로그인 중...")
                if not poster.login():
                    self._emit_log("로그인 실패!")
                    return
                self._emit_log("로그인 성공")

                import datetime as _dt
                base_time = _dt.datetime.now()
                first_immediate = getattr(self, 'first_post_immediate', True)
                for i, item in enumerate(self.posting_targets, 1):
                    if self.stop_flag:
                        self._emit_log("포스팅 중단됨")
                        break

                    # 첫 포스트: 즉시 발행 (옵션에 따라) / 나머지: 예약 발행
                    if i == 1 and first_immediate:
                        schedule_time = None  # 즉시 발행
                    else:
                        # i번째 포스트 = base_time + (i-1)*interval (첫 건 예약이면 i=1부터 interval)
                        offset_idx = (i - 1) if first_immediate else i
                        sched_dt = base_time + _dt.timedelta(seconds=interval_sec * offset_idx)
                        # 10분 단위 반올림
                        minute = (sched_dt.minute // 10) * 10
                        sched_dt = sched_dt.replace(minute=minute, second=0, microsecond=0)
                        if sched_dt <= _dt.datetime.now():
                            sched_dt += _dt.timedelta(minutes=10)
                        schedule_time = sched_dt.strftime("%Y-%m-%d %H:%M")
                        self._emit_log(f"[{i}/{total}] 예약 시간: {schedule_time}")

                    place = item["place"]
                    content = item["content"]
                    name = place.get("name", "")
                    self._emit_log(f"[{i}/{total}] '{name}' 포스팅 중...")
                    self._emit_status(f"포스팅 {i}/{total}", "#8b5cf6")

                    # 포스트 생성 시 저장된 이미지 우선 사용 (재다운로드 방지)
                    img_paths = []
                    saved_paths = content.get("image_paths", []) or []
                    saved_paths = [p for p in saved_paths if p and os.path.exists(p)]
                    if saved_paths:
                        img_paths = saved_paths
                        self._emit_log(f"저장된 이미지 {len(img_paths)}장 사용")
                    elif pix_keys:
                        try:
                            biz = (place.get("category") or "").strip() or keyword
                            self._emit_log(f"이미지 재검색 업종: '{biz}' (저장본 없음)")
                            img_paths = download_images(
                                pix_keys[0], biz,
                                content.get("image_count", 3)
                            )
                            self._emit_log(f"이미지 {len(img_paths)}장 다운로드")
                        except Exception as e:
                            self._emit_log(f"이미지 다운로드 실패: {e}")
                    else:
                        self._emit_log("Pixabay API 키 미설정 - 이미지 없이 포스팅")

                    body = content.get("body", "")

                    # 제목의 잘못된 지역명 교체 (검색 키워드의 구 ≠ 실제 주소의 구인 경우)
                    actual_address = place.get("address", "") or place.get("jibun_address", "")
                    import re
                    actual_gu_match = re.search(r"([가-힣]+구)", actual_address)
                    if actual_gu_match:
                        actual_gu = actual_gu_match.group(1)
                        title = content.get("title", "")
                        wrong_gus = re.findall(r"([가-힣]+구)", title)
                        for wg in wrong_gus:
                            if wg != actual_gu:
                                title = title.replace(wg, actual_gu)
                                self._emit_log(f"제목 지역 교체: {wg} → {actual_gu}")
                        # 동 이름도 확인
                        actual_dong_match = re.search(r"([가-힣]+동)", actual_address)
                        if actual_dong_match:
                            actual_dong = actual_dong_match.group(1)
                            wrong_dongs = re.findall(r"([가-힣]+동)", title)
                            for wd in wrong_dongs:
                                if wd != actual_dong and wd != actual_gu:
                                    title = title.replace(wd, actual_dong)
                        content["title"] = title

                    # 이미지가 있는데 본문에 [이미지] 마커가 없으면 균등 분포로 자동 삽입
                    if img_paths and "[이미지]" not in body:
                        paragraphs = [p for p in body.split("\n\n") if p.strip()]
                        if len(paragraphs) >= 2:
                            step = max(1, len(paragraphs) // (len(img_paths) + 1))
                            new_parts = []
                            img_used = 0
                            for idx, p in enumerate(paragraphs):
                                new_parts.append(p)
                                if img_used < len(img_paths) and (idx + 1) % step == 0 and idx < len(paragraphs) - 1:
                                    new_parts.append("[이미지]")
                                    img_used += 1
                            body = "\n\n".join(new_parts)
                            content["body"] = body
                            self._emit_log(f"본문에 [이미지] 마커 {img_used}개 자동 삽입")

                    try:
                        success = poster.write_post(
                            title=content["title"],
                            body=content["body"],
                            tags=content["tags"],
                            image_paths=img_paths,
                            category=account.get("blog_category", ""),
                            place_name=name,
                            place_address=place.get("address", "") or place.get("jibun_address", ""),
                            schedule_time=schedule_time,
                        )
                        msg = "완료!" if success else "실패"
                        self._emit_log(f"[{i}/{total}] '{name}' {msg}")
                        # 브라우저 세션 확인 — 죽었으면 즉시 중단
                        try:
                            _ = poster.driver.current_url
                        except Exception as _se:
                            self._emit_log(f"!!! 브라우저 세션이 종료됨: {str(_se)[:120]}. 포스팅 중단")
                            self.stop_flag = True
                            break
                        if success:
                            # 포스팅 완료 시: 생성된 포스트만 제거 (업체는 F7 목록에 유지)
                            _k = self._place_key(place)
                            self._generated_posts = [
                                gp for gp in self._generated_posts
                                if self._place_key(gp.get("place", {})) != _k
                            ]
                            self._save_generated_posts()
                            self._emit_log(f"'{place.get('name','')}' 포스팅 완료 → 생성된 포스트 제거")
                    except Exception as e:
                        self._emit_log(f"'{name}' 오류: {e}")

                if not self.stop_flag:
                    self._emit_log(f"전체 포스팅 완료! ({total}개)")
                self._emit_status("완료", "#22c55e")

            except Exception as e:
                self._emit_log(f"오류: {e}")
                self._emit_status("오류", "#ef4444")
            finally:
                self.is_posting = False
                if poster:
                    poster.close()

        threading.Thread(target=_worker, daemon=True).start()

    # ── 포스팅 업체 선택 ──
    def _load_all_crawl_results(self) -> dict:
        """현재 계정의 logs 폴더의 모든 크롤링 결과를 키워드별로 그룹핑 (삭제된 키 제외)"""
        from places_crawler import load_results
        log_dir = self._get_logs_dir()
        groups = {}
        if not os.path.exists(log_dir):
            return groups
        deleted = self._load_deleted_keys()
        files = sorted(
            [f for f in os.listdir(log_dir) if f.endswith(".json")],
            reverse=True
        )
        for f in files:
            try:
                raw = load_results(os.path.join(log_dir, f))
                keyword = raw.get("keyword", "")
                items = raw.get("items", [])
                if not items:
                    continue
                date_part = f.replace("places_", "").replace(".json", "")
                if keyword:
                    group_name = f"{keyword} ({len(items)}개) - {date_part}"
                else:
                    first = items[0]
                    addr = first.get("address", "")
                    category = first.get("category", "")
                    group_name = f"{addr.split()[0] if addr else ''} {category} ({len(items)}개) - {date_part}"
                groups[group_name] = items
            except Exception:
                continue
        return groups

    def _show_posting_selector(self) -> list:
        # 모든 크롤링 결과 로드
        all_groups = self._load_all_crawl_results()
        # 현재 메모리에 있는 것도 추가
        if self.crawled_data:
            all_groups["현재 크롤링 결과 (" + str(len(self.crawled_data)) + "개)"] = self.crawled_data

        if not all_groups:
            QMessageBox.warning(self, "경고", "크롤링 결과가 없습니다.")
            return []

        # 생성된 포스트 로드해서 (업체명+주소) → post 매핑
        _gen_posts = self._load_generated_posts()
        _post_map = {}
        for _gp in _gen_posts:
            _pl = _gp.get("place", {})
            _key = (_pl.get("name", ""), _pl.get("address", "") or _pl.get("jibun_address", ""))
            _post_map[_key] = _gp

        dlg = QDialog(self)
        dlg.setWindowTitle("포스팅할 업체 선택")
        dlg.resize(950, 600)

        layout = QVBoxLayout(dlg)

        # 상단
        top = QHBoxLayout()
        btn_all = QPushButton("전체 선택")
        btn_all.setStyleSheet("padding: 6px 15px;")
        btn_none = QPushButton("전체 해제")
        btn_none.setStyleSheet("padding: 6px 15px;")
        count_label = QLabel("0개 선택됨")
        count_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        top.addWidget(btn_all)
        top.addWidget(btn_none)
        top.addStretch()
        top.addWidget(count_label)
        layout.addLayout(top)

        # 트리뷰
        tree = QTreeWidget()
        tree.setHeaderLabels(["업체명", "업체주소", "카테고리", "근처역", "앞 키워드", "태그", "픽사베이 키워드"])
        tree.setColumnWidth(0, 200)
        tree.setColumnWidth(1, 220)
        tree.setColumnWidth(2, 120)
        tree.setColumnWidth(3, 120)
        tree.setColumnWidth(4, 180)
        tree.setColumnWidth(5, 140)
        tree.setColumnWidth(6, 180)
        tree.setAlternatingRowColors(True)
        tree.setStyleSheet("""
            QTreeWidget { font-size: 12px; }
            QTreeWidget::item { padding: 3px 0; }
            alternate-background-color: #f5f5f5;
        """)

        # 삭제된 키 로드 (F7/F8 공유)
        _deleted_keys = self._load_deleted_keys()

        # 그룹별 트리 구성
        all_items = []  # (QTreeWidgetItem, place_data)
        for group_name, places in all_groups.items():
            # 삭제된 항목 필터
            places = [p for p in places if self._place_key(p) not in _deleted_keys]
            if not places:
                continue
            parent = QTreeWidgetItem(tree)
            parent.setText(0, group_name)
            parent.setFlags(parent.flags() | Qt.ItemIsUserCheckable)
            parent.setCheckState(0, Qt.Unchecked)
            parent.setExpanded(False)

            posted_count = 0
            child_count = 0

            for p in places:
                addr = p.get("address", "")
                jibun = p.get("jibun_address", "")
                if jibun:
                    full_addr = f"{addr} {jibun}" if addr else jibun
                else:
                    full_addr = addr

                child = QTreeWidgetItem(parent)
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked)

                # 상태 표시등: 생성된 포스트가 있는지 + 업로드 완료 여부
                _k = (p.get("name", ""), p.get("address", "") or p.get("jibun_address", ""))
                _gp = _post_map.get(_k)
                is_generated = _gp is not None
                is_done = bool(_gp and _gp.get("posted", False))
                if is_done:
                    child.setText(0, "[완] " + p.get("name", ""))
                    child.setForeground(0, QColor("#3b82f6"))
                    posted_count += 1
                elif is_generated:
                    child.setText(0, "●  " + p.get("name", ""))
                    child.setForeground(0, QColor("#22c55e"))
                    posted_count += 1
                else:
                    child.setText(0, "●  " + p.get("name", ""))
                    child.setForeground(0, QColor("#ef4444"))

                child.setText(1, full_addr)
                child.setText(2, p.get("category", ""))
                child.setText(3, p.get("nearby_station", ""))
                child.setText(4, p.get("front_keywords", ""))
                child.setText(5, p.get("tags", ""))
                child.setText(6, p.get("pixabay_keywords", ""))
                child.setFlags(child.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
                all_items.append((child, p))
                child_count += 1

            # 폴더 상태등: 모두 초록 / 모두 빨강 / 혼합 주황
            if child_count > 0:
                if posted_count == child_count:
                    parent.setForeground(0, QColor("#22c55e"))
                    parent.setText(0, "●  " + group_name)
                elif posted_count == 0:
                    parent.setForeground(0, QColor("#ef4444"))
                    parent.setText(0, "●  " + group_name)
                else:
                    parent.setForeground(0, QColor("#f59e0b"))
                    parent.setText(0, "●  " + group_name)

        def update_count():
            cnt = sum(1 for item, _ in all_items if item.checkState(0) == Qt.Checked)
            count_label.setText(f"{cnt}개 선택됨")

        def on_item_changed(item, col):
            if col != 0:
                return
            # 부모 체크 → 자식 전부 체크/해제
            if item.childCount() > 0:
                state = item.checkState(0)
                for i in range(item.childCount()):
                    item.child(i).setCheckState(0, state)
            update_count()

        tree.itemChanged.connect(on_item_changed)

        def select_all():
            tree.blockSignals(True)
            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                parent.setCheckState(0, Qt.Checked)
                for j in range(parent.childCount()):
                    parent.child(j).setCheckState(0, Qt.Checked)
            tree.blockSignals(False)
            update_count()

        def select_none():
            tree.blockSignals(True)
            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                parent.setCheckState(0, Qt.Unchecked)
                for j in range(parent.childCount()):
                    parent.child(j).setCheckState(0, Qt.Unchecked)
            tree.blockSignals(False)
            update_count()

        btn_all.clicked.connect(select_all)
        btn_none.clicked.connect(select_none)

        layout.addWidget(tree)

        # 하단
        bottom = QHBoxLayout()

        # 삭제 버튼들 — 영구 저장 (deleted_keys_*.json) + generated_posts 동기화
        def _persist_delete(places_to_delete: list):
            if not places_to_delete:
                return
            deleted = self._load_deleted_keys()
            keys = {self._place_key(p) for p in places_to_delete}
            deleted.update(keys)
            self._save_deleted_keys(deleted)
            # generated_posts에도 있으면 제거
            changed = False
            new_gp = []
            current = self._load_generated_posts()
            for gp in current:
                if self._place_key(gp.get("place", {})) in keys:
                    changed = True
                    continue
                new_gp.append(gp)
            if changed:
                self._generated_posts = new_gp
                self._save_generated_posts()

        def delete_selected():
            # 체크된 places 수집
            checked_places = []
            for it, p in all_items:
                if it.checkState(0) == Qt.Checked:
                    checked_places.append(p)
            if not checked_places:
                QMessageBox.information(dlg, "안내", "선택된 항목이 없습니다.")
                return
            reply = QMessageBox.question(dlg, "삭제 확인", f"{len(checked_places)}개 항목을 삭제하시겠습니까?\n(F8에서도 같이 제거됩니다)",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            _persist_delete(checked_places)
            # UI에서 제거
            tree.blockSignals(True)
            to_remove_idx = []
            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                for j in range(parent.childCount() - 1, -1, -1):
                    child = parent.child(j)
                    if child.checkState(0) == Qt.Checked:
                        all_items[:] = [(it, p) for it, p in all_items if it is not child]
                        parent.removeChild(child)
                if parent.childCount() == 0:
                    to_remove_idx.append(i)
            for idx in reversed(to_remove_idx):
                tree.takeTopLevelItem(idx)
            tree.blockSignals(False)
            update_count()
            self._emit_log(f"{len(checked_places)}개 항목 삭제 (영구 반영)")

        def delete_all():
            all_places = [p for _, p in all_items]
            if not all_places:
                return
            reply = QMessageBox.question(dlg, "전체 삭제 확인", f"현재 표시된 전체 {len(all_places)}개 항목을 삭제하시겠습니까?\n(F8에서도 같이 제거됩니다)",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            _persist_delete(all_places)
            tree.blockSignals(True)
            tree.clear()
            all_items.clear()
            tree.blockSignals(False)
            update_count()
            self._emit_log(f"{len(all_places)}개 전체 삭제 (영구 반영)")

        btn_del_sel = QPushButton("선택 삭제")
        btn_del_sel.setStyleSheet("background: #ef4444; color: white; border: none; border-radius: 8px; padding: 8px 15px;")
        btn_del_sel.setCursor(Qt.PointingHandCursor)
        btn_del_sel.clicked.connect(delete_selected)

        btn_del_all = QPushButton("전체 삭제")
        btn_del_all.setStyleSheet("background: #dc2626; color: white; border: none; border-radius: 8px; padding: 8px 15px;")
        btn_del_all.setCursor(Qt.PointingHandCursor)
        btn_del_all.clicked.connect(delete_all)

        btn_refresh = QPushButton("새로고침")
        btn_refresh.setStyleSheet("background: #64748b; color: white; border: none; border-radius: 8px; padding: 8px 15px;")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        def do_refresh():
            dlg.done(2)  # 특수 코드: 새로고침
        btn_refresh.clicked.connect(do_refresh)

        bottom.addWidget(btn_del_sel)
        bottom.addWidget(btn_del_all)
        bottom.addWidget(btn_refresh)
        bottom.addStretch()

        btn_cancel = QPushButton("취소")
        btn_cancel.setStyleSheet("padding: 8px 20px;")
        btn_cancel.clicked.connect(dlg.reject)
        btn_ok = QPushButton("포스트 생성")
        btn_ok.setStyleSheet("background: #8b5cf6; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; padding: 10px 25px;")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.clicked.connect(dlg.accept)
        bottom.addWidget(btn_cancel)
        bottom.addWidget(btn_ok)
        layout.addLayout(bottom)

        _rc = dlg.exec()
        if _rc == 2:
            # 새로고침: 다이얼로그 재오픈
            return self._show_posting_selector()
        if _rc == QDialog.Accepted:
            selected = []
            for item, p in all_items:
                if item.checkState(0) == Qt.Checked:
                    # 수정된 값 반영
                    p["front_keywords"] = item.text(4)
                    p["tags"] = item.text(5)
                    p["pixabay_keywords"] = item.text(6)
                    selected.append(p)
            return selected
        return []

    # ── 블로그 포스팅 ──
    def _start_blog_posting(self):
        # 크롤링 결과 불러오기 (현재 없으면 logs에서 로드)
        if not self.crawled_data:
            log_dir = self._get_logs_dir()
            if os.path.exists(log_dir):
                files = sorted(
                    [f for f in os.listdir(log_dir) if f.endswith(".json")],
                    reverse=True
                )
                if files:
                    from places_crawler import load_results
                    filepath = os.path.join(log_dir, files[0])
                    raw = load_results(filepath)
                    self.crawled_data = raw.get("items", []) if isinstance(raw, dict) else raw

        if not self.crawled_data:
            QMessageBox.warning(self, "경고", "먼저 크롤링을 실행해주세요.")
            return

        # 업체 선택 다이얼로그
        selected = self._show_posting_selector()
        if not selected:
            return

        cfg = load_config()
        provider = cfg.get("ai_provider", "Gemini")
        key_list_name = "gemini_key_list" if provider == "Gemini" else "gpt_key_list"
        api_keys = [k for k in cfg.get(key_list_name, []) if k]
        if not api_keys:
            QMessageBox.critical(self, "오류", f"{provider} API 키를 설정해주세요.")
            return
        api_key = api_keys[0]
        from config import get_active_account
        account = get_active_account(cfg)
        if not account.get("naver_id") or not account.get("naver_pw"):
            QMessageBox.critical(self, "오류", "네이버 계정 정보를 설정해주세요.")
            return
        if self.is_posting:
            return

        total = len(selected)
        interval_sec = self._get_interval_seconds()
        h = int(self.interval_hour.currentText())
        m = int(self.interval_min.currentText())
        acc_idx = cfg.get("active_account", 0) + 1

        reply = QMessageBox.question(self, "포스팅 확인",
            f"[아이디 {acc_idx}] {account['naver_id']}\n선택된 {total}개 업체 포스팅\n간격: {h}시간 {m}분\n\n시작할까요?")
        if reply != QMessageBox.Yes:
            return

        keyword = self.keyword_input.currentText().strip()
        self.is_posting = True
        self.stop_flag = False
        self.posting_targets = selected

        def _worker():
            poster = None
            try:
                self._emit_status("포스팅 중...", "#8b5cf6")
                # 메인 프로그램 창 위치에 브라우저 띄우기
                _g = self.geometry()
                poster = NaverBlogPoster(
                    naver_id=account["naver_id"],
                    naver_pw=account["naver_pw"],
                    blog_id=account["blog_id"],
                    window_x=_g.x(),
                    window_y=_g.y(),
                )
                self._emit_log("브라우저 시작...")
                poster.start_browser()

                self._emit_log("네이버 로그인 중...")
                if not poster.login():
                    self._emit_log("로그인 실패!")
                    return

                self._emit_log("로그인 성공")

                for i, place in enumerate(self.posting_targets, 1):
                    if self.stop_flag:
                        self._emit_log("포스팅 중단됨")
                        break

                    name = place.get("name", "")
                    self._emit_log(f"[{i}/{total}] '{name}' 글 생성 중...")
                    self._emit_status(f"포스팅 {i}/{total}", "#8b5cf6")

                    try:
                        content = generate_content(
                            provider=cfg["ai_provider"],
                            api_key=api_key,
                            place=place, keyword=keyword
                        )
                    except Exception as e:
                        self._emit_log(f"'{name}' 글 생성 실패: {e}")
                        continue

                    img_paths = []
                    pix_keys = [k for k in cfg.get("pixabay_key_list", []) if k]
                    if pix_keys:
                        biz = (place.get("category") or "").strip() or keyword
                        img_paths = download_images(
                            pix_keys[0], biz,
                            content.get("image_count", 3)
                        )

                    self._emit_log(f"[{i}/{total}] '{name}' 포스팅 중...")

                    try:
                        success = poster.write_post(
                            title=content["title"], body=content["body"],
                            tags=content["tags"], image_paths=img_paths,
                            category=account.get("blog_category", ""),
                        )
                        msg = "완료!" if success else "실패"
                        self._emit_log(f"[{i}/{total}] '{name}' {msg}")
                    except Exception as e:
                        self._emit_log(f"'{name}' 오류: {e}")

                    if i < total and interval_sec > 0 and not self.stop_flag:
                        remaining = interval_sec
                        while remaining > 0 and not self.stop_flag:
                            m_left, s_left = divmod(remaining, 60)
                            self._emit_status(f"대기 {m_left}분 {s_left}초", "#94a3b8")
                            import time as _time
                            wait = min(60, remaining)
                            _time.sleep(wait)
                            remaining -= wait

                if not self.stop_flag:
                    self._emit_log(f"전체 포스팅 완료! ({total}개)")

                self._emit_status("완료", "#22c55e")

            except Exception as e:
                self._emit_log(f"오류: {e}")
                self._emit_status("오류", "#ef4444")
            finally:
                self.is_posting = False
                if poster:
                    poster.close()

        threading.Thread(target=_worker, daemon=True).start()


LOGIN_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login_cache.json")


def _load_login_cache():
    try:
        with open(LOGIN_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_login_cache(data):
    try:
        with open(LOGIN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("로그인")
        self.setFixedSize(340, 290)
        self.user = None  # 로그인 성공 시 유저 dict

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)

        title = QLabel("플레이스 블로그 자동화")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(12)

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("아이디")
        self.id_edit.setStyleSheet("padding: 8px; font-size: 13px;")
        layout.addWidget(self.id_edit)

        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.Password)
        self.pw_edit.setPlaceholderText("비밀번호")
        self.pw_edit.setStyleSheet("padding: 8px; font-size: 13px;")
        self.pw_edit.returnPressed.connect(self._try_login)
        layout.addWidget(self.pw_edit)

        chk_row = QHBoxLayout()
        self.chk_save_id = QCheckBox("아이디 저장")
        self.chk_save_pw = QCheckBox("비밀번호 저장")
        self.chk_save_id.setStyleSheet("font-size: 11px; color: #64748b;")
        self.chk_save_pw.setStyleSheet("font-size: 11px; color: #64748b;")
        chk_row.addWidget(self.chk_save_id)
        chk_row.addWidget(self.chk_save_pw)
        chk_row.addStretch()
        layout.addLayout(chk_row)

        self.msg = QLabel("")
        self.msg.setStyleSheet("color: #ef4444; font-size: 11px;")
        layout.addWidget(self.msg)

        btn_row = QHBoxLayout()
        btn_login = QPushButton("로그인")
        btn_login.setStyleSheet("background: #4a6cf7; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
        btn_login.setCursor(Qt.PointingHandCursor)
        btn_login.clicked.connect(self._try_login)
        btn_cancel = QPushButton("종료")
        btn_cancel.setStyleSheet("padding: 8px 20px;")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_login)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        layout.addSpacing(4)
        signup_row = QHBoxLayout()
        signup_row.addStretch()
        self.signup_link = QLabel('<a href="#" style="color:#64748b; text-decoration:none;">회원가입</a>')
        self.signup_link.setStyleSheet("font-size: 11px; color: #64748b;")
        self.signup_link.setCursor(Qt.PointingHandCursor)
        self.signup_link.linkActivated.connect(self._open_signup)
        signup_row.addWidget(self.signup_link)
        signup_row.addStretch()
        layout.addLayout(signup_row)

        self._load_cached()

    def _load_cached(self):
        cache = _load_login_cache()
        if cache.get("save_id"):
            self.chk_save_id.setChecked(True)
            self.id_edit.setText(cache.get("id", ""))
        if cache.get("save_pw"):
            self.chk_save_pw.setChecked(True)
            self.pw_edit.setText(cache.get("pw", ""))

    def _open_signup(self):
        dlg = SignupDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.username:
            self.id_edit.setText(dlg.username)
            self.pw_edit.setFocus()
            self.msg.setStyleSheet("color: #22c55e; font-size: 11px;")
            self.msg.setText("가입 완료. 로그인해주세요.")

    def _try_login(self):
        from users import verify, is_expired
        import datetime as _dt
        uid = self.id_edit.text().strip()
        pw = self.pw_edit.text()
        user = verify(uid, pw)
        if not user:
            self.msg.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.msg.setText("아이디 또는 비밀번호가 틀렸습니다.")
            return
        if is_expired(user):
            self.msg.setStyleSheet(u"color: #ef4444; font-size: 11px;")
            self.msg.setText(f"사용 기간 만료 ({user.get('expires','')})")
            return
        cache = {
            "save_id": self.chk_save_id.isChecked(),
            "save_pw": self.chk_save_pw.isChecked(),
            "id": uid if self.chk_save_id.isChecked() else "",
            "pw": pw if self.chk_save_pw.isChecked() else "",
        }
        _save_login_cache(cache)
        self.user = user
        self.accept()


class SignupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("회원가입")
        self.setFixedSize(340, 300)
        self.username = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)

        title = QLabel("회원가입")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(10)

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("아이디 (3자 이상)")
        self.id_edit.setStyleSheet("padding: 8px; font-size: 13px;")
        layout.addWidget(self.id_edit)

        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.Password)
        self.pw_edit.setPlaceholderText("비밀번호 (4자 이상)")
        self.pw_edit.setStyleSheet("padding: 8px; font-size: 13px;")
        layout.addWidget(self.pw_edit)

        self.pw2_edit = QLineEdit()
        self.pw2_edit.setEchoMode(QLineEdit.Password)
        self.pw2_edit.setPlaceholderText("비밀번호 확인")
        self.pw2_edit.setStyleSheet("padding: 8px; font-size: 13px;")
        self.pw2_edit.returnPressed.connect(self._try_signup)
        layout.addWidget(self.pw2_edit)

        self.msg = QLabel("")
        self.msg.setStyleSheet("color: #ef4444; font-size: 11px;")
        self.msg.setWordWrap(True)
        layout.addWidget(self.msg)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("가입")
        btn_ok.setStyleSheet("background: #22c55e; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.clicked.connect(self._try_signup)
        btn_cancel = QPushButton("취소")
        btn_cancel.setStyleSheet("padding: 8px 20px;")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _try_signup(self):
        from users import create_user, load_users
        uid = self.id_edit.text().strip()
        pw = self.pw_edit.text()
        pw2 = self.pw2_edit.text()
        if len(uid) < 3:
            self.msg.setText("아이디는 3자 이상이어야 합니다.")
            return
        if len(pw) < 4:
            self.msg.setText("비밀번호는 4자 이상이어야 합니다.")
            return
        if pw != pw2:
            self.msg.setText("비밀번호가 일치하지 않습니다.")
            return
        if uid in load_users():
            self.msg.setText("이미 존재하는 아이디입니다.")
            return
        expires = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        if not create_user(uid, pw, role="user", expires=expires):
            self.msg.setText("가입 실패. 다시 시도해주세요.")
            return
        self.username = uid
        self.accept()


class ExpiresEditor(QWidget):
    """만료일 편집기 — 달력 팝업 + +30/+90/+180/+365 + 무제한"""
    def __init__(self, expires_str: str = "", parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QSizePolicy
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.line = QLineEdit()
        self.line.setPlaceholderText("무제한")
        self.line.setText(expires_str or "")
        self.line.setFixedWidth(92)
        layout.addWidget(self.line)

        btn_cal = QPushButton("📅")
        btn_cal.setFixedWidth(28)
        btn_cal.setStyleSheet("padding: 2px;")
        btn_cal.setCursor(Qt.PointingHandCursor)
        btn_cal.clicked.connect(self._open_calendar)
        layout.addWidget(btn_cal)

        for days in (30, 90, 180, 365):
            b = QPushButton(f"+{days}")
            b.setFixedWidth(38)
            b.setStyleSheet("padding: 2px; font-size: 10px;")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, d=days: self._add_days(d))
            layout.addWidget(b)

        btn_inf = QPushButton("무제한")
        btn_inf.setFixedWidth(54)
        btn_inf.setStyleSheet("padding: 2px; font-size: 10px;")
        btn_inf.setCursor(Qt.PointingHandCursor)
        btn_inf.clicked.connect(lambda: self.line.setText(""))
        layout.addWidget(btn_inf)
        layout.addStretch()

    def _open_calendar(self):
        from PySide6.QtWidgets import QCalendarWidget, QDialogButtonBox
        from PySide6.QtCore import QDate
        dlg = QDialog(self)
        dlg.setWindowTitle("만료일 선택")
        v = QVBoxLayout(dlg)
        cal = QCalendarWidget()
        txt = self.line.text().strip()
        if txt:
            d = QDate.fromString(txt, "yyyy-MM-dd")
            if d.isValid():
                cal.setSelectedDate(d)
        v.addWidget(cal)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(dlg.accept)
        bbox.rejected.connect(dlg.reject)
        v.addWidget(bbox)
        if dlg.exec() == QDialog.Accepted:
            self.line.setText(cal.selectedDate().toString("yyyy-MM-dd"))

    def _add_days(self, days: int):
        from PySide6.QtCore import QDate
        txt = self.line.text().strip()
        base = QDate.currentDate()
        if txt:
            d = QDate.fromString(txt, "yyyy-MM-dd")
            if d.isValid():
                base = d
        self.line.setText(base.addDays(days).toString("yyyy-MM-dd"))

    def get_value(self) -> str:
        return self.line.text().strip()


class AdminDialog(QDialog):
    """관리자 전용 — 사용자 계정 + 기간 관리"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("관리자 메뉴")
        self.resize(900, 460)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("사용자 관리 (아이디 / 역할 / 사용 만료일, 빈값=무제한)"))

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["아이디", "역할", "만료일", "비밀번호 재설정"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 360)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e2e8f0;
                selection-background-color: #e2e8f0;
                selection-color: #000;
                background: white;
            }
            QTableWidget::item:selected {
                background-color: #e2e8f0;
                color: #000;
            }
        """)
        layout.addWidget(self.table)

        self._reload()

        bottom = QHBoxLayout()
        btn_add = QPushButton("+ 사용자 추가")
        btn_add.setStyleSheet("background: #22c55e; color: white; border: none; border-radius: 6px; padding: 8px 14px;")
        btn_add.clicked.connect(self._add_user)
        btn_del = QPushButton("선택 삭제")
        btn_del.setStyleSheet("background: #ef4444; color: white; border: none; border-radius: 6px; padding: 8px 14px;")
        btn_del.clicked.connect(self._del_user)
        btn_save = QPushButton("저장")
        btn_save.setStyleSheet("background: #4a6cf7; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
        btn_save.clicked.connect(self._save_all)
        btn_close = QPushButton("닫기")
        btn_close.setStyleSheet("padding: 8px 20px;")
        btn_close.clicked.connect(self.reject)
        bottom.addWidget(btn_add)
        bottom.addWidget(btn_del)
        bottom.addStretch()
        bottom.addWidget(btn_save)
        bottom.addWidget(btn_close)
        layout.addLayout(bottom)

    def _reload(self):
        from users import load_users
        users = load_users()
        self.table.setRowCount(len(users))
        for row, (uid, u) in enumerate(sorted(users.items())):
            it_id = QTableWidgetItem(uid)
            if uid == "admin":
                it_id.setFlags(it_id.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, it_id)

            # 역할 드롭다운
            role_combo = QComboBox()
            role_combo.addItems(["user", "admin"])
            role_combo.setCurrentText(u.get("role", "user") if u.get("role") in ("user", "admin") else "user")
            role_combo.setStyleSheet("padding: 2px 6px;")
            self.table.setCellWidget(row, 1, role_combo)

            # 만료일 편집기
            exp_editor = ExpiresEditor(u.get("expires", ""))
            self.table.setCellWidget(row, 2, exp_editor)

            self.table.setItem(row, 3, QTableWidgetItem(""))  # 비번 재설정 입력칸

    def _add_user(self):
        from PySide6.QtWidgets import QInputDialog
        uid, ok = QInputDialog.getText(self, "사용자 추가", "아이디:")
        if not ok or not uid.strip():
            return
        uid = uid.strip()
        pw, ok = QInputDialog.getText(self, "사용자 추가", f"'{uid}' 비밀번호:", QLineEdit.Password)
        if not ok or not pw:
            return
        from users import create_user
        if not create_user(uid, pw, role="user", expires=""):
            QMessageBox.warning(self, "경고", "이미 존재하는 아이디입니다.")
            return
        self._reload()

    def _del_user(self):
        row = self.table.currentRow()
        if row < 0:
            return
        uid = self.table.item(row, 0).text()
        if uid == "admin":
            QMessageBox.warning(self, "경고", "admin 계정은 삭제할 수 없습니다.")
            return
        if QMessageBox.question(self, "확인", f"'{uid}' 삭제?") != QMessageBox.Yes:
            return
        from users import delete_user
        delete_user(uid)
        self._reload()

    def _save_all(self):
        from users import update_user
        for row in range(self.table.rowCount()):
            uid = self.table.item(row, 0).text().strip()
            role_widget = self.table.cellWidget(row, 1)
            role = role_widget.currentText() if role_widget else "user"
            exp_widget = self.table.cellWidget(row, 2)
            expires = exp_widget.get_value() if exp_widget else ""
            new_pw_item = self.table.item(row, 3)
            new_pw = (new_pw_item.text() if new_pw_item else "").strip()
            if role not in ("user", "admin"):
                role = "user"
            update_user(uid, password=(new_pw if new_pw else None), role=role, expires=expires)
        QMessageBox.information(self, "완료", "저장되었습니다.")
        self._reload()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    app.setFont(QFont("맑은 고딕", 10))

    # 로그인 먼저
    login = LoginDialog()
    if login.exec() != QDialog.Accepted or not login.user:
        sys.exit(0)

    # 로그인 유저 컨텍스트 설정 (MainWindow 생성 전에 필수 — load_config가 이걸로 유저별 accounts 분기)
    import config as _cfg
    _cfg.set_current_user(login.user.get("username", "admin"))

    window = MainWindow()
    window.apply_user_session(login.user)
    window.show()
    sys.exit(app.exec())
