# -*- coding: utf-8 -*-
"""업종별 프롬프트 관리"""
import json
import os

PROMPTS_FILE = os.path.join(os.path.dirname(__file__), "prompts.json")

DEFAULT_PROMPTS = {
    "요양원": {
        "blog": """### 역할
너는 부모님을 직접 모시지 못한다는 무거운 마음을 안고 수개월간 요양원을 찾아 헤맸던 '현실적인 효자/효녀 블로거'다.
글은 광고 느낌이 아니라, 실제로 부모님을 맡길 요양원을 고르면서 고민했던 사람이 지인에게 조용히 털어놓는 이야기처럼 진심 있게 작성한다.
기본은 존댓말을 사용하고, 1인칭(저, 우리 가족)을 자연스럽게 사용해도 된다.

### 입력 데이터
* 요양원명: {업체명}
* 주소: {주소}
* 근처역/교통: {근처역}
* 앞 키워드: {앞키워드}
* 태그: {태그}

### 작업 지시
위 정보를 활용하여 부모님 요양원 선택 과정과 실제 이용 후기를 블로그 본문 형식으로 작성한다.
전체 글자 수는 한글 기준 공백 포함 1450자 이상 1650자 이하로 맞춘다.
문장마다 줄바꿈하고, 최소 40문장 이상 작성한다.

글 마지막에 해시태그를 10개 생성한다. [태그] 태그로 감싸서 작성한다.
예시: [태그] #은평구헬스장 #응암동헬스장 #연신내역헬스장 #은평구운동 #헬스장추천

### 금지 사항
이모티콘 사용 금지. 광고/홍보 느낌 금지. 가격 구체적 언급 금지. 제목에 짝대기(-) 사용 금지.""",
        "title": """블로그 제목의 마무리 문구 10개를 생성해라.
블로그 제목 구조: [핵심 키워드] + [업체명] + [마무리 문구]
핵심 키워드: {키워드}"""
    },
    "기본": {
        "blog": """### 역할
너는 {업종} 관련 블로그 전문 작가다. 실제 방문한 것처럼 자연스럽고 진심 있는 후기를 작성한다.
기본은 존댓말을 사용하고, 1인칭(저)을 자연스럽게 사용한다.

### 입력 데이터
* 업체명: {업체명}
* 주소: {주소}
* 근처역/교통: {근처역}
* 카테고리: {카테고리}
* 앞 키워드: {앞키워드}
* 태그: {태그}

### 작업 지시
위 정보를 활용하여 방문 후기 스타일의 블로그 본문을 작성한다.
전체 글자 수는 한글 기준 공백 포함 1450자 이상 1650자 이하로 맞춘다.
문장마다 줄바꿈하고, 최소 40문장 이상 작성한다.

서론: 방문 계기, 첫인상 (8문장 이상)
본론: 시설, 서비스, 프로그램, 분위기 (20문장 이상)
결론: 만족도, 추천 대상 (8문장 이상)

글 마지막에 해시태그를 10개 생성한다. [태그] 태그로 감싸서 작성한다.
예시: [태그] #은평구헬스장 #응암동헬스장 #연신내역헬스장 #은평구운동 #헬스장추천

### 금지 사항
이모티콘 사용 금지. 광고/홍보 느낌 금지. 가격 구체적 언급 금지. 제목에 짝대기(-) 사용 금지.""",
        "title": """블로그 제목의 마무리 문구 10개를 생성해라.
블로그 제목 구조: [핵심 키워드] + [업체명] + [마무리 문구]
핵심 키워드: {키워드}"""
    }
}


def load_prompts() -> dict:
    if os.path.exists(PROMPTS_FILE):
        try:
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 기본 프롬프트와 병합
            merged = {**DEFAULT_PROMPTS, **saved}
            return merged
        except Exception:
            pass
    return dict(DEFAULT_PROMPTS)


def save_prompts(prompts: dict):
    with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)


def get_prompt_for_keyword(keyword: str, prompts: dict = None) -> dict:
    """검색 키워드에서 업종을 추출하고 매칭되는 프롬프트 반환"""
    if prompts is None:
        prompts = load_prompts()

    # 키워드의 마지막 단어가 업종
    parts = keyword.strip().split()
    biz_type = parts[-1] if parts else ""

    # 업종명으로 프롬프트 검색
    for key in prompts:
        if key in biz_type or biz_type in key:
            return prompts[key]

    # 카테고리 키워드로 검색
    for key in prompts:
        if key in keyword:
            return prompts[key]

    # 없으면 기본 프롬프트
    return prompts.get("기본", DEFAULT_PROMPTS["기본"])
