"""설정 관리 모듈 — 앱 로그인 유저별 네이버 계정 슬롯 분리"""
import json
import os
import sys

# users.json과 동일한 데이터 위치(app_paths.data_file)에 config.json 저장 → 경로 통일
try:
    from app_paths import data_file as _data_file
    CONFIG_FILE = _data_file("config.json")
except Exception:
    if getattr(sys, "frozen", False):
        _BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    else:
        _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_FILE = os.path.join(_BASE_DIR, "config.json")

MAX_ACCOUNTS = 9

_empty_acc = lambda: {"blog_id": "", "naver_id": "", "naver_pw": "", "blog_category": ""}
_empty_accounts = lambda: [_empty_acc() for _ in range(MAX_ACCOUNTS)]

DEFAULT_CONFIG = {
    "pixabay_api_key": "",
    "ai_provider": "GPT",
    "ai_api_key": "",
    "accounts": _empty_accounts(),
    "accounts_by_user": {},
    "active_account_by_user": {},
    "api_keys_by_user": {},
    "active_account": 0,
    "image_source": "auto",
}

API_KEY_FIELDS = ("gpt_key_list", "gemini_key_list", "pixabay_key_list")

# 현재 로그인한 앱-유저 (main.py에서 로그인 성공 시 set_current_user 호출)
_current_app_user = "admin"


def set_current_user(username: str):
    global _current_app_user
    _current_app_user = (username or "admin").strip() or "admin"


def get_current_user() -> str:
    return _current_app_user


def _normalize_accounts(accs: list) -> list:
    out = list(accs or [])
    while len(out) < MAX_ACCOUNTS:
        out.append(_empty_acc())
    return out[:MAX_ACCOUNTS]


def load_config() -> dict:
    user = _current_app_user
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
        except Exception:
            saved = {}
        merged = {**DEFAULT_CONFIG, **saved}
        abu = dict(merged.get("accounts_by_user") or {})
        # 구버전 마이그레이션: 기존 accounts → admin 유저에 귀속
        if not abu and saved.get("accounts"):
            abu["admin"] = _normalize_accounts(saved["accounts"])
        merged["accounts_by_user"] = abu
        # Firebase 사용자 레코드의 accounts 우선 적용 (cross-PC 동기화)
        try:
            from users import load_users as _lu_acc
            _fb_user = _lu_acc().get(user, {})
            _fb_accounts = _fb_user.get("accounts") or []
            if _fb_accounts:
                abu[user] = _fb_accounts
                merged["accounts_by_user"] = abu
        except Exception:
            pass
        # 현재 유저의 accounts 뷰
        merged["accounts"] = _normalize_accounts(abu.get(user, []))
        # 현재 유저의 active_account 뷰
        aabu = dict(merged.get("active_account_by_user") or {})
        merged["active_account_by_user"] = aabu
        merged["active_account"] = int(aabu.get(user, 0))
        # API 키: 사용자별 분리 (api_keys_by_user) — 구버전 root-level 키는 admin에게 귀속
        akbu = dict(merged.get("api_keys_by_user") or {})
        if not akbu and any(saved.get(k) for k in API_KEY_FIELDS):
            akbu["admin"] = {k: list(saved.get(k) or []) for k in API_KEY_FIELDS}
        merged["api_keys_by_user"] = akbu
        user_bucket = akbu.get(user, {})
        for kn in API_KEY_FIELDS:
            merged[kn] = list(user_bucket.get(kn, []))
        # Firebase 사용자 레코드에서 API 키 우선 적용 (관리자 어디서든 동기화)
        try:
            from users import load_users as _lu
            _u = _lu().get(user, {})
            online_keys = _u.get("api_keys", {}) or {}
            for kn in API_KEY_FIELDS:
                online = [k for k in (online_keys.get(kn) or []) if k]
                if online:
                    merged[kn] = list(online)
            shared = _u.get("shared_api_keys", {}) or {}
            if shared:
                for kn in API_KEY_FIELDS:
                    own = [k for k in merged.get(kn, []) if k]
                    if not own:
                        merged[kn] = list(shared.get(kn) or [])
                merged["_has_shared_keys"] = True
        except Exception as e:
            import sys
            print(f"[config.load_config] Firebase api 키 병합 실패: {e}", file=sys.stderr)
        return merged
    default = dict(DEFAULT_CONFIG)
    default["accounts"] = _empty_accounts()
    default["accounts_by_user"] = {}
    default["active_account_by_user"] = {}
    # 새 설치(config.json 없음) — Firebase에서 본인 accounts/api_keys 가져오기
    abu = {}
    try:
        from users import load_users as _lu_acc
        _fb_user = _lu_acc().get(user, {})
        _fb_accounts = _fb_user.get("accounts") or []
        if _fb_accounts:
            abu[user] = _fb_accounts
            default["accounts_by_user"] = abu
            default["accounts"] = _normalize_accounts(_fb_accounts)
        # API 키도 동일하게 — api_keys + shared_api_keys 병합
        akbu = {}
        online_keys = _fb_user.get("api_keys", {}) or {}
        for kn in API_KEY_FIELDS:
            online = [k for k in (online_keys.get(kn) or []) if k]
            if online:
                default[kn] = list(online)
        shared = _fb_user.get("shared_api_keys", {}) or {}
        if shared:
            for kn in API_KEY_FIELDS:
                own = [k for k in default.get(kn, []) if k]
                if not own:
                    default[kn] = list(shared.get(kn) or [])
            default["_has_shared_keys"] = True
    except Exception as e:
        import sys as _sys
        print(f"[config.load_config fresh] Firebase fetch 실패: {e}", file=_sys.stderr)
    return default


