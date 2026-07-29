# -*- coding: utf-8 -*-
"""[QA] 주소로 검증: '강남구 헬스장' 수집 결과가 진짜 강남구인지 주소로 확인.

검증 방법 = 주소.
- 수집된 업체의 '구'가 실제로 강남구인지
- 강남구가 아닌 게 섞였는지 (오염)
- 강남구 내 어느 동까지 커버됐는지
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from naver_crawler import fetch_all_places

KEYWORD = sys.argv[1] if len(sys.argv) > 1 else "강남구 헬스장"
TARGET = int(sys.argv[2]) if len(sys.argv) > 2 else 400
EXPECT_GU = sys.argv[3] if len(sys.argv) > 3 else "강남구"

items = fetch_all_places(KEYWORD, count=TARGET, sleep_range=(0.5, 1.0))

right, wrong = [], []
dong_count = {}
for it in items:
    gu = (it.get("구") or "").strip()
    dong = (it.get("동") or "").strip()
    if gu == EXPECT_GU:
        right.append(it)
        dong_count[dong] = dong_count.get(dong, 0) + 1
    else:
        wrong.append(it)

print(f"=== '{KEYWORD}' 주소 검증 ===")
print(f"총 수집        : {len(items)}")
print(f"✅ {EXPECT_GU} 맞음 : {len(right)}")
print(f"❌ {EXPECT_GU} 아님 : {len(wrong)}")

print(f"\n[{EXPECT_GU} 내 동별 분포] ({len(dong_count)}개 동)")
for d, c in sorted(dong_count.items(), key=lambda x: -x[1]):
    print(f"  {d or '(동없음)':<10} {c}개")

if wrong:
    print(f"\n[{EXPECT_GU} 아닌 오염 샘플 10개]")
    for it in wrong[:10]:
        print(f"  {it['name']:<22} → {it['시']} {it['구']} {it['동']}")

# 강남구 행정동 전체 (검증 기준)
GANGNAM_DONGS = ["역삼동","개포동","청담동","삼성동","대치동","신사동","논현동",
                 "압구정동","세곡동","자곡동","율현동","일원동","수서동","도곡동"]
covered = set(dong_count.keys())
missing = [d for d in GANGNAM_DONGS if d not in covered]
print(f"\n[강남구 행정동 커버리지] {len(GANGNAM_DONGS)}개 중 {len(GANGNAM_DONGS)-len(missing)}개 커버")
if missing:
    print(f"  미커버 동: {', '.join(missing)}")
