# -*- coding: utf-8 -*-
"""앱 데이터 경로 관리 — 개발 모드는 현재폴더, 설치본(frozen)은 %APPDATA%\\NaverBlogAuto"""
import os
import sys
import shutil


def get_app_data_dir() -> str:
    """쓰기 가능한 사용자 데이터 폴더"""
    if getattr(sys, "frozen", False):
        base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "NaverBlogAuto")
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base, exist_ok=True)
    return base


def get_bundle_dir() -> str:
    """PyInstaller 패키지된 리소스 위치 (읽기 전용)"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(os.path.abspath(__file__))


def data_file(name: str) -> str:
    """데이터 파일 절대경로 (쓰기 가능 폴더 기준)"""
    return os.path.join(get_app_data_dir(), name)


def safe_load_json(path, default=None, max_mb: int = 40):
    """JSON을 안전하게 로드. 파일이 비정상적으로 크거나(폭주) 깨졌으면
    백업(.corrupt.bak) 후 default 반환 — 절대 예외를 올리지 않는다(앱 멈춤 방지)."""
    import json as _json
    if not os.path.exists(path):
        return default
    try:
        if os.path.getsize(path) > max_mb * 1024 * 1024:
            try:
                os.replace(path, path + ".corrupt.bak")
            except Exception:
                pass
            return default
    except Exception:
        pass
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        try:
            os.replace(path, path + ".corrupt.bak")
        except Exception:
            pass
        return default


def ensure_from_bundle(name: str):
    """번들된 기본 파일을 최초 실행시 사용자 폴더로 복사 (있으면 skip)"""
    dst = data_file(name)
    if os.path.exists(dst):
        return dst
    src = os.path.join(get_bundle_dir(), name)
    if os.path.exists(src):
        try:
            shutil.copy2(src, dst)
        except Exception:
            pass
    return dst
