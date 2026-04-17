# -*- coding: utf-8 -*-
"""AI 기반 블로그 글 생성 모듈 — 프롬프트 시스템 연동"""
import re
import openai
from prompts import get_prompt_for_keyword


def generate_with_gpt(api_key: str, place: dict, keyword: str) -> dict:
    """GPT로 블로그 글 생성"""
    client = openai.OpenAI(api_key=api_key)
    prompt_data = get_prompt_for_keyword(keyword)
    prompt = _fill_prompt(prompt_data.get("blog", ""), place, keyword)

    # 디버그: 실제 전송 프롬프트 파일에 기록
    try:
        import os as _os
        dbg = _os.path.join(_os.path.dirname(__file__), "last_prompt.txt")
        with open(dbg, "w", encoding="utf-8") as _f:
            _f.write(f"KEYWORD: {keyword}\nPLACE: {place.get('name','')}\n\n--- PROMPT ---\n{prompt}\n")
    except Exception:
        pass

    if not prompt or len(prompt.strip()) < 50:
        raise ValueError(f"프롬프트가 너무 짧음 ({len(prompt or '')}자) - 생성 중단")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=4000,
    )

    raw_text = response.choices[0].message.content
    # 디버그: 응답도 저장
    try:
        dbg2 = _os.path.join(_os.path.dirname(__file__), "last_response.txt")
        with open(dbg2, "w", encoding="utf-8") as _f:
            _f.write(raw_text or "")
    except Exception:
        pass
    title_suffix = _generate_title(client, keyword, place, prompt_data, provider="gpt")
    title = _build_full_title(place, keyword, title_suffix)
    return parse_blog_content(raw_text, title)


def _gemini_request(client, prompt, retries=3):
    """Gemini API 요청 + 429 자동 재시도"""
    import time as _time
    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return resp
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                _time.sleep(5)
                continue
            raise


def generate_with_gemini(api_key: str, place: dict, keyword: str) -> dict:
    """Gemini로 블로그 글 생성"""
    import time as _time
    from google import genai

    client = genai.Client(api_key=api_key)

    prompt_data = get_prompt_for_keyword(keyword)
    prompt = _fill_prompt(prompt_data.get("blog", ""), place, keyword)

    response = _gemini_request(client, prompt)
    raw_text = response.text

    # 분당 제한 방지
    _time.sleep(4)

    # 제목 생성
    title_prompt = _fill_prompt(prompt_data.get("title", ""), place, keyword)
    if title_prompt:
        title_resp = _gemini_request(client, title_prompt)
        titles = [l.strip().lstrip("0123456789.-) ") for l in title_resp.text.strip().split("\n") if l.strip()]
        title = _pick_clean_title(titles, place, keyword)
    else:
        title = ""

    full_title = _build_full_title(place, keyword, title)
    return parse_blog_content(raw_text, full_title)


def _extract_biz_type(place: dict, keyword: str) -> str:
    biz_type = place.get("category", "")
    if not biz_type:
        parts = keyword.strip().split()
        biz_type = parts[-1] if parts else keyword
    import re as _re
    m = _re.search(r"(헬스장|요양원|요양센터|요양병원|미용실|카페|음식점|학원|치과|병원|약국|피트니스|요양|네일|빵집|베이커리|[가-힣]{2,3}점)$", biz_type)
    if m:
        biz_type = m.group(1)
    return biz_type


def _title_blacklist(place: dict, keyword: str) -> list:
    """마무리 문구에 들어가면 안 되는 단어들 — 지역/업종/업체명 변형 포함"""
    import re as _re
    biz = _extract_biz_type(place, keyword)
    dong = place.get("dong", "")
    addr = (place.get("address","") or "") + " " + (place.get("jibun_address","") or "")
    gu_match = _re.search(r"([가-힣]+구)", addr)
    gu = gu_match.group(1) if gu_match else ""
    name = place.get("name", "")
    station = place.get("nearby_station", "")
    items = set()
    for v in [biz, dong, gu, name, station, keyword]:
        if v:
            items.add(v.strip())
    # 키워드 분해 (예: "강서구헬스장" → ["강서구", "헬스장"])
    if keyword:
        for tok in keyword.split():
            items.add(tok)
    # 업종 변형 (요양원/요양센터/요양 등 부분 문자열도 차단)
    if biz:
        if "요양" in biz:
            items.update(["요양", "요양원", "요양센터", "요양병원"])
        if "헬스" in biz or biz == "피트니스":
            items.update(["헬스", "헬스장", "피트니스", "gym"])
    return [x for x in items if x and len(x) >= 2]


