# -*- coding: utf-8 -*-
"""4번 — 키워드별 제목 매칭 테스트.
업종별로 GPT 호출 → 마무리 문구가 해당 업종 답게 나오는지 + 다른 업종 단어 안 섞이는지 검증.
"""
import sys, os, io, json, re, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from content_generator import _build_full_title, _generate_title, _strip_markdown
from prompts import get_prompt_for_keyword
import openai

# GPT 키 로드
cfg = json.load(open('config.json', 'r', encoding='utf-8'))
api_keys = cfg.get('api_keys_by_user', {})
gpt_key = None
for u in ['admin', 'admin0904', 'kidth1']:
    keys = api_keys.get(u, {}).get('gpt_key_list')
    if keys:
        gpt_key = next((k for k in keys if k), None) if isinstance(keys, list) else keys
        if gpt_key:
            break
if not gpt_key:
    print("GPT 키 없음")
    sys.exit(1)

client = openai.OpenAI(api_key=gpt_key)

# 테스트 케이스: 업종별 + 다른 업종 키워드가 섞였을 때 안 섞이는지 검증
tests = [
    # (keyword, place, 검증할 금기 키워드들 - 다른 업종)
    ("강남구 변호사", {"name": "법무법인 하나로", "category": "법률사무소",
                "address": "서울 강남구 언주로 711", "jibun_address": "서울 강남구 논현동",
                "nearby_station": "학동역"},
     ["네일", "헬스", "운동", "요양", "세무", "리프팅", "마사지"]),

    ("역삼동 헬스장", {"name": "휘트니스엠 선릉점", "category": "헬스장",
                "address": "서울 강남구 역삼로 100", "jibun_address": "서울 강남구 역삼동",
                "nearby_station": "선릉역"},
     ["변호사", "법률", "요양", "세무", "네일"]),

    ("은평구 요양원", {"name": "행복한요양원", "category": "요양원",
                "address": "서울 은평구 응암로 50", "jibun_address": "서울 은평구 응암동",
                "nearby_station": "응암역"},
     ["변호사", "헬스", "운동", "네일", "법률", "세무"]),

    ("마포구 네일아트", {"name": "핑크네일", "category": "네일샵",
                  "address": "서울 마포구 합정로 12", "jibun_address": "서울 마포구 합정동",
                  "nearby_station": "합정역"},
     ["변호사", "법률", "요양", "헬스", "세무"]),

    ("서초구 세무사", {"name": "서초세무법인", "category": "세무사",
                "address": "서울 서초구 서초대로 100", "jibun_address": "서울 서초구 서초동",
                "nearby_station": "교대역"},
     ["변호사", "법률(전문가는 제외)", "요양", "네일", "헬스"]),

    # === prompts.json에 없는 업종 — '기본' 프롬프트로 폴백 ===
    ("강남구 법무사", {"name": "스마트법무사", "category": "법무사",
                "address": "서울 강남구 테헤란로 200", "jibun_address": "서울 강남구 역삼동",
                "nearby_station": "역삼역"},
     ["네일", "헬스", "운동", "요양", "마사지"]),

    ("관악구 고시원", {"name": "신림고시원", "category": "고시원",
                "address": "서울 관악구 관악로 50", "jibun_address": "서울 관악구 신림동",
                "nearby_station": "신림역"},
     ["변호사", "법률", "헬스", "운동", "요양", "네일", "세무"]),

    ("동대문구 원룸텔", {"name": "회기원룸텔", "category": "원룸텔",
                "address": "서울 동대문구 회기로 30", "jibun_address": "서울 동대문구 회기동",
                "nearby_station": "회기역"},
     ["변호사", "법률", "헬스", "운동", "요양", "네일", "세무"]),
]

def _check_contamination(text, banned):
    """제목에 금기 키워드가 섞였는지"""
    found = []
    for ban in banned:
        # 괄호 주석 무시
        ban_word = ban.split("(")[0].strip()
        if ban_word and ban_word in text:
            found.append(ban_word)
    return found

print(f"=== 키워드별 제목 매칭 테스트 — {len(tests)}건 ===\n")
ok = 0
for i, (kw, place, banned) in enumerate(tests, 1):
    print(f"[{i}] keyword={kw!r}")
    print(f"    place: {place['name']} / category: {place['category']}")
    try:
        # 프롬프트 매칭 확인
        prompt_data = get_prompt_for_keyword(kw)
        title_prompt_preview = (prompt_data.get("title") or "")[:50].replace("\n", " ")
        print(f"    매칭 프롬프트(title): {title_prompt_preview!r}...")

        # 실제 제목 생성
        suffix = _generate_title(client, kw, place, prompt_data, provider="gpt")
        title = _build_full_title(place, kw, suffix)
        print(f"    생성된 제목: {title}")
        print(f"    suffix: {suffix!r}")

        # 검증: 다른 업종 단어 섞였는지
        contaminated = _check_contamination(title, banned)
        if contaminated:
            print(f"    ❌ 다른 업종 단어 섞임: {contaminated}")
        else:
            print(f"    ✅ 다른 업종 단어 없음")
            ok += 1
    except Exception as e:
        print(f"    ERR: {e}")
    print()
    time.sleep(0.5)

print("=" * 50)
print(f"통과: {ok}/{len(tests)}")
