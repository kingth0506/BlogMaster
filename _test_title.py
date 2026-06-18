# -*- coding: utf-8 -*-
"""제목 생성 테스트 — 업종별로 5개 케이스 확인"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from config import load_config, get_active_account
from content_generator import _generate_title, _build_full_title
from prompts import get_prompt_for_keyword
import openai

cfg = load_config()
api_key = (cfg.get("ai_api_key") or "").strip()
if not api_key:
    print("API 키 없음")
    sys.exit(1)

client = openai.OpenAI(api_key=api_key)

TESTS = [
    # (keyword, place)
    ("강동구 변호사",  {"name": "법무법인 하나로", "address": "서울 강동구 천호대로 1234", "dong": "천호동", "category": "변호사", "nearby_station": "천호역", "front_keywords": "", "tags": ""}),
    ("역삼동 헬스장",  {"name": "휘트니스엠 선릉점", "address": "서울 강남구 역삼동 123", "dong": "역삼동", "category": "헬스장", "nearby_station": "선릉역", "front_keywords": "", "tags": ""}),
    ("은평구 요양원",  {"name": "행복한요양원", "address": "서울 은평구 응암동 456", "dong": "응암동", "category": "요양원", "nearby_station": "응암역", "front_keywords": "", "tags": ""}),
    ("마포구 네일샵",  {"name": "핑크네일", "address": "서울 마포구 합정동 789", "dong": "합정동", "category": "네일샵", "nearby_station": "합정역", "front_keywords": "", "tags": ""}),
    ("서초구 세무사",  {"name": "서초세무법인", "address": "서울 서초구 서초동 101", "dong": "서초동", "category": "세무사", "nearby_station": "교대역", "front_keywords": "", "tags": ""}),
]

for keyword, place in TESTS:
    prompt_data = get_prompt_for_keyword(keyword)
    suffix = _generate_title(client, keyword, place, prompt_data, provider="gpt")
    full = _build_full_title(place, keyword, suffix)
    print(f"[{keyword}]")
    print(f"  suffix: {suffix}")
    print(f"  full  : {full}")
    print()
