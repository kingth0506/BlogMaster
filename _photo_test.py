# -*- coding: utf-8 -*-
"""네이버 실사 크롤 + OpenCV 얼굴감지 + PIL 워터마크 + Pixabay 폴백 파이프라인 테스트"""
import sys, os, time, re, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np

OUT_DIR = os.path.expanduser(r"~/OneDrive/Desktop/실사테스트")
BLOG_ID = "kidth0506"
TARGET_REAL = 1    # 실사 1장
TARGET_TOTAL = 3   # 전체 3장 (부족분 Pixabay 보충)
PIXABAY_BIZ = "요양원"

def _get_pixabay_key():
    try:
        from users import load_users as _lu
        u = _lu().get("admin", {})
        ks = (u.get("api_keys") or {}).get("pixabay_key_list") or []
        return ks[0] if ks else ""
    except Exception:
        return ""

PIXABAY_API_KEY = _get_pixabay_key()


def _make_driver():
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--disable-blink-features=AutomationControlled")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--window-size=1920,1080")
    opt.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    opt.add_experimental_option("excludeSwitches", ["enable-automation"])
    d = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
    d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return d


def crawl_business_photos(driver, place_id: str, max_count: int = 30):
    """네이버 지도 place 사진 탭 > 업체 카테고리 이미지 URL + 업체명 수집"""
    driver.get(f"https://map.naver.com/p/entry/place/{place_id}?placePath=%2Fphoto")
    time.sleep(6)
    try:
        driver.switch_to.frame("entryIframe")
    except Exception:
        return [], ""
    time.sleep(2)
    # 업체명 추출 (GHAhO 또는 place_name 계열)
    biz_name = ""
    for sel in ["span.GHAhO", "h2.place_name", "h1", "span.Fc1rA", "span.YouOG"]:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            txt = (el.text or "").strip()
            if txt:
                biz_name = txt
                break
        except Exception:
            pass
    # 여러 탭 순회 (업체 → 외부 → 내부 → 메뉴) 하며 이미지 수집
    import urllib.parse as _up
    urls_raw = []
    TAB_ORDER = ["업체", "외부", "내부", "메뉴", "전체"]
    tabs_visited = set()
    def _collect_imgs():
        got = []
        for im in driver.find_elements(By.TAG_NAME, "img"):
            src = im.get_attribute("src") or ""
            # ldb-phinf.pstatic.net 만: 업체/리뷰 원본. blogfiles(네이버 합성 카드) 제외
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

    # 초기 (어떤 탭이든 자동 선택된 상태) 이미지 먼저 수집
    urls_raw += _collect_imgs()
    for tab in TAB_ORDER:
        if tab in tabs_visited:
            continue
        if _click_tab(tab):
            tabs_visited.add(tab)
            for _ in range(3):
                driver.execute_script("window.scrollBy(0, 1500);")
                time.sleep(1)
            urls_raw += _collect_imgs()
    urls_raw = list(dict.fromkeys(urls_raw))
    # src= 파라미터 추출 후 고해상도 래퍼로 재구성 (w1280_sharpen)
    finals = []
    seen_srcs = set()
    for u in urls_raw:
        try:
            q = _up.parse_qs(_up.urlparse(u).query)
            orig = q["src"][0] if "src" in q else u
            # blogfiles 경로는 합성 카드라 제외
            if "blogfiles.naver" in orig:
                continue
            if "ldb-phinf.pstatic.net" not in orig:
                continue
            if orig in seen_srcs:
                continue
            seen_srcs.add(orig)
            finals.append(orig)
        except Exception:
            pass
    final = finals[:max_count]
    driver.switch_to.default_content()
    return final, biz_name


_yunet = None
# 한글 경로 회피: 임시 폴더에 저장
import tempfile as _tf
_yunet_path = os.path.join(_tf.gettempdir(), "face_detection_yunet.onnx")

def _ensure_yunet():
    """YuNet 모델 파일 자동 다운로드 (처음 한 번만)"""
    global _yunet
    if _yunet is not None:
        return _yunet
    if not os.path.exists(_yunet_path):
        try:
            url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            with open(_yunet_path, "wb") as f:
                f.write(r.content)
            print(f"  YuNet 모델 다운로드 완료 ({len(r.content)//1024} KB)")
        except Exception as e:
            print(f"  [warn] YuNet 다운로드 실패, Haar 폴백: {e}")
            return None
    try:
        # score_threshold 0.9로 매우 보수적 — false positive 최소화
        _yunet = cv2.FaceDetectorYN.create(_yunet_path, "", (320, 320), 0.9, 0.3, 5000)
        return _yunet
    except Exception as e:
        print(f"  [warn] YuNet 생성 실패, Haar 폴백: {e}")
        return None


