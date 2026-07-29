# -*- coding: utf-8 -*-
"""[QA] 마지막 항목까지 크롤링되는지 검증하는 테스트.

count를 크게 줘서, 페이지네이션이 끝까지 돌아 결과가 소진될 때까지
(= 마지막 item 도달) 수집되는지 확인한다.
- 합격 조건: 목표(count) 미달이지만 '결과 소진'으로 자연 종료해야 함.
  (즉 더 가져올 게 없어서 멈춰야지, count에 막혀 멈추면 끝 도달 여부 모름)
- total(네이버가 보고한 전체 개수)과 수집 개수를 비교 출력.
"""
import sys
import io

# 콘솔 한글 깨짐 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from naver_crawler import fetch_all_places, fetch_places_html, fetch_places_graphql

KEYWORD = sys.argv[1] if len(sys.argv) > 1 else "강남구 헬스장"
TARGET = int(sys.argv[2]) if len(sys.argv) > 2 else 300

print(f"=== '{KEYWORD}' 마지막 항목까지 수집 테스트 (목표 {TARGET}개) ===\n")

# 1) 네이버가 보고하는 전체 개수 확인
html_rows, total = fetch_places_html(KEYWORD)
print(f"[HTML 1페이지] {len(html_rows)}개 수집, 네이버 보고 total = {total}\n")

# 2) 페이지 진행 로그
logs = []
def emit(msg):
    logs.append(msg)
    print(f"  · {msg}")

print("[전체 페이지네이션 진행]")
items = fetch_all_places(KEYWORD, count=TARGET, emit_log=emit,
                         sleep_range=(0.6, 1.2))

print(f"\n=== 결과 ===")
print(f"수집 개수      : {len(items)}")
print(f"네이버 total   : {total}")
print(f"목표(count)    : {TARGET}")

# 마지막 항목 출력
if items:
    last = items[-1]
    print(f"\n[마지막 항목] {last['name']}")
    print(f"  지번: {last['jibun_address']}")
    print(f"  시/구/동: {last['시']} / {last['구']} / {last['동']}")

# 합격 판정
print("\n=== 판정 ===")
reached_count = len(items) >= TARGET
exhausted = len(items) < TARGET
if total and len(items) >= total - 2:  # total 근처까지 모았으면 끝 도달
    print(f"✅ 통과: 네이버 total({total}) 대비 {len(items)}개 수집 — 마지막 항목까지 도달")
elif exhausted and len(items) > len(html_rows):
    print(f"✅ 통과: 2페이지 이상 진행 후 결과 소진으로 자연 종료 — 마지막 항목까지 도달 (목표 {TARGET} 미달은 결과가 그만큼뿐이라는 뜻)")
elif reached_count:
    print(f"⚠️ 보류: 목표 {TARGET}개를 채워서 멈춤 — 더 있을 수 있으니 count를 더 키워 재확인 필요")
else:
    print(f"❌ 실패: 1페이지({len(html_rows)}개)에서 더 못 넘어감 — 페이지네이션(GraphQL) 점검 필요")