def _is_suffix_clean(suffix: str, blacklist: list) -> bool:
    if not suffix:
        return False
    for w in blacklist:
        if w in suffix:
            return False
    return True


def _clean_suffix(suffix: str, blacklist: list) -> str:
    """마무리 문구에서 블랙리스트 단어 제거"""
    import re as _re
    clean = suffix
    # 긴 토큰부터 제거 (부분 매칭 회피)
    for token in sorted(blacklist, key=len, reverse=True):
        if token and token in clean:
            clean = clean.replace(token, "")
    clean = _re.sub(r"\s{2,}", " ", clean).strip(" ,~-·.")
    return clean


def _get_title_prefix_type(biz_type: str) -> str:
    """업종별 제목 키워드 형식 — prompts.json의 title_prefix 설정 읽기 (dong/station/gu)"""
    try:
        import json as _json
        import os as _os
        pp = _os.path.join(_os.path.dirname(__file__), "prompts.json")
        with open(pp, "r", encoding="utf-8") as f:
            prompts = _json.load(f)
        entry = prompts.get(biz_type, {}) or {}
        return (entry.get("title_prefix") or "dong").strip().lower()
    except Exception:
        return "dong"


def _build_full_title(place: dict, keyword: str, suffix: str) -> str:
    """제목 조합: [지역+업종] [업체명] [마무리 문구] — 업종별 prefix 형식 적용"""
    import re as _re
    biz_type = _extract_biz_type(place, keyword)
    dong = place.get("dong", "")
    name = place.get("name", "")
    station = (place.get("nearby_station") or "").replace("역", "").strip()
    addr = (place.get("address", "") or "") + " " + (place.get("jibun_address", "") or "")
    gu_match = _re.search(r"([가-힣]+구)", addr)
    gu = gu_match.group(1) if gu_match else ""

    ptype = _get_title_prefix_type(biz_type)
    if ptype == "station" and station:
        prefix = f"{station}역{biz_type}"
    elif ptype == "gu" and gu:
        prefix = f"{gu}{biz_type}"
    else:
        prefix = f"{dong}{biz_type}" if dong else biz_type

    if suffix:
        blacklist = _title_blacklist(place, keyword)
        clean = _clean_suffix(suffix, blacklist)
        if clean and len(clean) >= 3:
            return f"{prefix} {name} {clean}"

    return f"{prefix} {name} 방문 후기"


def _fill_prompt(template: str, place: dict, keyword: str) -> str:
    """프롬프트 템플릿에 변수 채우기"""
    if not template:
        return ""

    parts = keyword.strip().split()
    biz_type = parts[-1] if parts else keyword

    addr = place.get("address", "")
    jibun = place.get("jibun_address", "")
    if jibun:
        full_addr = f"{addr} {jibun}" if addr else jibun
    else:
        full_addr = addr

    # 검색 키워드의 지역명을 실제 주소의 구로 교체 (검색 = 은평구, 실제 = 강서구인 경우)
    import re as _re
    actual_gu_match = _re.search(r"([가-힣]+구)", full_addr or "")
    effective_keyword = keyword
    if actual_gu_match and keyword:
        actual_gu = actual_gu_match.group(1)
        keyword_gus = _re.findall(r"([가-힣]+구)", keyword)
        for kg in keyword_gus:
            if kg != actual_gu:
                effective_keyword = effective_keyword.replace(kg, actual_gu)

    replacements = {
        "{업체명}": place.get("name", ""),
        "{주소}": full_addr,
        "{근처역}": place.get("nearby_station", ""),
        "{카테고리}": place.get("category", ""),
        "{앞키워드}": place.get("front_keywords", ""),
        "{태그}": place.get("tags", ""),
        "{업종}": biz_type,
        "{키워드}": effective_keyword,
        "{근처역/교통}": place.get("nearby_station", ""),
        "{기타 설명}": place.get("category", ""),
    }

    result = template
    for key, val in replacements.items():
        result = result.replace(key, val)
    return result


