# -*- coding: utf-8 -*-
"""네이버 모바일 검색 기반 플레이스 크롤러 (requests + BeautifulSoup)

고정 URL https://m.search.naver.com/search.naver?query={keyword} 의
HTML(Apollo 상태)에서 상호명·지번 주소를 파싱하고, 추가 페이지는
동일 모바일 파이프라인 GraphQL로 이어서 수집한다.
"""
import json
import random
import re
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup


SEARCH_URL = "https://m.search.naver.com/search.naver"
GRAPHQL_URL = "https://api.place.naver.com/graphql"
PAGE_SIZE = 20

_MOBILE_UA_POOL = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918N) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
]

_GRAPHQL_QUERY = """
query getPlaceList($input: PlaceListInput!) {
  placeList(input: $input) {
    businesses {
      total
      items {
        id
        name
        address
        commonAddress
        category
        subwayId
        x
        y
      }
    }
  }
}
"""


def build_mobile_headers(*, json_request: bool = False) -> dict:
    """모바일 기기 User-Agent를 포함한 요청 헤더."""
    headers = {
        "User-Agent": random.choice(_MOBILE_UA_POOL),
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Referer": "https://m.search.naver.com/",
    }
    if json_request:
        headers["Accept"] = "application/json, text/plain, */*"
        headers["Content-Type"] = "application/json"
    else:
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    return headers


def _clean_text(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def split_address_tokens(common_address: str) -> dict:
    """commonAddress('서울 강남구 역삼동')를 공백 단위로 시/구/동 분리."""
    parts = (common_address or "").split()
    return {
        "시": parts[0] if len(parts) >= 1 else "",
        "구": parts[1] if len(parts) >= 2 else "",
        "동": parts[2] if len(parts) >= 3 else "",
    }


def build_jibun_address(common_address: str, jibun_detail: str) -> str:
    """행정동(commonAddress) + 지번(detail)을 하나의 지번 주소 문자열로 합친다."""
    common = (common_address or "").strip()
    detail = (jibun_detail or "").strip()
    if not common:
        return detail
    if not detail:
        return common

    tokens = split_address_tokens(common)
    dong = tokens["동"]
    if dong and detail.startswith(dong):
        suffix = detail[len(dong):].strip()
        return f"{common} {suffix}".strip() if suffix else common
    return f"{common} {detail}".strip()


def normalize_place_item(raw: dict) -> dict:
    """Apollo/GraphQL 원본을 공통 place dict로 정규화."""
    name = _clean_text(raw.get("name") or "")
    common = (raw.get("commonAddress") or "").strip()
    detail = (raw.get("address") or "").strip()
    parsed = split_address_tokens(common)
    jibun = build_jibun_address(common, detail)
    dong = parsed["동"] or _extract_dong_from_detail(detail)

    return {
        "name": name,
        "address": common or jibun,
        "jibun_address": jibun,
        "category": (raw.get("category") or "").strip(),
        "시": parsed["시"],
        "구": parsed["구"],
        "동": dong,
        "place_id": str(raw.get("id") or "").strip(),
        "nearby_station": "",
        "x": str(raw.get("x") or "").strip(),  # 경도(lng)
        "y": str(raw.get("y") or "").strip(),  # 위도(lat)
    }


def _extract_dong_from_detail(detail: str) -> str:
    match = re.search(r"(\S+동)\b", detail or "")
    return match.group(1) if match else ""


def extract_apollo_state(html: str) -> dict:
    """script 태그에서 __APOLLO_STATE__ JSON 추출."""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        text = script.string or script.get_text() or ""
        if "__APOLLO_STATE__" not in text:
            continue
        idx = text.find("__APOLLO_STATE__")
        brace = text.find("{", idx)
        if brace == -1:
            continue
        depth = 0
        in_str = False
        esc = False
        for i in range(brace, len(text)):
            ch = text[i]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace:i + 1])
                    except json.JSONDecodeError:
                        return {}
        return {}
    return {}


def parse_places_from_apollo(state: dict) -> list[dict]:
    """Apollo 상태 dict에서 PlaceListBusinessesItem 목록 추출."""
    rows = []
    seen = set()
    for obj in state.values():
        if not isinstance(obj, dict):
            continue
        if obj.get("__typename") != "PlaceListBusinessesItem":
            continue
        place = normalize_place_item(obj)
        if not place["name"] or place["name"] in seen:
            continue
        seen.add(place["name"])
        rows.append(place)
    return rows


def _is_blocked_html(html: str) -> bool:
    if not html:
        return True
    blocked_markers = (
        "서비스 이용이 제한되었습니다",
        "비정상적인 접근",
        "자동화된 접근",
        "보안문자",
    )
    return any(marker in html for marker in blocked_markers)


