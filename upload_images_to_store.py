# -*- coding: utf-8 -*-
"""사진올리기 — 업종별 사진을 GitHub 릴리즈(images)에 '청크 zip'으로 업로드.

사용법:
    python upload_images_to_store.py "C:\\경로\\이미지원본"
구조:
    이미지원본/
    ├── 이사/   (*.jpg *.png ...)
    ├── 미용실/
    └── 헬스장/

각 업종 사진을 CHUNK_N장씩 묶어 <slug>_cNN.zip 으로 업로드(자산 수가 적어 rate limit 회피).
zip 안의 사진은 내용해시(<md5>.확장자)로 이름 붙어 같은 사진은 자동 1개로 합쳐진다.
앱은 글 쓸 때 청크 1개(~수MB)만 받아 그 안에서 쓰고, 다양성이 필요해지면 청크를 하나씩 더 받는다.

manifest.json (schema 3):
  { "schema":3, "updated":"...",
    "categories": { "이사": {"slug":"cat_xxxx","count":1250,
                            "chunks":[{"file":"cat_xxxx_c00.zip","n":50,"hash":"..."}, ...]} } }

⚠️ images 릴리즈는 절대 latest로 표시되지 않게 한다(--latest=false).
   앱 업데이트 체크가 releases/latest(=vX.Y.Z)를 보기 때문.
"""
import os
import sys
import json
import time
import shutil
import hashlib
import zipfile
import tempfile
import subprocess
import datetime

REPO = "kingth0506/BlogMaster"
TAG = "images"
TITLE = "이미지 라이브러리"
IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp")
CHUNK_N = 50            # 청크당 사진 수 (zip 1개 ≈ 10MB 수준)
RETRY = 4              # 업로드 실패 시 재시도
BACKOFF = 90          # rate limit 시 대기(초)


def _slug(category: str) -> str:
    return "cat_" + hashlib.md5(category.encode("utf-8")).hexdigest()[:10]


def _list_images(folder: str):
    out = []
    for fn in sorted(os.listdir(folder)):
        p = os.path.join(folder, fn)
        if os.path.isfile(p) and fn.lower().endswith(IMG_EXTS):
            out.append(p)
    return out


def _file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _gh(args: list) -> int:
    return subprocess.call(["gh"] + args)


def _existing_assets() -> set:
    try:
        out = subprocess.check_output(
            ["gh", "release", "view", TAG, "-R", REPO, "--json", "assets",
             "-q", ".assets[].name"], text=True, stderr=subprocess.DEVNULL)
        return set(x.strip() for x in out.splitlines() if x.strip())
    except Exception:
        return set()


def _upload(path: str) -> bool:
    name = os.path.basename(path)
    for attempt in range(1, RETRY + 1):
        rc = _gh(["release", "upload", TAG, "-R", REPO, "--clobber", path])
        if rc == 0:
            return True
        if attempt < RETRY:
            print(f"    재시도 {attempt}/{RETRY - 1} (rate limit?) — {BACKOFF}초 대기: {name}")
            time.sleep(BACKOFF)
    return False


