"""설정 관리 모듈 — 앱 로그인 유저별 네이버 계정 슬롯 분리"""
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

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
    "active_account": 0,
    "brand_connect": "",
    "connect": "",
    "connect_naver": "",
    "image_source": "auto",
}

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
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        merged = {**DEFAULT_CONFIG, **saved}
        abu = dict(merged.get("accounts_by_user") or {})
        # 구버전 마이그레이션: 기존 accounts → admin 유저에 귀속
        if not abu and saved.get("accounts"):
            abu["admin"] = _normalize_accounts(saved["accounts"])
        merged["accounts_by_user"] = abu
        # 현재 유저의 accounts 뷰
        merged["accounts"] = _normalize_accounts(abu.get(user, []))
        # 현재 유저의 active_account 뷰
        aabu = dict(merged.get("active_account_by_user") or {})
        merged["active_account_by_user"] = aabu
        merged["active_account"] = int(aabu.get(user, 0))
        return merged
    default = dict(DEFAULT_CONFIG)
    default["accounts"] = _empty_accounts()
    default["accounts_by_user"] = {}
    default["active_account_by_user"] = {}
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
    if "active_account" in cfg:
        aabu[user] = int(cfg.get("active_account", 0))

    out = dict(base)
    # cfg의 다른 키(공용 설정: AI키, pixabay 등)는 그대로 반영
    for k, v in cfg.items():
        if k in ("accounts", "active_account", "accounts_by_user", "active_account_by_user"):
            continue
        out[k] = v
    out["accounts_by_user"] = abu
    out["active_account_by_user"] = aabu
    # 하위 호환을 위해 현재 유저의 accounts 뷰도 최상위에 기록
    out["accounts"] = abu.get(user, _empty_accounts())
    out["active_account"] = aabu.get(user, 0)

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def get_active_account(cfg: dict) -> dict:
    idx = cfg.get("active_account", 0)
    accounts = cfg.get("accounts", _empty_accounts())
    if 0 <= idx < len(accounts):
        return accounts[idx]
    return accounts[0] if accounts else _empty_acc()


def get_taken_naver_ids(exclude_user: str = None) -> dict:
    """다른 앱-유저가 이미 등록한 네이버 ID 집합 → {naver_id_lower: app_user}"""
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
    except Exception:
        return {}
    abu = saved.get("accounts_by_user") or {}
    taken = {}
    for u, accs in abu.items():
        if exclude_user and u == exclude_user:
            continue
        for a in (accs or []):
            nid = (a.get("naver_id") or "").strip().lower()
            if nid:
                taken[nid] = u
    return taken