def _request_with_backoff(method: str, url: str, *, max_retries: int = 4, **kwargs):
    """429(Too Many Requests)/5xx 시 백오프 재시도. 성공 resp 또는 None.

    대량(서울 전구 등) 크롤 후반에 throttle 걸려도 잠깐 쉬고 재시도해 누락 방지.
    """
    delay = 3.0
    for attempt in range(max_retries):
        try:
            resp = requests.request(method, url, **kwargs)
        except requests.RequestException:
            return None
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt < max_retries - 1:
                time.sleep(delay + random.uniform(0, 1.0))
                delay = min(delay * 2, 30.0)
                continue
            return None
        return resp
    return None


def fetch_places_html(keyword: str, timeout: int = 15) -> tuple[list[dict], int]:
    """모바일 검색 HTML 1페이지 파싱 (BeautifulSoup + Apollo)."""
    resp = _request_with_backoff(
        "GET", SEARCH_URL,
        params={"query": keyword},
        headers=build_mobile_headers(),
        timeout=timeout,
    )
    if resp is None or resp.status_code != 200:
        return [], 0

    if _is_blocked_html(resp.text):
        return [], 0

    state = extract_apollo_state(resp.text)
    if not state:
        return [], 0

    total = 0
    for obj in state.values():
        if isinstance(obj, dict) and obj.get("__typename") == "PlaceListResult":
            total = int(obj.get("businesses", {}).get("total") or 0)
            break

    return parse_places_from_apollo(state), total


def fetch_places_graphql(keyword: str, start: int = 1, display: int = PAGE_SIZE,
                         timeout: int = 15) -> tuple[list[dict], int]:
    """모바일 GraphQL로 플레이스 페이지 수집 (start는 1-based)."""
    payload = {
        "operationName": "getPlaceList",
        "variables": {
            "input": {
                "query": keyword,
                "start": start,
                "display": display,
                "deviceType": "mobile",
                "businessType": "place",
                "adult": False,
                "isNx": True,
                "ssc": "tab.m.all",
            }
        },
        "query": _GRAPHQL_QUERY,
    }
    resp = _request_with_backoff(
        "POST", GRAPHQL_URL,
        json=payload,
        headers=build_mobile_headers(json_request=True),
        timeout=timeout,
    )
    if resp is None or resp.status_code != 200:
        return [], 0
    try:
        data = resp.json()
    except ValueError:
        return [], 0

    businesses = (
        data.get("data", {})
        .get("placeList", {})
        .get("businesses", {})
    )
    total = int(businesses.get("total") or 0)
    items = businesses.get("items") or []

    rows = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        place = normalize_place_item(item)
        if not place["name"] or place["name"] in seen:
            continue
        seen.add(place["name"])
        rows.append(place)
    return rows, total


def fetch_all_places(keyword: str, count: int = 100, *,
                     stop_flag=lambda: False,
                     emit_log=lambda _m: None,
                     sleep_range: tuple[float, float] = (1.0, 2.0)) -> list[dict]:
    """키워드로 count개까지 플레이스 수집.

    1페이지: m.search.naver.com HTML 파싱
    2페이지~: 동일 모바일 백엔드 GraphQL (start/display)
    """
    results = []
    seen = set()
    total = 0

    html_rows, total = fetch_places_html(keyword)
    for row in html_rows:
        if stop_flag():
            break
        name = row["name"]
        if name in seen:
            continue
        seen.add(name)
        results.append(row)
        if len(results) >= count:
            return results[:count]

    start = len(html_rows) + 1
    if start <= 1:
        start = 6 if html_rows else 1

    while len(results) < count:
        if stop_flag():
            break

        need = count - len(results)
        display = min(PAGE_SIZE, max(need, 5))
        rows, page_total = fetch_places_graphql(keyword, start=start, display=display)
        if page_total:
            total = page_total

        if not rows:
            break

        added = 0
        for row in rows:
            name = row["name"]
            if name in seen:
                continue
            seen.add(name)
            results.append(row)
            added += 1
            if len(results) >= count:
                break

        if added == 0:
            break

        start += display
        if total and start > total + 1:
            break

        delay = random.uniform(*sleep_range)
        end = time.time() + delay
        while time.time() < end:
            if stop_flag():
                break
            time.sleep(min(0.2, end - time.time()))

    return results[:count]


PLACE_DETAIL_URL = "https://m.place.naver.com/place/{pid}/home"


def fetch_nearby_station(place_id: str, timeout: int = 15) -> dict:
    """업체 상세 페이지에서 가장 가까운 지하철역 정보 추출.

    네이버가 계산해 둔 값(역명/출구/도보거리/도보시간)을 그대로 가져온다.
    실패/역없음 시 빈 dict.

    주의: 상세는 요청당 무거워 대량 연타 시 429 차단됨 → 호출부에서 딜레이 필수.
    """
    pid = (place_id or "").strip()
    if not pid:
        return {}
    try:
        resp = requests.get(
            PLACE_DETAIL_URL.format(pid=pid),
            headers=build_mobile_headers(),
            timeout=timeout,
        )
        resp.encoding = "utf-8"  # 상세는 charset 미선언 → UTF-8 강제 (한글 깨짐 방지)
        if resp.status_code != 200 or len(resp.text) < 5000:
            return {}
        if _is_blocked_html(resp.text):
            return {}
        state = extract_apollo_state(resp.text)
    except requests.RequestException:
        return {}

    for obj in state.values():
        if not isinstance(obj, dict) or obj.get("__typename") != "SubwayStationInfo":
            continue
        name = (obj.get("displayName") or obj.get("name") or "").strip()
        if name and not name.endswith("역"):
            name += "역"
        exit_no = str(obj.get("nearestExit") or "").strip()
        dist = obj.get("walkingDistance")
        walk = obj.get("walkTime")
        if not name:
            return {}
        # "역삼역 3번 출구 28m" 형태 텍스트
        text = name
        if exit_no:
            text += f" {exit_no}번 출구"
        if dist:
            text += f" {dist}m"
        return {
            "station": name,
            "exit": exit_no,
            "distance_m": dist,
            "walk_min": walk,
            "text": text,
        }
    return {}