def has_person(img_path: str) -> bool:
    """YuNet DNN 얼굴 감지 — 사진 대비 너무 작은 얼굴(<5%)은 무시"""
    try:
        arr = np.fromfile(img_path, dtype=np.uint8)
        if arr.size == 0:
            return False
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return False
        H, W = img.shape[:2]
        min_face_w = W * 0.05  # 최소 얼굴 너비 = 이미지 가로의 5%
        det = _ensure_yunet()
        if det is not None:
            det.setInputSize((W, H))
            ret, faces = det.detect(img)
            if faces is not None and len(faces) > 0:
                # 각 얼굴: [x, y, w, h, 5 landmarks(10), score]
                for f in faces:
                    fw = float(f[2])
                    if fw >= min_face_w:
                        return True
                return False
        # YuNet 실패 시 Haar frontal 폴백
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = casc.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(int(min_face_w), int(min_face_w)))
        return len(faces) > 0
    except Exception as e:
        print(f"  [warn] person detect fail: {e}")
        return False


has_face = has_person


def add_watermark(img_path: str, text: str, out_path: str):
    """우하단 반투명(50%) 워터마크 — 기존 대비 3pt 정도 크게"""
    img = Image.open(img_path).convert("RGBA")
    W, H = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # 이미지 가로 × 3.3% + 3pt 추가분
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
    # 가독성 불필요 — 중복검출 회피용이라 픽셀값만 살짝 바꾸면 됨
    # 흰 본체 매우 옅게 (alpha 30)
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 30))
    out = Image.alpha_composite(img, overlay).convert("RGB")
    out.save(out_path, "JPEG", quality=92)


def download(url: str, out_path: str) -> bool:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"  [warn] download fail: {e}")
        return False


def run_test(place_id: str, folder_name: str, biz_type: str = "요양원"):
    print(f"\n=== place_id={place_id} biz={biz_type} ===")
    out_biz = os.path.join(OUT_DIR, folder_name)
    os.makedirs(out_biz, exist_ok=True)

    driver = _make_driver()
    try:
        urls, biz_name = crawl_business_photos(driver, place_id, max_count=20)
    finally:
        driver.quit()
    wm = biz_name or folder_name
    print(f"업체명: {biz_name}")

    print(f"수집된 사진 URL: {len(urls)}개")
    if not urls:
        print("  → 실사 없음 (Pixabay로 전부 대체해야 함)")
        return

    # 다운로드 + 얼굴 감지 + 파노라마/카드 필터
    rej_dir = os.path.join(out_biz, "_rejected")
    os.makedirs(rej_dir, exist_ok=True)
    kept = []
    rejected_face = []
    for i, url in enumerate(urls):
        raw_path = os.path.join(out_biz, f"raw_{i+1}.jpg")
        if not download(url, raw_path):
            continue
        if has_face(raw_path):
            rej_dst = os.path.join(rej_dir, f"rejected_{i+1}.jpg")
            os.replace(raw_path, rej_dst)
            rejected_face.append(rej_dst)
            print(f"  [{i+1}] 얼굴 감지 → 제외")
        else:
            kept.append(raw_path)
            print(f"  [{i+1}] OK [{url[:80]}]")
        if len(kept) >= TARGET_REAL:
            break

    print(f"얼굴 필터 후 확보: {len(kept)}장 (제외 {len(rejected_face)}장)")

    # 워터마크 적용 (실사만)
    finals = []
    for i, src in enumerate(kept):
        dst = os.path.join(out_biz, f"final_{i+1}.jpg")
        try:
            add_watermark(src, wm, dst)
            finals.append(dst)
            os.remove(src)
        except Exception as e:
            print(f"  [warn] watermark fail {src}: {e}")

    # Pixabay 폴백 — 중복 없는 ID로 전체 TARGET_TOTAL까지 채움
    need = TARGET_TOTAL - len(finals)
    if need > 0 and PIXABAY_API_KEY:
        import image_handler
        used_ids_file = os.path.join(OUT_DIR, "used_pixabay_ids.json")
        image_handler.configure_used_ids_file(used_ids_file)
        print(f"  Pixabay 보충 요청: {need}장 (업종: {biz_type})")
        paths = image_handler.download_images(PIXABAY_API_KEY, biz_type, need)
        import shutil as _sh
        for i, p in enumerate(paths):
            dst = os.path.join(out_biz, f"pixabay_{i+1}.jpg")
            try:
                _sh.copyfile(p, dst)
                finals.append(dst)
            except Exception as e:
                print(f"  [warn] pixabay copy fail: {e}")
    print(f"최종 {len(finals)}장 (실사 {len(kept)}장 + Pixabay {len(finals)-len(kept)}장)")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    TESTS = [
        ("36283072", "JY법률사무소", "변호사"),
        ("1523622973", "법무법인율촌", "변호사"),
        ("1533207449", "법무법인태림", "변호사"),
        ("1985582390", "법무법인테헤란", "변호사"),
        ("964297286", "법무법인더킴로펌", "변호사"),
    ]
    for pid, folder, biz in TESTS:
        run_test(pid, folder, biz)
    print(f"\n결과 저장: {OUT_DIR}")


if __name__ == "__main__":
    main()