def _pick_clean_title(candidates: list, place: dict, keyword: str) -> str:
    """10개 후보 중 블랙리스트 단어가 없는 첫 번째 후보 선택. 없으면 가장 덜 오염된 것을 정제."""
    blacklist = _title_blacklist(place, keyword)
    # 1) 블랙리스트 단어가 하나도 없는 깨끗한 후보
    for c in candidates:
        if _is_suffix_clean(c, blacklist) and 3 <= len(c) <= 30:
            return c
    # 2) 정제해서 최소 3자 이상 남는 첫 후보
    for c in candidates:
        cleaned = _clean_suffix(c, blacklist)
        if cleaned and len(cleaned) >= 3:
            return cleaned
    return candidates[0] if candidates else ""


def _generate_title(client, keyword, place, prompt_data, provider="gpt"):
    """GPT로 제목 마무리 문구 생성 — 10개 받아서 블랙리스트 필터로 최적 선택"""
    title_prompt = _fill_prompt(prompt_data.get("title", ""), place, keyword)
    if not title_prompt:
        return ""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": title_prompt}],
            temperature=0.9,
            max_tokens=500,
        )
        titles = [l.strip().lstrip("0123456789.-) ") for l in response.choices[0].message.content.strip().split("\n") if l.strip()]
        return _pick_clean_title(titles, place, keyword)
    except Exception:
        return ""


def parse_blog_content(raw_text: str, title: str = "") -> dict:
    """생성된 텍스트를 구조화"""
    if not title:
        title_match = re.search(r"\[제목\]\s*(.+?)(?:\n|$)", raw_text)
        title = title_match.group(1).strip() if title_match else "제목 없음"

    # 제목에서 특수문자 제거 (짝대기, 콜론 등)
    title = title.replace(" - ", " ").replace("-", " ").replace(":", " ").replace("|", " ").strip()

    tag_match = re.search(r"\[태그\]\s*(.+?)(?:\n|$)", raw_text)
    tags = []
    if tag_match:
        tag_text = tag_match.group(1).strip()
        tags = [t.strip().lstrip("#") for t in re.split(r"[,\s#]+", tag_text) if t.strip()]

    # 태그가 비어있으면 본문에서 #태그 패턴 추출
    if not tags:
        hash_tags = re.findall(r"#(\S+)", raw_text)
        if hash_tags:
            tags = [t.strip() for t in hash_tags]

    image_count = raw_text.count("[이미지]")

    body = raw_text
    body = re.sub(r"\[제목\]\s*.+?\n?", "", body)
    body = re.sub(r"\[태그\]\s*.+?\n?", "", body)

    return {
        "title": title,
        "body": body.strip(),
        "tags": tags,
        "image_count": max(image_count, 3),
        "raw": raw_text,
    }


def generate_content(provider: str, api_key: str, place: dict, keyword: str) -> dict:
    """통합 생성 함수"""
    if provider == "GPT":
        result = generate_with_gpt(api_key, place, keyword)
    elif provider == "Gemini":
        result = generate_with_gemini(api_key, place, keyword)
    else:
        raise ValueError(f"지원하지 않는 AI 제공자: {provider}")

    # 태그가 비어있으면 place 데이터에서 자동 생성 (지역+업종 조합만 사용, 동/역 단독 제외)
    if not result.get("tags"):
        biz_type = place.get("category", "") or place.get("biz_type", "")
        auto_tags = []
        for field in ["tags", "pixabay_keywords"]:
            val = place.get(field, "")
            if val:
                auto_tags.extend([t.strip() for t in val.split(",") if t.strip()])
        # 업종명이 포함된 조합 태그만 유지 (동/역 단독 제외)
        filtered = [t for t in auto_tags if not biz_type or biz_type in t]
        if not filtered:
            filtered = auto_tags
        # 중복 제거
        seen = []
        for t in filtered:
            if t not in seen:
                seen.append(t)
        result["tags"] = seen[:10]

    return result
