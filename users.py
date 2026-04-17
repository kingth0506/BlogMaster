# -*- coding: utf-8 -*-
"""사용자 인증 / 기간 관리 — Firebase Firestore 연동 (오프라인 시 로컬 fallback)"""
import hashlib
import json
import os
import datetime

try:
    from app_paths import data_file, get_bundle_dir
    LOCAL_FALLBACK = data_file("users.json")
    CRED_PATH = os.path.join(get_bundle_dir(), "firebase_credentials.json")
except Exception:
    LOCAL_FALLBACK = os.path.join(os.path.dirname(__file__), "users.json")
    CRED_PATH = os.path.join(os.path.dirname(__file__), "firebase_credentials.json")

COLLECTION = "users"

_db = None
_firebase_error = None


def _init_firebase():
    """Firestore 클라이언트 1회 초기화. 실패 시 로컬 fallback 사용."""
    global _db, _firebase_error
    if _db is not None:
        return _db
    if _firebase_error is not None:
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        if not os.path.exists(CRED_PATH):
            _firebase_error = f"credentials not found: {CRED_PATH}"
            return None
        if not firebase_admin._apps:
            cred = credentials.Certificate(CRED_PATH)
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
        return _db
    except Exception as e:
        _firebase_error = str(e)
        _db = None
        return None


def _hash(pw: str) -> str:
    return hashlib.sha256((pw or "").encode("utf-8")).hexdigest()


def _default_users() -> dict:
    return {
        "admin": {
            "pw": _hash("admin1234"),
            "role": "admin",
            "expires": "",
        }
    }


# ── 로컬 fallback (Firestore 불가 시) ──
def _load_local() -> dict:
    if not os.path.exists(LOCAL_FALLBACK):
        _save_local(_default_users())
    try:
        with open(LOCAL_FALLBACK, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _default_users()


def _save_local(users: dict):
    try:
        os.makedirs(os.path.dirname(LOCAL_FALLBACK), exist_ok=True)
    except Exception:
        pass
    try:
        with open(LOCAL_FALLBACK, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── Firestore CRUD ──
def load_users() -> dict:
    db = _init_firebase()
    if db is None:
        return _load_local()
    try:
        docs = db.collection(COLLECTION).stream()
        users = {}
        for d in docs:
            data = d.to_dict() or {}
            users[d.id] = {
                "pw": data.get("pw", ""),
                "role": data.get("role", "user"),
                "expires": data.get("expires", ""),
            }
        # 최초 1회: 비어있으면 admin 생성
        if not users:
            default = _default_users()
            for uid, u in default.items():
                db.collection(COLLECTION).document(uid).set(u)
            users = default
        _save_local(users)
        return users
    except Exception as e:
        globals()["_firebase_error"] = str(e)
        return _load_local()


def save_users(users: dict):
    db = _init_firebase()
    if db is None:
        _save_local(users)
        return
    try:
        for uid, u in users.items():
            db.collection(COLLECTION).document(uid).set({
                "pw": u.get("pw", ""),
                "role": u.get("role", "user"),
                "expires": u.get("expires", ""),
            })
        _save_local(users)
    except Exception:
        _save_local(users)


def verify(username: str, password: str):
    users = load_users()
    u = users.get(username)
    if not u:
        return None
    if u.get("pw") != _hash(password):
        return None
    return {"username": username, **u}


def is_expired(user: dict) -> bool:
    exp = (user.get("expires") or "").strip()
    if not exp:
        return False
    try:
        d = datetime.datetime.strptime(exp, "%Y-%m-%d").date()
        return datetime.date.today() > d
    except Exception:
        return False


def create_user(username: str, password: str, role: str = "user", expires: str = "") -> bool:
    users = load_users()
    if username in users:
        return False
    entry = {"pw": _hash(password), "role": role, "expires": expires}
    db = _init_firebase()
    if db is not None:
        try:
            db.collection(COLLECTION).document(username).set(entry)
        except Exception:
            pass
    users[username] = entry
    _save_local(users)
    return True


def update_user(username: str, password=None, role=None, expires=None) -> bool:
    users = load_users()
    u = users.get(username)
    if not u:
        return False
    if password:
        u["pw"] = _hash(password)
    if role is not None:
        u["role"] = role
    if expires is not None:
        u["expires"] = expires
    users[username] = u
    db = _init_firebase()
    if db is not None:
        try:
            db.collection(COLLECTION).document(username).set(u)
        except Exception:
            pass
    _save_local(users)
    return True


def delete_user(username: str) -> bool:
    if username == "admin":
        return False
    users = load_users()
    if username not in users:
        return False
    users.pop(username, None)
    db = _init_firebase()
    if db is not None:
        try:
            db.collection(COLLECTION).document(username).delete()
        except Exception:
            pass
    _save_local(users)
    return True


def get_status() -> str:
    """현재 연동 상태 문자열 (디버그용)"""
    db = _init_firebase()
    if db is not None:
        return "firestore_online"
    return f"local_fallback ({_firebase_error})"
