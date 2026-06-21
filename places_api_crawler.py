# -*- coding: utf-8 -*-
"""네이버 지도 내부 검색 API 크롤러 (requests 전용 — Selenium 미사용)

상호명 + 지번 주소를 초고속 수집해 시/구/동으로 정제.
애드포스트 수익형 블로그 자동 포스팅 베이스 데이터용.
"""
import time
import random
import requests


# 네이버 방화벽 차단 회피용 UA 풀
_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
]

_SEARCH_URL = "https://map.naver.com/p/api/search/all/searchMore"


def _build_headers() -> dict:
    """User-Agent + Referer 포함 헤더 (차단 회피 필수)."""
    return {
        "User-Agent": random.choice(_UA_POOL),
        "Referer": "https://map.naver.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }


def _parse_jibun(address: str) -> dict:
    """지번 주소를 공백으로 쪼개 시/구/동 추출.

    예: "서울특별시 강남구 역삼동 123-4"
        -> {"시": "서울특별시", "구": "강남구", "동": "역삼동"}
    토큰 수가 부족하면 빈 문자열로 채움."""
    parts = (address or "").split()
    si = parts[0] if len(parts) >= 1 else ""
    gu = parts[1] if len(parts) >= 2 else ""
    dong = parts[2] if len(parts) >= 3 else ""
    return {"시": si, "구": gu, "동": dong}


def fetch_places(keyword: str, page: int = 1, display_count: int = 20,
                 timeout: int = 10) -> list[dict]:
    """네이버 지도 내부 API에서 한 페이지(기본 20개)를 수집.

    Args:
        keyword: 검색어 (예: "강남구 헬스장")
        page: 페이지 번호 (1-based)
        display_count: 페이지당 개수 (기본 20)
        timeout: 요청 타임아웃(초)

    Returns:
        [{"상호명", "주소", "시", "구", "동"}, ...] — 실패 시 빈 리스트
    """
    params = {
        "query": keyword,
        "page": page,
        "displayCount": display_count,
        "type": "all",
    }
    try:
        resp = requests.get(_SEARCH_URL, params=params,
                            headers=_build_headers(), timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"[요청실패] {keyword} p{page}: {e}", flush=True)
        return []

    # result -> place -> list 구조 파싱
    try:
        place_list = data["result"]["place"]["list"]
    except (KeyError, TypeError):
        return []

    rows = []
    for item in place_list:
        name = (item.get("name") or "").strip()
        address = (item.get("address") or "").strip()
        if not name:
            continue
        parsed = _parse_jibun(address)
        rows.append({
            "상호명": name,
            "주소": address,
            "시": parsed["시"],
            "구": parsed["구"],
            "동": parsed["동"],
        })
    return rows


def crawl(keyword: str, max_pages: int = 5, display_count: int = 20) -> list[dict]:
    """여러 페이지를 순회 수집. 요청당 1~2초 랜덤 딜레이로 IP 차단 예방.

    Args:
        keyword: 검색어
        max_pages: 최대 페이지 수
        display_count: 페이지당 개수

    Returns:
        전체 결과 리스트 (상호명 기준 중복 제거)
    """
    all_rows = []
    seen = set()
    for page in range(1, max_pages + 1):
        rows = fetch_places(keyword, page=page, display_count=display_count)
        if not rows:
            # 빈 페이지면 더 이상 결과 없음 → 종료
            break
        new_count = 0
        for r in rows:
            if r["상호명"] in seen:
                continue
            seen.add(r["상호명"])
            all_rows.append(r)
            new_count += 1
        print(f"[수집] {keyword} p{page}: +{new_count}개 (누적 {len(all_rows)})", flush=True)
        if new_count == 0:
            break
        # 요청당 1~2초 랜덤 딜레이
        time.sleep(random.uniform(1.0, 2.0))
    return all_rows


if __name__ == "__main__":
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else "강남구 헬스장"
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    results = crawl(kw, max_pages=pages)
    print(f"\n총 {len(results)}개 수집\n" + "=" * 40)
    for r in results:
        print(f"{r['상호명']:<24} | {r['시']} {r['구']} {r['동']}")
