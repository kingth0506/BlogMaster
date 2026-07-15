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
                "expires_2": data.get("expires_2", ""),
                "expires_3": data.get("expires_3", ""),
                "api_expires": data.get("api_expires", ""),
                "api_expires_2": data.get("api_expires_2", ""),
                "api_expires_3": data.get("api_expires_3", ""),
                "max_accounts": int(data.get("max_accounts", 3)),
                "name": data.get("name", ""),
                "birth": data.get("birth", ""),
                "phone": data.get("phone", ""),
                "referrer": data.get("referrer", ""),
                "email": data.get("email", ""),
                "shared_api_keys": data.get("shared_api_keys", {}),
                "shared_api_keys_admin_granted": data.get("shared_api_keys_admin_granted", False),
                "shared_api_grace_until": data.get("shared_api_grace_until", ""),
                "api_keys": data.get("api_keys", {}),
                "accounts": data.get("accounts", []),
                "locked_naver_ids": data.get("locked_naver_ids", []),
                "prompts": data.get("prompts", {}),
                "keywordmaster_enabled": data.get("keywordmaster_enabled", False),
                "privacy_consent": data.get("privacy_consent", False),
                "privacy_consent_date": data.get("privacy_consent_date", ""),
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
                "expires_2": u.get("expires_2", ""),
                "expires_3": u.get("expires_3", ""),
                "api_expires": u.get("api_expires", ""),
                "api_expires_2": u.get("api_expires_2", ""),
                "api_expires_3": u.get("api_expires_3", ""),
                "max_accounts": int(u.get("max_accounts", 3)),
                "name": u.get("name", ""),
                "birth": u.get("birth", ""),
                "phone": u.get("phone", ""),
                "referrer": u.get("referrer", ""),
                "email": u.get("email", ""),
                "shared_api_keys": u.get("shared_api_keys", {}),
                "shared_api_keys_admin_granted": u.get("shared_api_keys_admin_granted", False),
                "shared_api_grace_until": u.get("shared_api_grace_until", ""),
                "api_keys": u.get("api_keys", {}),
                "accounts": u.get("accounts", []),
                "locked_naver_ids": u.get("locked_naver_ids", []),
                "prompts": u.get("prompts", {}),
                "keywordmaster_enabled": u.get("keywordmaster_enabled", False),
                "privacy_consent": u.get("privacy_consent", False),
                "privacy_consent_date": u.get("privacy_consent_date", ""),
            })
        _save_local(users)
    except Exception as e:
        import sys
        print(f"[users.save_users] Firebase 저장 실패: {e}", file=sys.stderr)
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
    return is_account_expired(user, slot=1)


def is_account_expired(user: dict, slot: int = 1) -> bool:
    """명의(계정 슬롯)별 이용기간 만료 여부. slot=1,2,3.
    - 관리자: 항상 False
    - 1명의 빈값: 무제한(관리자 부여/레거시) → 만료 아님
    - 2·3명의 빈값: '사용 불가'(무료 제공 안 함) → 만료 취급(차단)
    - 날짜 있으면: 오늘 > 만료일 이면 만료"""
    if (user or {}).get("role") == "admin":
        return False
    field = "expires" if slot == 1 else f"expires_{slot}"
    exp = (user.get(field) or "").strip()
    if not exp:
        return True  # 빈값 = 사용불가(차단). 무제한은 먼 미래 날짜(2099-12-31)로 부여한다.
    try:
        d = datetime.datetime.strptime(exp, "%Y-%m-%d").date()
        return datetime.date.today() > d
    except Exception:
        return False


def create_user(username: str, password: str, role: str = "user", expires: str = "", max_accounts: int = 3,
                name: str = "", birth: str = "", phone: str = "", referrer: str = "", email: str = "") -> bool:
    users = load_users()
    if username in users:
        return False
    entry = {"pw": _hash(password), "role": role, "expires": expires, "max_accounts": max_accounts,
             "name": name, "birth": birth, "phone": phone, "referrer": referrer, "email": email}
    db = _init_firebase()
    if db is not None:
        try:
            db.collection(COLLECTION).document(username).set(entry)
        except Exception as e:
            import sys
            print(f"[users.create_user] Firebase 쓰기 실패 ({username}): {e}", file=sys.stderr)
    users[username] = entry
    _save_local(users)
    return True