def save_config(cfg: dict):
    user = _current_app_user
    # 기존 파일 원본 유지 + 이번 유저 분만 덮어쓰기
    base = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                base = json.load(f)
        except Exception:
            base = {}

    # accounts_by_user / active_account_by_user 갱신
    abu = dict(base.get("accounts_by_user") or cfg.get("accounts_by_user") or {})
    aabu = dict(base.get("active_account_by_user") or cfg.get("active_account_by_user") or {})
    if "accounts" in cfg:
        abu[user] = _normalize_accounts(cfg["accounts"])
        # Firebase에 accounts 푸시 (cross-PC 동기화)
        try:
            from users import update_user as _upd
            _upd(user, accounts=abu[user])
        except Exception:
            pass
    if "active_account" in cfg:
        aabu[user] = int(cfg.get("active_account", 0))

    # API 키: save_config에서 api_keys_by_user는 건드리지 않음.
    # 런타임 cfg의 공유 키가 비관리자 본인 버킷으로 오염되는 것을 방지.
    # 키 저장은 settings_dialog._save()에서 is_admin일 때만 직접 파일 I/O로 처리.
    akbu = dict(base.get("api_keys_by_user") or {})
    if not akbu and any(base.get(k) for k in API_KEY_FIELDS):
        akbu["admin"] = {k: list(base.get(k) or []) for k in API_KEY_FIELDS}
    # cfg에 "_persist_api_keys_for_user" 가 있을 때만 그 유저 본인 버킷 덮어쓰기 (관리자 저장 경로)
    _persist_user = cfg.get("_persist_api_keys_for_user")
    if _persist_user:
        user_bucket = dict(akbu.get(_persist_user, {}))
        for k in API_KEY_FIELDS:
            if k in cfg:
                user_bucket[k] = [v for v in (cfg.get(k) or []) if v]
        akbu[_persist_user] = user_bucket

    out = dict(base)
    skip = {"accounts", "active_account", "accounts_by_user",
            "active_account_by_user", "api_keys_by_user", "_has_shared_keys",
            "_persist_api_keys_for_user"} | set(API_KEY_FIELDS)
    for k, v in cfg.items():
        if k in skip:
            continue
        out[k] = v
    # root-level API 키 흔적 제거
    for k in API_KEY_FIELDS:
        out.pop(k, None)
    out.pop("_has_shared_keys", None)
    out["accounts_by_user"] = abu
    out["active_account_by_user"] = aabu
    out["api_keys_by_user"] = akbu
    # 하위 호환을 위해 현재 유저의 accounts 뷰도 최상위에 기록
    out["accounts"] = abu.get(user, _empty_accounts())
    out["active_account"] = aabu.get(user, 0)

    _tmp = CONFIG_FILE + ".tmp"
    with open(_tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    os.replace(_tmp, CONFIG_FILE)


def get_active_account(cfg: dict) -> dict:
    idx = cfg.get("active_account", 0)
    accounts = cfg.get("accounts", _empty_accounts())
    if 0 <= idx < len(accounts):
        return accounts[idx]
    return accounts[0] if accounts else _empty_acc()


def get_taken_naver_ids(exclude_user: str = None) -> dict:
    """다른 앱-유저가 이미 등록한 네이버 ID 집합 → {naver_id_lower: app_user}.
    관리자(role=admin)가 등록한 ID는 전역 유일성 예외 — 다른 사용자도 사용 가능."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
    except Exception:
        return {}
    try:
        from users import load_users as _lu
        admin_uids = {u for u, d in _lu().items() if d.get("role") == "admin"}
    except Exception:
        admin_uids = set()
    abu = saved.get("accounts_by_user") or {}
    taken = {}
    for u, accs in abu.items():
        if exclude_user and u == exclude_user:
            continue
        if u in admin_uids:
            continue  # admin 등록 네이버 ID는 다른 사용자도 사용 허용
        for a in (accs or []):
            nid = (a.get("naver_id") or "").strip().lower()
            if nid:
                taken[nid] = u
    return taken