# ── 근처 역 (이름추출 + 좌표 최단거리 하이브리드, 요청 0) ─────────────
import math
import os

_STATION_COORDS = None       # {역명: [lng, lat]}
_STATION_NAMES_BY_LEN = None  # 역명(긴 것 우선) 리스트 — 이름매칭용


def _load_station_coords() -> dict:
    global _STATION_COORDS, _STATION_NAMES_BY_LEN
    if _STATION_COORDS is None:
        path = os.path.join(os.path.dirname(__file__), "station_coords.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _STATION_COORDS = json.load(f)
        except Exception:
            _STATION_COORDS = {}
        # 이름매칭은 긴 역명부터(예: '압구정로데오역'이 '압구정역'보다 우선)
        _STATION_NAMES_BY_LEN = sorted(_STATION_COORDS.keys(), key=len, reverse=True)
    return _STATION_COORDS


def _haversine_m(lng1, lat1, lng2, lat2) -> float:
    """두 좌표 간 거리(m)."""
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


_NAME_STATION_RE = re.compile(r"([가-힣A-Za-z0-9]{2,12}역)")
_STATION_STOPWORDS = {"지하철역", "전철역", "기차역", "고속버스역", "시외버스역"}


def _station_from_name(biz_name: str) -> str:
    """업체명에서 '○○역' 토큰을 정규식으로 추출 (고정 목록 불필요).

    '스포애니 노원역점' → '노원역'. 목록에 없는 역도 잡힘.
    여러 개면 가장 긴(구체적인) 것 채택.
    """
    if not biz_name:
        return ""
    cands = [m for m in _NAME_STATION_RE.findall(biz_name) if m not in _STATION_STOPWORDS]
    if not cands:
        return ""
    return max(cands, key=len)


def nearest_station_by_coord(x, y):
    """업체 좌표(x=경도, y=위도)에서 가장 가까운 역과 거리(m) 반환."""
    coords = _load_station_coords()
    try:
        lng, lat = float(x), float(y)
    except (TypeError, ValueError):
        return "", None
    best, best_d = "", None
    for st, (slng, slat) in coords.items():
        d = _haversine_m(lng, lat, slng, slat)
        if best_d is None or d < best_d:
            best, best_d = st, d
    return best, (round(best_d) if best_d is not None else None)


def resolve_nearby_station(biz_name: str, x=None, y=None, max_m: int = 2000) -> dict:
    """근처 역 하이브리드 결정 (요청 0, 즉시).

    1) 업체명에 역명이 있으면 그 역 — 단 좌표상 max_m 이내일 때만 인정(오탐 방지)
    2) 아니면 좌표 최단역 (max_m 이내)
    거리 정보 없거나 max_m 초과면 빈 dict.
    """
    coords = _load_station_coords()
    coord_st, coord_d = nearest_station_by_coord(x, y)

    # 1) 이름 기반 후보
    name_st = _station_from_name(biz_name)
    if name_st:
        d = None
        if name_st in coords and x and y:
            try:
                slng, slat = coords[name_st]
                d = round(_haversine_m(float(x), float(y), slng, slat))
            except (TypeError, ValueError):
                d = None
        # 이름 후보가 좌표상으로도 타당(또는 좌표없음)하면 채택
        if d is None or d <= max_m:
            return {"station": name_st, "distance_m": d, "source": "name"}

    # 2) 좌표 최단역
    if coord_st and (coord_d is None or coord_d <= max_m):
        return {"station": coord_st, "distance_m": coord_d, "source": "coord"}

    return {}


def search_url(keyword: str) -> str:
    """디버그/로그용 검색 URL."""
    return f"{SEARCH_URL}?query={quote(keyword)}"


if __name__ == "__main__":
    import sys

    kw = sys.argv[1] if len(sys.argv) > 1 else "강남구 변호사"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    items = fetch_all_places(kw, count=limit)
    print(f"\n[{kw}] {len(items)}개\n" + "=" * 50)
    for i, p in enumerate(items, 1):
        print(
            f"[{i}] {p['name']}\n"
            f"    지번: {p['jibun_address']}\n"
            f"    시/구/동: {p['시']} / {p['구']} / {p['동']}\n"
            f"    카테고리: {p['category']}"
        )