def update_user(username: str, password=None, role=None, expires=None, expires_2=None, expires_3=None,
                api_expires=None, api_expires_2=None, api_expires_3=None,
                max_accounts=None, email=None, shared_api_keys=None, api_keys=None,
                accounts=None, locked_naver_ids=None, prompts=None, keywordmaster_enabled=None,
                privacy_consent=None, privacy_consent_date=None,
                shared_api_keys_admin_granted=None, shared_api_grace_until=None) -> bool:
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
    if expires_2 is not None:
        u["expires_2"] = expires_2
    if expires_3 is not None:
        u["expires_3"] = expires_3
    if api_expires is not None:
        u["api_expires"] = api_expires
    if api_expires_2 is not None:
        u["api_expires_2"] = api_expires_2
    if api_expires_3 is not None:
        u["api_expires_3"] = api_expires_3
    if max_accounts is not None:
        u["max_accounts"] = int(max_accounts)
    if email is not None:
        u["email"] = email
    if shared_api_keys is not None:
        u["shared_api_keys"] = shared_api_keys
    if shared_api_keys_admin_granted is not None:
        u["shared_api_keys_admin_granted"] = shared_api_keys_admin_granted
    if shared_api_grace_until is not None:
        u["shared_api_grace_until"] = shared_api_grace_until
    if api_keys is not None:
        u["api_keys"] = api_keys
    if accounts is not None:
        u["accounts"] = accounts
    if locked_naver_ids is not None:
        u["locked_naver_ids"] = locked_naver_ids
    if prompts is not None:
        u["prompts"] = prompts
    if keywordmaster_enabled is not None:
        u["keywordmaster_enabled"] = keywordmaster_enabled
    if privacy_consent is not None:
        u["privacy_consent"] = privacy_consent
    if privacy_consent_date is not None:
        u["privacy_consent_date"] = privacy_consent_date
    users[username] = u
    db = _init_firebase()
    if db is not None:
        try:
            db.collection(COLLECTION).document(username).set(u)
        except Exception as e:
            import sys
            print(f"[users.update_user] Firebase 쓰기 실패 ({username}): {e}", file=sys.stderr)
    _save_local(users)
    return True


def is_api_expired(user: dict, slot: int = 1) -> bool:
    """API 구독 만료 여부. slot=1,2,3. 빈 문자열이면 구독 없음(만료 취급).
    - 관리자: 항상 False (만료 아님)"""
    if (user or {}).get("role") == "admin":
        return False
    key = "api_expires" if slot == 1 else f"api_expires_{slot}"
    exp = (user.get(key) or "").strip()
    if not exp:
        return True
    try:
        d = datetime.datetime.strptime(exp, "%Y-%m-%d").date()
        return datetime.date.today() > d
    except Exception:
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
        except Exception as e:
            import sys
            print(f"[users.delete_user] Firebase 삭제 실패 ({username}): {e}", file=sys.stderr)
    _save_local(users)
    return True


def find_user_by_identity(name: str, phone: str, email: str):
    """이름+전화번호+이메일 일치하는 사용자 username 반환. 없으면 None."""
    import re as _re
    def _norm_phone(p):
        return _re.sub(r"\D", "", p or "")
    name = (name or "").strip()
    email = (email or "").strip().lower()
    users = load_users()
    for uid, u in users.items():
        if uid == "admin":
            continue
        if ((u.get("name", "") or "").strip() == name
                and _norm_phone(u.get("phone", "")) == _norm_phone(phone)
                and (u.get("email", "") or "").strip().lower() == email):
            return uid
    return None


def get_status() -> str:
    """현재 연동 상태 문자열 (디버그용)"""
    db = _init_firebase()
    if db is not None:
        return "firestore_online"
    return f"local_fallback ({_firebase_error})"


# ── 중복 로그인 방지 세션 관리 ──
SESSION_TTL_MINUTES = 10


def check_session_conflict(username: str) -> bool:
    """여러 컴퓨터에서 동시 로그인 허용 — 중복 세션 검사 비활성화.
    (이전: 다른 기기에 활성 세션이 있으면 True로 로그인 차단했으나,
     한 아이디를 여러 PC에서 쓰도록 항상 False 반환.)"""
    return False


def set_session(username: str, session_id: str):
    """로그인 시 세션 등록."""
    db = _init_firebase()
    if db is None:
        return
    try:
        from firebase_admin import firestore as _fs
        db.collection(COLLECTION).document(username).update({
            "session_id": session_id,
            "session_heartbeat": _fs.SERVER_TIMESTAMP,
        })
    except Exception:
        pass


def clear_session(username: str, session_id: str):
    """앱 종료 시 본인 세션만 삭제."""
    db = _init_firebase()
    if db is None:
        return
    try:
        doc = db.collection(COLLECTION).document(username).get()
        if doc.exists and (doc.to_dict() or {}).get("session_id") == session_id:
            db.collection(COLLECTION).document(username).update({
                "session_id": None,
                "session_heartbeat": None,
            })
    except Exception:
        pass


def heartbeat_session(username: str, session_id: str):
    """5분마다 호출해서 세션 유지."""
    db = _init_firebase()
    if db is None:
        return
    try:
        from firebase_admin import firestore as _fs
        doc = db.collection(COLLECTION).document(username).get()
        if doc.exists and (doc.to_dict() or {}).get("session_id") == session_id:
            db.collection(COLLECTION).document(username).update({
                "session_heartbeat": _fs.SERVER_TIMESTAMP,
            })
    except Exception:
        pass


# ── 포스팅 히스토리 ──
HISTORY_COLLECTION = "posting_history"


def add_posting_history(app_user: str, blog_id: str, place_name: str,
                        place_address: str, keyword: str, title: str,
                        schedule_time: str = None):
    """포스팅 성공 시 Firestore에 히스토리 기록. 실패해도 무시."""
    db = _init_firebase()
    if db is None:
        return
    try:
        from firebase_admin import firestore as _fs
        import datetime as _dt
        db.collection(HISTORY_COLLECTION).add({
            "app_user": app_user,
            "blog_id": blog_id,
            "place_name": place_name,
            "place_address": place_address,
            "keyword": keyword,
            "title": title,
            "schedule_time": schedule_time or "",
            "posted_at": _fs.SERVER_TIMESTAMP,
        })
    except Exception:
        pass
