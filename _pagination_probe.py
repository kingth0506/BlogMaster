# -*- coding: utf-8 -*-
"""[QA] GraphQL 페이지네이션을 직접 돌려 '네이버 total vs 실제 수집'을 검증.

목적: '강남구 헬스장'이 끝(마지막 항목)까지 수집되는지 증명.
- GraphQL이 보고하는 total을 찍고
- 페이지별 실제 반환 개수 / 중복 제외 누적을 찍고
- 어떤 사유로 종료했는지(빈응답 / total도달 / 중복) 출력
"""
import sys, io, time, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from naver_crawler import fetch_places_html, fetch_places_graphql, PAGE_SIZE

KEYWORD = sys.argv[1] if len(sys.argv) > 1 else "강남구 헬스장"

print(f"=== '{KEYWORD}' GraphQL 페이지네이션 프로브 ===\n")

# 1페이지 HTML
html_rows, html_total = fetch_places_html(KEYWORD)
print(f"[HTML] {len(html_rows)}개, total={html_total}")

seen = set(r["name"] for r in html_rows)
collected = len(html_rows)
start = len(html_rows) + 1
if start <= 1:
    start = 6 if html_rows else 1

gql_total = 0
page = 0
reason = "?"
while True:
    page += 1
    rows, page_total = fetch_places_graphql(KEYWORD, start=start, display=PAGE_SIZE)
    if page_total:
        gql_total = page_total
    if not rows:
        reason = f"빈 응답 (start={start}) → 더 이상 결과 없음 = 진짜 끝"
        break
    new = [r for r in rows if r["name"] not in seen]
    for r in new:
        seen.add(r["name"])
    collected += len(new)
    print(f"[GQL p{page}] start={start} 반환={len(rows)} 신규={len(new)} 누적={collected} total={gql_total}")
    if len(new) == 0:
        reason = f"중복만 반환 (start={start}) → 페이지네이션 한계 또는 끝"
        break
    start += PAGE_SIZE
    if gql_total and start > gql_total + 1:
        reason = f"start({start}) > total({gql_total}) → total 도달 = 끝"
        break
    if page > 60:
        reason = "안전장치(60페이지) 도달"
        break
    time.sleep(random.uniform(0.5, 1.0))

print(f"\n=== 결과 ===")
print(f"네이버 GraphQL total : {gql_total}")
print(f"실제 수집(중복제외)  : {collected}")
print(f"종료 사유            : {reason}")
print("\n=== 판정 ===")
if gql_total and collected >= gql_total - 2:
    print(f"✅ 통과: total({gql_total}) ≈ 수집({collected}) — 강남구 헬스장 전부 수집됨")
elif gql_total and collected < gql_total - 2:
    print(f"❌ 실패: total({gql_total})인데 {collected}개만 수집 — 끝까지 못 감 ({gql_total - collected}개 누락)")
else:
    print(f"⚠️ total 미확보({gql_total}) — '빈 응답으로 종료'면 사실상 끝 도달이나, total 없어 100% 단정 불가")
