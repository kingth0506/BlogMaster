# -*- coding: utf-8 -*-
"""업체 실사 수집 + 얼굴 필터 + 워터마크 + Pixabay 폴백.

- collect_business_photos(driver, place_id, max_count): 원본(ldb-phinf) URL만 수집
- has_person(img_path): YuNet 얼굴 감지 (사진 가로 5% 미만 얼굴은 무시)
- add_watermark(img_path, text, out_path): 우하단 반투명 업체명 (alpha 30)
- prepare_images_for_place(...): 실사 1 + Pixabay 나머지 파이프라인
"""
import os
import sys
import time
import re
import tempfile
import urllib.parse
import requests
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from selenium.webdriver.common.by import By


# ── YuNet ─────────────────────────────────────────────────
_YUNET = None
_YUNET_PATH = os.path.join(tempfile.gettempdir(), "face_detection_yunet.onnx")


def _ensure_yunet():
    global _YUNET
    if _YUNET is not None:
        return _YUNET
    if not os.path.exists(_YUNET_PATH):
        try:
            url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            with open(_YUNET_PATH, "wb") as f:
                f.write(r.content)
        except Exception:
            return None
    try:
        _YUNET = cv2.FaceDetectorYN.create(_YUNET_PATH, "", (320, 320), 0.9, 0.3, 5000)
        return _YUNET
    except Exception:
        return None


def is_flyer(img_path: str, text_ratio_threshold: float = 0.30) -> bool:
    """전단지/메뉴판/가격표 감지 — 글자 영역 비중이 높으면 True.
    OpenCV 모폴로지 기반 텍스트 영역 추정. OCR 없이 가볍게.
    text_ratio_threshold: 이미지 대비 글자 영역 비율 임계값 (기본 30%)."""
    try:
        arr = np.fromfile(img_path, dtype=np.uint8)
        if arr.size == 0:
            return False
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return False
        H, W = img.shape[:2]
        if H < 50 or W < 50:
            return False
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # MSER로 글자후보 추출 → 모폴로지로 합친 영역 비율 계산
        # 적응형 임계화: 밝기 변화 무시하고 글자 에지 추출
        thr = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 15, 8,
        )
        # 가로 방향 커널로 글자 줄 연결
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(5, W // 40), 2))
        merged = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel)
        # 글자영역 후보 윤곽 추출
        contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        text_area = 0
        min_w, min_h = W * 0.04, H * 0.012
        max_h = H * 0.15  # 너무 큰 덩어리는 글자가 아니라 벽/배경
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w < min_w or h < min_h or h > max_h:
                continue
            # 가로세로비가 글자줄다운 형태만
            if w / max(h, 1) < 1.5:
                continue
            text_area += w * h
        ratio = text_area / (H * W)
        return ratio >= text_ratio_threshold
    except Exception:
        return False


def has_person(img_path: str) -> bool:
    """YuNet 얼굴 감지 — 사진 가로 5% 이상 크기의 얼굴만 인정"""
    try:
        arr = np.fromfile(img_path, dtype=np.uint8)
        if arr.size == 0:
            return False
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return False
        H, W = img.shape[:2]
        min_face_w = W * 0.05
        det = _ensure_yunet()
        if det is not None:
            det.setInputSize((W, H))
            ret, faces = det.detect(img)
            if faces is not None and len(faces) > 0:
                for f in faces:
                    if float(f[2]) >= min_face_w:
                        return True
                return False
        # 폴백: Haar
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = casc.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(int(min_face_w), int(min_face_w)))
        return len(faces) > 0
    except Exception:
        return False


# ── 워터마크 ──────────────────────────────────────────────
def add_watermark(img_path: str, text: str, out_path: str):
    """우하단 반투명(alpha 30) 업체명 워터마크"""
    img = Image.open(img_path).convert("RGBA")
    W, H = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font_size = max(18, int(W * 0.033) + 3)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = int(font_size * 0.4)
    x = W - tw - pad * 2
    y = H - th - pad * 2
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 30))
    out = Image.alpha_composite(img, overlay).convert("RGB")
    out.save(out_path, "JPEG", quality=92)