def main():
    if len(sys.argv) < 2:
        src = input("업종별 폴더가 들어있는 상위 폴더 경로를 입력하세요: ").strip().strip('"')
    else:
        src = sys.argv[1].strip().strip('"')
    if not os.path.isdir(src):
        print(f"[오류] 폴더가 없습니다: {src}")
        sys.exit(1)
    if subprocess.call(["gh", "auth", "status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
        print("[오류] gh CLI 로그인이 안 돼 있습니다. 먼저: gh auth login")
        sys.exit(1)

    work = tempfile.mkdtemp(prefix="imgstore_")
    categories = {}
    chunk_files = []      # 업로드할 zip 경로들
    total_imgs = 0

    print(f"\n[1/3] 업종별 청크 압축  (원본: {src}, 청크당 {CHUNK_N}장)")
    for name in sorted(os.listdir(src)):
        cdir = os.path.join(src, name)
        if not os.path.isdir(cdir):
            continue
        imgs = _list_images(cdir)
        if not imgs:
            print(f"  - {name}: 사진 없음, 건너뜀")
            continue
        slug = _slug(name)
        # 내용해시 이름으로 dedup
        named = {}   # asset_name -> src_path
        for p in imgs:
            ext = os.path.splitext(p)[1].lower()
            if ext == ".jpeg":
                ext = ".jpg"
            md5 = _file_md5(p)
            named.setdefault(f"{md5[:12]}{ext}", p)
        items = sorted(named.items())
        chunks_meta = []
        for ci in range(0, len(items), CHUNK_N):
            part = items[ci:ci + CHUNK_N]
            cn = ci // CHUNK_N
            zip_name = f"{slug}_c{cn:02d}.zip"
            zip_path = os.path.join(work, zip_name)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
                for aname, srcp in part:
                    zf.write(srcp, arcname=aname)
            chash = hashlib.md5("".join(a for a, _ in part).encode("utf-8")).hexdigest()[:12]
            chunks_meta.append({"file": zip_name, "n": len(part), "hash": chash})
            chunk_files.append(zip_path)
        categories[name] = {"slug": slug, "count": len(items), "chunks": chunks_meta}
        total_imgs += len(items)
        dup = len(imgs) - len(items)
        print(f"  - {name}: {len(items)}장 → 청크 {len(chunks_meta)}개" + (f" (중복 {dup}장 제외)" if dup else ""))

    if not categories:
        print("[오류] 업로드할 업종 폴더가 없습니다.")
        sys.exit(1)

    # 기존 릴리즈 manifest와 병합 — 다른 업종(예: 이사)은 그대로 두고 이번 업종만 추가/갱신
    existing_categories = {}
    try:
        import requests as _rq
        _r = _rq.get(f"https://github.com/{REPO}/releases/download/{TAG}/manifest.json", timeout=15)
        if _r.status_code == 200 and _r.content:
            _em = _r.json()
            if isinstance(_em, dict) and isinstance(_em.get("categories"), dict):
                existing_categories = _em["categories"]
                print(f"  기존 manifest 발견 → 기존 업종 유지: {list(existing_categories.keys())}")
    except Exception as _e:
        print(f"  (기존 manifest 없음/못 읽음 — 새로 만듦)")

    # 별칭(aliases) 적용: src/_aliases.json 에 {"요양원":["노인","할머니",...]} 형식으로 두면 반영.
    # 파일에 없으면 기존 manifest의 별칭을 그대로 유지(재업로드해도 안 사라짐).
    alias_map = {}
    _ap = os.path.join(src, "_aliases.json")
    if os.path.exists(_ap):
        try:
            alias_map = json.load(open(_ap, encoding="utf-8")) or {}
            print(f"  별칭 파일 적용: { {k: v for k, v in alias_map.items()} }")
        except Exception:
            alias_map = {}
    for cname, cinfo in categories.items():
        al = alias_map.get(cname)
        if al is None and cname in existing_categories:
            al = existing_categories[cname].get("aliases")  # 기존 별칭 유지
        if al:
            cinfo["aliases"] = [a for a in al if a]

    merged_categories = {**existing_categories, **categories}  # 같은 이름이면 이번 것으로 갱신
    manifest = {
        "schema": 3,
        "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "categories": merged_categories,
    }
    manifest_path = os.path.join(work, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n[2/3] manifest.json 생성  (이번 {len(categories)}개 / 전체 업종 {len(merged_categories)}개: {list(merged_categories.keys())} / 사진 {total_imgs}장 / 청크 {len(chunk_files)}개)")

    print(f"\n[3/3] GitHub 릴리즈 '{TAG}' 업로드")
    exists = subprocess.call(["gh", "release", "view", TAG, "-R", REPO],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    if not exists:
        print("  (images 릴리즈 새로 생성)")
        if _gh(["release", "create", TAG, "-R", REPO, "--title", TITLE,
                "--notes", "앱 이미지 라이브러리 (자동 업로드)", "--latest=false"]) != 0:
            print("[오류] 릴리즈 생성 실패")
            sys.exit(1)

    existing = _existing_assets()    # 재실행 시 이미 올린 청크는 건너뜀(resume)
    done = 0
    for zp in chunk_files:
        done += 1
        if os.path.basename(zp) in existing:
            print(f"  ({done}/{len(chunk_files)}) 건너뜀(이미 있음): {os.path.basename(zp)}")
            continue
        if not _upload(zp):
            print(f"[오류] 업로드 실패: {os.path.basename(zp)} — 잠시 후 같은 명령 재실행하면 이어서 올립니다.")
            sys.exit(1)
        print(f"  ({done}/{len(chunk_files)}) 업로드: {os.path.basename(zp)}")
        time.sleep(1)
    # manifest 는 맨 마지막 (목록과 자산 일치 보장)
    if not _upload(manifest_path):
        print("[오류] manifest 업로드 실패")
        sys.exit(1)

    print(f"\n✅ 완료! 업종 {len(categories)}개 / 사진 {total_imgs}장 / 청크 {len(chunk_files)}개 업로드됨")
    print(f"   https://github.com/{REPO}/releases/tag/{TAG}")
    print("   이제 사용자 앱이 글당 청크 1개만 받아 그 안에서 사진을 씁니다.")


if __name__ == "__main__":
    main()
