# -*- coding: utf-8 -*-
"""main.py의 실사+Pixabay 통합 플로우를 상용 전 빠르게 검증"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import real_photos as _rp
import image_handler as _ih
from users import load_users
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 테스트 업체: 법률사무소 + 요양원 섞어서
PLACES = [
    {"name": "법무법인 율촌", "place_id": "1523622973", "category": "변호사"},
    {"name": "개나리요양원", "place_id": "1951056467", "category": "요양원"},
]
OUT_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_integration_out")
TARGET_TOTAL = 3
pix_key = (load_users().get("admin", {}).get("api_keys", {}) or {}).get("pixabay_key_list", [""])[0]

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
        "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
    })
    return d

def main():
    os.makedirs(OUT_BASE, exist_ok=True)
    used_ids = os.path.join(OUT_BASE, "used_pixabay_ids.json")
    _ih.configure_used_ids_file(used_ids)
    def _log(msg): print(msg, flush=True)

    for p in PLACES:
        safe = p["name"].replace(" ", "")
        out_dir = os.path.join(OUT_BASE, safe)
        os.makedirs(out_dir, exist_ok=True)
        for f in os.listdir(out_dir):
            try: os.remove(os.path.join(out_dir, f))
            except: pass
        print(f"\n--- {p['name']} (place_id={p['place_id']}) ---", flush=True)

        # 실사 1장
        drv = _make_driver()
        try:
            real_paths = _rp.pick_real_photos(drv, p["place_id"], p["name"],
                                              target_real=1, out_dir=out_dir, emit_log=_log)
        finally:
            drv.quit()

        need = TARGET_TOTAL - len(real_paths)
        print(f"  실사 {len(real_paths)}장 + Pixabay {need}장 필요", flush=True)
        if need > 0:
            tmp = _ih.download_images(pix_key, p["category"], need)
            import shutil as _sh
            for i, tp in enumerate(tmp):
                dst = os.path.join(out_dir, f"pix_{i+1}.jpg")
                try:
                    _sh.copyfile(tp, dst)
                except Exception:
                    pass
        print(f"  최종 파일: {sorted(os.listdir(out_dir))}", flush=True)

if __name__ == "__main__":
    main()
