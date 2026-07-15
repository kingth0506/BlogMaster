# -*- coding: utf-8 -*-
"""로컬 이미지 라이브러리 — GitHub 릴리즈(images)에서 업종별 사진을 '청크'로 받아 캐시·매칭.

배포 구조 (upload_images_to_store.py 가 만드는 규격, schema 3):
  GitHub 릴리즈 tag=images 에
    <slug>_cNN.zip ...   ← 업종 사진을 CHUNK_N장씩 묶은 청크 zip (zip 안 사진은 <내용해시>.jpg)
    manifest.json        ← 아래 형식
  manifest.json:
    { "schema":3, "updated":"...",
      "categories": { "이사": {"slug":"cat_xxxx","count":1250,
                              "chunks":[{"file":"cat_xxxx_c00.zip","n":50,"hash":"..."}, ...]} } }

앱은 글 쓸 때 키워드(업종)로 manifest에서 업종을 유연 매칭 →
청크 1개(~수MB)만 받아 그 안의 사진을 쓴다. 다양성이 필요해지면(이미 받은 사진을 다 씀)
청크를 하나씩 더 받는다 → '쓰는 만큼만' 다운로드. 첫 포스팅도 빠름.
매칭/네트워크 실패는 [] 반환 → download_images가 픽사베이로 폴백/보충.
"""
import os
import io
import json
import time
import random
import zipfile
import threading

import requests

try:
    from app_paths import get_app_data_dir
except Exception:  # 단독 테스트 대비
    def get_app_data_dir():
        return os.path.dirname(os.path.abspath(__file__))

# ── 배포 대상 (업로더와 동일해야 함) ──────────────────────────────
REPO = "kingth0506/BlogMaster"
TAG = "images"
_ASSET_BASE = f"https://github.com/{REPO}/releases/download/{TAG}"
MANIFEST_URL = f"{_ASSET_BASE}/manifest.json"

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp")

_LOCK = threading.Lock()
_ENABLED = True
_CACHE_DIR = ""
_MANIFEST = None
_MANIFEST_TS = 0.0
_MANIFEST_TTL = 6 * 3600     # 6시간마다 manifest 재확인
_USED = {}                   # {category: set(filename)}  세션/영속 중복회피
_USED_LOADED = False


# ── 설정 / 경로 ──────────────────────────────────────────────────
def configure(enabled: bool = True, cache_dir: str = ""):
    """앱 시작 시 1회 호출(선택). 안 불러도 첫 사용 시 기본값으로 lazy-init."""
    global _ENABLED, _CACHE_DIR
    _ENABLED = bool(enabled)
    if cache_dir:
        _CACHE_DIR = cache_dir


def _cache_root() -> str:
    global _CACHE_DIR
    if not _CACHE_DIR:
        _CACHE_DIR = os.path.join(get_app_data_dir(), "image_library")
    os.makedirs(_CACHE_DIR, exist_ok=True)
    return _CACHE_DIR


def _slug_dir(slug: str) -> str:
    d = os.path.join(_cache_root(), "lib", slug)
    os.makedirs(d, exist_ok=True)
    return d


def _used_path() -> str:
    return os.path.join(_cache_root(), "used_images.json")


def _load_used():
    global _USED, _USED_LOADED
    if _USED_LOADED:
        return
    _USED_LOADED = True
    try:
        from app_paths import safe_load_json as _slj
        data = _slj(_used_path(), default={}, max_mb=20) or {}
        _USED = {k: set(v) for k, v in data.items()}
    except Exception:
        _USED = {}