# ── 네이버 사진 수집 ──────────────────────────────────────
def collect_business_photos(driver, place_id: str, max_count: int = 20):
    """ldb-phinf.pstatic.net 원본 이미지 URL + 업체명 수집"""
    driver.get(f"https://map.naver.com/p/entry/place/{place_id}?placePath=%2Fphoto")
    time.sleep(6)
    try:
        driver.switch_to.frame("entryIframe")
    except Exception:
        return [], ""
    time.sleep(2)
    biz_name = ""
    for sel in ["span.GHAhO", "h2.place_name", "h1", "span.Fc1rA", "span.YouOG"]:
        try:
            txt = (driver.find_element(By.CSS_SELECTOR, sel).text or "").strip()
            if txt:
                biz_name = txt
                break
        except Exception:
            pass

    def _collect():
        got = []
        for im in driver.find_elements(By.TAG_NAME, "img"):
            src = im.get_attribute("src") or ""
            if "ldb-phinf.pstatic.net" in src:
                got.append(src)
        return got

    def _click_tab(text):
        for a in driver.find_elements(By.CSS_SELECTOR, "a, button"):
            t = (a.text or "").strip()
            if t == text:
                try:
                    driver.execute_script("arguments[0].click();", a)
                    time.sleep(2)
                    return True
                except Exception:
                    return False
        return False

    urls_raw = _collect()
    # "메뉴" 탭은 전단지/메뉴판/가격표 비중 높아 제외
    for tab in ("업체", "외부", "내부"):
        if _click_tab(tab):
            for _ in range(3):
                driver.execute_script("window.scrollBy(0, 1500);")
                time.sleep(1)
            urls_raw += _collect()
    urls_raw = list(dict.fromkeys(urls_raw))

    finals = []
    seen = set()
    for u in urls_raw:
        try:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
            orig = q["src"][0] if "src" in q else u
            if "blogfiles.naver" in orig:
                continue
            if "ldb-phinf.pstatic.net" not in orig:
                continue
            if orig in seen:
                continue
            seen.add(orig)
            finals.append(orig)
        except Exception:
            pass
    driver.switch_to.default_content()
    return finals[:max_count], biz_name


# ── 오케스트레이션 ────────────────────────────────────────
def download_url(url: str, out_path: str) -> bool:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception:
        return False


def pick_real_photos(driver, place_id: str, biz_name: str,
                     target_real: int, out_dir: str, emit_log=None) -> list:
    """place_id로 실사 수집 → 얼굴 필터 → 워터마크 → out_dir에 final_*.jpg 저장.
    반환: 저장된 파일 경로 리스트 (target_real장 이내)."""
    if not place_id:
        return []
    urls, _name = collect_business_photos(driver, place_id, max_count=20)
    if emit_log:
        emit_log(f"  실사 URL 수집: {len(urls)}개")
    kept = []
    tmp_dir = os.path.join(out_dir, "_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    for i, u in enumerate(urls):
        raw = os.path.join(tmp_dir, f"raw_{i+1}.jpg")
        if not download_url(u, raw):
            continue
        if has_person(raw) or is_flyer(raw):
            try: os.remove(raw)
            except: pass
            continue
        kept.append(raw)
        if len(kept) >= target_real:
            break
    # 워터마크 적용
    finals = []
    for i, src in enumerate(kept):
        dst = os.path.join(out_dir, f"image_{i+1}.jpg")
        try:
            add_watermark(src, biz_name or "", dst)
            finals.append(dst)
        except Exception:
            pass
        try: os.remove(src)
        except: pass
    # tmp 폴더 제거
    try:
        import shutil as _sh
        _sh.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass
    if emit_log:
        emit_log(f"  실사 확보: {len(finals)}장")
    return finals
