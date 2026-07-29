# -*- coding: utf-8 -*-
import requests, re, json
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
H = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8", "Accept-Language": "ko-KR,ko;q=0.9", "Referer": "https://m.search.naver.com/"}
kw = "강남구 헬스장"

# 후보 1: m.place.naver.com/place/list (모바일 플레이스 리스트)
for url in [
    "https://m.place.naver.com/place/list",
    "https://m.search.naver.com/search.naver",
]:
    params = {"query": kw} if "search" in url else {"query": kw, "type": "place"}
    try:
        r = requests.get(url, params=params, headers=H, timeout=10, allow_redirects=True)
        print(f"=== {url} -> {r.status_code} len={len(r.text)} final={r.url[:80]}")
        # 플레이스 개수 흔적
        print("   PlaceListBusinessesItem count:", r.text.count("PlaceListBusinessesItem"))
        print("   totalCount 흔적:", re.findall(r'"total[A-Za-z]*"\s*:\s*\d+', r.text)[:5])
    except Exception as e:
        print(f"=== {url} ERR {e}")

# 후보 2: GraphQL API (POST) — 페이지네이션 가능 소스
gql_url = "https://pcmap-api.place.naver.com/graphql"
gh = dict(H)
gh["Content-Type"] = "application/json"
gh["Referer"] = "https://pcmap.place.naver.com/"
try:
    r = requests.get(gql_url, headers=gh, timeout=10)
    print(f"=== GraphQL GET -> {r.status_code} len={len(r.text)} head={r.text[:120]}")
except Exception as e:
    print("=== GraphQL ERR", e)