def _save_used():
    try:
        data = {k: sorted(v) for k, v in _USED.items()}
        json.dump(data, open(_used_path(), "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


# ── manifest 로드 (릴리즈에서, 캐시 폴백) ────────────────────────
def _local_manifest_path() -> str:
    return os.path.join(_cache_root(), "manifest.json")


def _load_manifest(force: bool = False):
    global _MANIFEST, _MANIFEST_TS
    now = time.time()
    if (not force) and _MANIFEST is not None and (now - _MANIFEST_TS) < _MANIFEST_TTL:
        return _MANIFEST
    try:
        # 캐시 우회(t=타임스탬프) — GitHub CDN이 옛 manifest를 주는 것 방지(새 업종 즉시 반영)
        r = requests.get(MANIFEST_URL, params={"t": int(time.time())},
                         headers={"Cache-Control": "no-cache"}, timeout=10)
        if r.status_code == 200 and r.content:
            m = r.json()
            if isinstance(m, dict) and isinstance(m.get("categories"), dict):
                _MANIFEST = m
                _MANIFEST_TS = now
                try:
                    with open(_local_manifest_path(), "w", encoding="utf-8") as f:
                        json.dump(m, f, ensure_ascii=False)
                except Exception:
                    pass
                return _MANIFEST
    except Exception:
        pass
    if _MANIFEST is None:
        try:
            p = _local_manifest_path()
            if os.path.exists(p):
                m = json.load(open(p, "r", encoding="utf-8"))
                if isinstance(m, dict) and isinstance(m.get("categories"), dict):
                    _MANIFEST = m
                    _MANIFEST_TS = now
        except Exception:
            _MANIFEST = None
    return _MANIFEST


# ── 키워드 → 업종 유연 매칭 ──────────────────────────────────────
def _match_category(keyword: str):
    """업종명이 키워드 안에 부분 포함되면 매칭(긴 이름 우선). 지역명/수식어 붙어도 됨.
    없으면 None → 픽사베이."""
    m = _load_manifest()
    if not m:
        return None
    cats = m.get("categories", {})
    if not cats:
        return None
    k = (keyword or "").strip().lower()
    if not k:
        return None
    for sep in (">", "/", ",", "·", "|"):
        k = k.replace(sep, " ")
    # (매칭어, 업종) 목록: 업종명 + 별칭(aliases). 긴 매칭어 우선.
    terms = []
    for name, info in cats.items():
        terms.append((name.lower(), name))
        for a in (info.get("aliases") or []):
            if a and str(a).strip():
                terms.append((str(a).strip().lower(), name))
    terms.sort(key=lambda t: len(t[0]), reverse=True)
    for term, name in terms:                   # 1) 키워드 전체에 부분 포함
        if term and term in k:
            return name
    toks = [t for t in k.split() if t]
    for tok in reversed(toks):                 # 2) 토큰 단위(구체적인 뒤 토큰부터)
        for term, name in terms:
            if term and (term in tok or tok in term):
                return name
    return None


# ── 청크 다운로드/해제 ──────────────────────────────────────────
def _chunk_stem(chunk: dict) -> str:
    return os.path.splitext(chunk.get("file", ""))[0] or "c"


def _downloaded_files(slug: str) -> list:
    """이미 받아 풀어둔 청크들의 이미지 파일 경로 전체."""
    base = _slug_dir(slug)
    out = []
    for stem in os.listdir(base):
        d = os.path.join(base, stem)
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if fn.lower().endswith(_IMG_EXTS):
                out.append(os.path.join(d, fn))
    return out


def _has_chunk(slug: str, chunk: dict) -> bool:
    d = os.path.join(_slug_dir(slug), _chunk_stem(chunk))
    if not os.path.isdir(d):
        return False
    return any(f.lower().endswith(_IMG_EXTS) for f in os.listdir(d))


def _download_chunk(slug: str, chunk: dict) -> bool:
    """청크 zip 하나를 받아 lib/<slug>/<stem>/ 에 푼다. 성공 여부 반환."""
    stem = _chunk_stem(chunk)
    d = os.path.join(_slug_dir(slug), stem)
    try:
        r = requests.get(f"{_ASSET_BASE}/{chunk.get('file')}", timeout=120)
        r.raise_for_status()
        os.makedirs(d, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            for zi in zf.infolist():
                if zi.is_dir():
                    continue
                base = os.path.basename(zi.filename)
                if not base or not base.lower().endswith(_IMG_EXTS):
                    continue
                with zf.open(zi) as s, open(os.path.join(d, base), "wb") as o:
                    o.write(s.read())
        return True
    except Exception:
        return False


def _pull_one_more_chunk(slug: str, chunks: list) -> bool:
    """아직 안 받은 청크 중 무작위로 하나 더 받는다. 받았으면 True."""
    not_yet = [c for c in chunks if not _has_chunk(slug, c)]
    if not_yet:
        return _download_chunk(slug, random.choice(not_yet))
    return False


# ── 선택 (중복 회피) ────────────────────────────────────────────
def _pick(name: str, files: list, count: int) -> list:
    """받아둔 사진들 중 distinct 랜덤 최대 count개. 한 바퀴 다 쓰면 리셋."""
    _load_used()
    used = _USED.setdefault(name, set())
    pool = [f for f in files if os.path.basename(f) not in used]
    if not pool:
        used.clear()
        pool = list(files)
    random.shuffle(pool)
    chosen = pool[:count]
    for f in chosen:
        used.add(os.path.basename(f))
    _save_used()
    return chosen


# ── 공개 API ────────────────────────────────────────────────────
def fetch(keyword: str, count: int) -> list:
    """키워드에 맞는 로컬 라이브러리 사진을 최대 count장 받아 경로 반환.
    청크 1개만 받아 그 안에서 쓰고, 받아둔 사진을 다 썼으면 청크를 하나 더 받아 다양성 확보.
    매칭 실패/비활성/네트워크 실패 → []  (호출부가 픽사베이로 폴백/보충)."""
    if not _ENABLED or count <= 0:
        return []
    try:
        with _LOCK:
            name = _match_category(keyword)
            if not name:
                return []
            info = (_load_manifest().get("categories") or {}).get(name) or {}
            slug = info.get("slug")
            chunks = info.get("chunks") or []
            if not slug or not chunks:
                return []

            files = _downloaded_files(slug)
            if not files:                       # 첫 사용 → 청크 1개 받기
                if not _pull_one_more_chunk(slug, chunks):
                    return []
                files = _downloaded_files(slug)
                if not files:
                    return []

            # 받아둔 사진의 미사용분이 부족하고, 아직 안 받은 청크가 있으면 하나 더 받아 다양성↑
            _load_used()
            used = _USED.get(name, set())
            unused = [f for f in files if os.path.basename(f) not in used]
            if len(unused) < count and any(not _has_chunk(slug, c) for c in chunks):
                if _pull_one_more_chunk(slug, chunks):
                    files = _downloaded_files(slug)

            return _pick(name, files, count)
    except Exception:
        return []


def has_category(keyword: str) -> bool:
    try:
        return _match_category(keyword) is not None
    except Exception:
        return False
