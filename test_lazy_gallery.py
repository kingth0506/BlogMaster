# -*- coding: utf-8 -*-
"""포스팅 이미지 Lazy Load 갤러리 테스트
saved_images/{user}/ 아래 모든 이미지를 썸네일로 표시.
스크롤로 보이는 것만 로드.
"""
import sys
import os

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLabel, QFrame, QPushButton, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QSize, QEvent
from PySide6.QtGui import QPixmap, QFont

THUMB_SIZE = 160
COLS = 6


class LazyThumb(QLabel):
    """썸네일 위젯 — 실제 이미지는 is_visible() 시점에 로드"""
    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self.loaded = False
        self.setFixedSize(THUMB_SIZE, THUMB_SIZE)
        self.setStyleSheet("background: #e5e7eb; border: 1px solid #d1d5db;")
        self.setAlignment(Qt.AlignCenter)
        self.setText("...")

    def load_image(self):
        if self.loaded:
            return
        try:
            pm = QPixmap(self.image_path)
            if pm.isNull():
                self.setText("!")
                return
            self.setPixmap(pm.scaled(
                THUMB_SIZE, THUMB_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            self.loaded = True
        except Exception as e:
            self.setText(f"E:{e}")


class LazyGallery(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("이미지 갤러리 (Lazy Load 테스트)")
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # 상단: 유저/폴더 선택
        top = QHBoxLayout()
        top.addWidget(QLabel("유저 폴더:"))
        self.user_combo = QComboBox()
        top.addWidget(self.user_combo, 1)
        btn_reload = QPushButton("새로고침")
        btn_reload.clicked.connect(self._reload_users)
        top.addWidget(btn_reload)
        self.count_label = QLabel("")
        top.addWidget(self.count_label)
        root.addLayout(top)

        # 스크롤 영역
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)
        root.addWidget(self.scroll, 1)

        self.canvas = QWidget()
        self.grid_layout = QVBoxLayout(self.canvas)
        self.grid_layout.setSpacing(16)
        self.scroll.setWidget(self.canvas)

        self.thumbs = []  # LazyThumb 인스턴스들
        self._reload_users()
        self.user_combo.currentIndexChanged.connect(self._on_user_changed)

    def _base_dir(self):
        return os.path.join(os.path.dirname(__file__), "saved_images")

    def _reload_users(self):
        self.user_combo.clear()
        base = self._base_dir()
        if os.path.exists(base):
            for name in sorted(os.listdir(base)):
                if os.path.isdir(os.path.join(base, name)):
                    self.user_combo.addItem(name)
        if self.user_combo.count() > 0:
            self._on_user_changed(0)

    def _on_user_changed(self, idx):
        if idx < 0:
            return
        user = self.user_combo.currentText()
        user_dir = os.path.join(self._base_dir(), user)
        self._build_gallery(user_dir)

    def _build_gallery(self, user_dir):
        # 기존 위젯 삭제
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self.thumbs = []

        if not os.path.isdir(user_dir):
            self.count_label.setText("폴더 없음")
            return

        # 포스트(서브폴더)별로 섹션 생성
        post_folders = sorted([f for f in os.listdir(user_dir)
                               if os.path.isdir(os.path.join(user_dir, f))])
        total_imgs = 0

        for folder_name in post_folders:
            folder_path = os.path.join(user_dir, folder_name)
            imgs = sorted([f for f in os.listdir(folder_path)
                          if f.lower().endswith((".jpg", ".jpeg", ".png"))])
            if not imgs:
                continue

            # 섹션 제목
            section = QFrame()
            section.setStyleSheet("background: #f9fafb; border-radius: 8px; padding: 8px;")
            sec_layout = QVBoxLayout(section)
            title = QLabel(f"{folder_name}  ({len(imgs)}장)")
            title.setFont(QFont("맑은 고딕", 11, QFont.Bold))
            sec_layout.addWidget(title)

            # 이미지 그리드
            grid = QHBoxLayout()
            grid.setSpacing(8)
            col = 0
            row_widgets = []
            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)
            sec_layout.addLayout(row_layout)

            for img_name in imgs:
                img_path = os.path.join(folder_path, img_name)
                thumb = LazyThumb(img_path)
                self.thumbs.append(thumb)
                total_imgs += 1
                row_layout.addWidget(thumb)
                col += 1
                if col >= COLS:
                    row_layout.addStretch()
                    col = 0
                    row_layout = QHBoxLayout()
                    row_layout.setSpacing(8)
                    sec_layout.addLayout(row_layout)
            if col > 0:
                row_layout.addStretch()

            self.grid_layout.addWidget(section)

        self.grid_layout.addStretch()
        self.count_label.setText(f"총 {len(post_folders)}개 포스트, {total_imgs}장 이미지")

        # 초기 로드 (보이는 썸네일만)
        QTimer.singleShot(50, self._load_visible)

    def _on_scroll(self):
        self._load_visible()

    def _load_visible(self):
        """현재 viewport에 보이는 썸네일만 이미지 로드"""
        viewport = self.scroll.viewport()
        vp_top = self.scroll.verticalScrollBar().value()
        vp_bottom = vp_top + viewport.height()
        # 프리로드 영역: viewport 위/아래 200px 여유
        preload = 200

        for thumb in self.thumbs:
            if thumb.loaded:
                continue
            # 썸네일 위치 (canvas 좌표)
            pos = thumb.mapTo(self.canvas, thumb.rect().topLeft())
            y_top = pos.y()
            y_bottom = y_top + thumb.height()
            if y_bottom + preload < vp_top:
                continue
            if y_top - preload > vp_bottom:
                continue
            thumb.load_image()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("맑은 고딕", 9))
    win = LazyGallery()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
