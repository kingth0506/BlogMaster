# -*- coding: utf-8 -*-
"""AI 기반 블로그 글 생성 모듈 — 프롬프트 시스템 연동"""
import re
import openai
from prompts import get_prompt_for_keyword


def generate_with_gpt(api_key: str, place: dict, keyword: str) -> dict:
    """GPT로 블로그 글 생성"""
    client = openai.OpenAI(api_key=api_key)
    # 지역 확장 크롤링: 이 업체가 수집된 실제 검색 키워드(예: "강남구 파스타") 우선
    keyword = place.get("search_keyword") or keyword
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

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 블로그 글쓰기 전문가다. 주어진 지시사항에 따라 블로그 본문만 작성한다. 평가·칭찬·설명·인사 없이 오직 블로그 본문 텍스트만 출력한다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=4096,
        )
    except Exception as e:
        raise RuntimeError(f"GPT API 호출 실패: {e}") from e

    if not response.choices:
        raise RuntimeError("GPT 응답 없음 (choices 비어있음)")
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


def _gemini_request(client, prompt, retries=5):
    """Gemini API 요청 + 429/503 자동 재시도 + 폴백 모델.
    gemini-2.5-flash가 503이면 gemini-2.5-flash-lite로 폴백. 성공 응답에만 과금."""
    import time as _time
    models_chain = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    last_err = None
    for model in models_chain:
        for attempt in range(retries):
            try:
                return client.models.generate_content(model=model, contents=prompt)
            except Exception as e:
                last_err = e
                msg = str(e)
                transient = ("429" in msg) or ("503" in msg) or ("UNAVAILABLE" in msg)
                if transient and attempt < retries - 1:
                    _time.sleep(min(30, 3 * (2 ** attempt)))
                    continue
                # 503 계속 나면 다음 모델로 폴백
                if "503" in msg or "UNAVAILABLE" in msg:
                    break
                raise
    if last_err:
        raise last_err


def generate_with_gemini(api_key: str, place: dict, keyword: str) -> dict:
    """Gemini로 블로그 글 생성"""
    import time as _time
    from google import genai

    client = genai.Client(api_key=api_key)

    # 지역 확장 크롤링: 이 업체가 수집된 실제 검색 키워드 우선
    keyword = place.get("search_keyword") or keyword
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
    # 수집할 때 쓴 search_keyword 우선, 없으면 인자 keyword. 카테고리는 사용 안 함.
    src_kw = (place.get("search_keyword") or keyword or "").strip()
    parts = src_kw.split()
    biz_type = parts[-1] if parts else src_kw
    if not biz_type:
        biz_type = place.get("category", "") or ""
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
    station = (place.get("nearby_station", "") or "").replace("역", "").strip()
    items = set()
    for v in [biz, dong, gu, name, station, keyword]:
        if v:
            items.add(v.strip())
    # 키워드 분해 (예: "강서구헬스장" → ["강서구", "헬스장"])
    if keyword:
        for tok in keyword.split():
            items.add(tok)
        # 붙어있는 키워드에서 동/구/역 패턴 추출 (예: "역삼동헬스장" → "역삼동")
        for tok in keyword.split():
            for m in _re.findall(r"[가-힣]+동|[가-힣]+구|[가-힣]+역", tok):
                items.add(m)
    # 주소에서 동 추출 (dong 필드 없을 때 보완)
    if not dong:
        dong_m = _re.search(r"([가-힣]+동)", addr)
        if dong_m:
            items.add(dong_m.group(1))
    # 업종 변형 (요양원/요양센터/요양 등 부분 문자열도 차단)
    if biz:
        if "요양" in biz:
            items.update(["요양", "요양원", "요양센터", "요양병원"])
        if "헬스" in biz or biz == "피트니스":
            items.update(["헬스", "헬스장", "피트니스", "gym"])
        if "네일" in biz:
            items.update(["네일", "네일샵", "네일아트"])
    # 항상 차단할 문구 (가격 관련 단어 포함)
    _BLOCKED_PHRASES = [
        # 가격/홍보성 단어만 차단 — 후기/방문/내돈내산 류는 새 제목 룰에서 '허용'(권장)이라 제외
        "이용권", "가격", "요금", "만원", "천원", "원권", "월정액", "회원권", "할인", "쿠폰",
        "일일", "1일", "무료체험",
    ]
    items.update(_BLOCKED_PHRASES)
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
    """업종별 제목 키워드 형식 — prompts.json의 title_prefix 설정 읽기 (dong/station/gu).
    get_prompt_for_keyword와 동일한 fuzzy 매칭을 사용해 사용자 선택이 무시되지 않도록 함."""
    try:
        from prompts import load_prompts
        prompts = load_prompts()
    except Exception:
        return "dong"
    entry = prompts.get(biz_type)
    if not entry and biz_type:
        for key, v in prompts.items():
            if key == "기본":
                continue
            if key in biz_type or biz_type in key:
                entry = v
                break
    if not entry:
        entry = prompts.get("기본", {})
    entry = entry or {}
    return (entry.get("title_prefix") or "dong").strip().lower()


def _build_full_title(place: dict, keyword: str, suffix: str) -> str:
    """제목 조합: [지역+업종] [업체명] [마무리 문구] — 업종별 prefix 형식 적용"""
    import re as _re
    biz_type = _extract_biz_type(place, keyword)
    dong = place.get("dong", "")
    name = place.get("name", "")
    # nearby_station 정리: 노선 prefix 제거 + 끝의 "역" 한 글자만 제거
    _raw_station = (place.get("nearby_station") or "").strip()
    # 노선 이름 제거 — 한자형(선릉역의 "선"과 충돌 방지로 "선" 미포함) + 호선형 + GTX
    _raw_station = _re.sub(
        r"^(?:수인분당|신분당|공항철도|경춘|경의중앙|경강|김포골드|우이신설|신림|GTX-?[A-Z]+|(?:인천)?\d+호선)\s*",
        "",
        _raw_station,
    ).strip()
    # 끝의 "역" 한 글자만 제거 (역삼역 → 역삼, 학동역 → 학동)
    if _raw_station.endswith("역"):
        station = _raw_station[:-1]
    else:
        station = _raw_station
    addr = (place.get("address", "") or "") + " " + (place.get("jibun_address", "") or "")
    gu_match = _re.search(r"([가-힣]+구)", addr)
    gu = gu_match.group(1) if gu_match else ""

    # dong 추출: place 필드 → 주소 → 검색 키워드(예: "역삼동헬스장" → "역삼동") → 업체명
    if not dong:
        for src in (addr, keyword, name):
            m = _re.search(r"([가-힣]{1,4}동)(?:\s|$|[^가-힣])", src + " ")
            if m:
                dong = m.group(1)
                break

    # 시골 단위 추출 (읍/면/리) — 동의 폴백
    eup = ""; myeon = ""; ri = ""
    for src in (addr, keyword):
        if not eup:
            m = _re.search(r"([가-힣]{1,4}읍)(?:\s|$|[^가-힣])", src + " ")
            if m: eup = m.group(1)
        if not myeon:
            m = _re.search(r"([가-힣]{1,4}면)(?:\s|$|[^가-힣])", src + " ")
            if m: myeon = m.group(1)
        if not ri:
            m = _re.search(r"([가-힣]{1,4}리)(?:\s|$|[^가-힣])", src + " ")
            if m: ri = m.group(1)

    # 시·군 추출 (구 폴백) — 광역시·특별시 제외
    _METROS = {"서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
               "대전광역시", "울산광역시", "세종특별자치시"}
    si = ""
    for s in _re.findall(r"([가-힣]+시)", addr):
        if s not in _METROS:
            si = s
            break
    gun_match = _re.search(r"([가-힣]+군)", addr)
    gun = gun_match.group(1) if gun_match else ""

    # station 추출 보완
    if not station:
        m = _re.search(r"([가-힣A-Za-z0-9]{1,8})역", keyword + " " + name)
        if m:
            station = m.group(1)

    # gu 보완
    if not gu:
        m = _re.search(r"([가-힣]{1,4}구)", keyword)
        if m:
            gu = m.group(1)

    # 폴백 헬퍼
    def _pick_dong_level():
        # 동 → 읍 → 면 → 리
        return dong or eup or myeon or ri
    def _pick_gu_level():
        # 구 → 시 → 군
        return gu or si or gun

    # 포스트 생성 다이얼로그에서 형식 지정 (dong/station/gu/free:...) — 미지정시 dong 기본
    forced = (place.get("_override_title_prefix") or "").strip()
    forced_lower = forced.lower()
    is_free = forced_lower.startswith("free:")
    is_forced = forced_lower in ("dong", "station", "gu") or is_free
    ptype = forced_lower if not is_free else "free"

    if is_free:
        free_text = forced[5:].strip()
        prefix = free_text if free_text else biz_type
    elif ptype == "dong":
        loc = _pick_dong_level()
        prefix = f"{loc}{biz_type}" if loc else biz_type
    elif ptype == "station":
        prefix = f"{station}역{biz_type}" if station else biz_type
    elif ptype == "gu":
        loc = _pick_gu_level()
        prefix = f"{loc}{biz_type}" if loc else biz_type
    else:
        prefix = biz_type

    # 강제 형식이 아닐 때만 다른 형식으로 폴백 (자동 모드)
    if not is_forced and prefix == biz_type:
        loc_d = _pick_dong_level()
        loc_g = _pick_gu_level()
        if loc_d:
            prefix = f"{loc_d}{biz_type}"
        elif station:
            prefix = f"{station}역 {biz_type}"
        elif loc_g:
            prefix = f"{loc_g}{biz_type}"

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
    # jibun_address는 이미 행정동(address)+지번을 합친 완전 주소 → addr 재결합 시 중복됨
    full_addr = (jibun or addr).strip()

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

    # 지역 단위(시/구/동) 보강: place 필드 우선, 없으면 실제 주소에서 추출
    # (크롤러가 dong/시/구를 채우지 못한 경우의 폴백 — 프롬프트에 지역 키워드가 비지 않도록)
    dong = (place.get("dong", "") or "").strip()
    gu = (place.get("구", "") or "").strip()
    si = (place.get("시", "") or "").strip()
    if not dong:
        _m = _re.search(r"([가-힣]{1,4}동)(?:\s|$|[^가-힣])", (full_addr or "") + " ")
        if _m:
            dong = _m.group(1)
    if not gu:
        _m = _re.search(r"([가-힣]{1,4}구)", full_addr or "")
        if _m:
            gu = _m.group(1)
    if not si:
        _m = _re.search(r"([가-힣]+시)", full_addr or "")
        if _m:
            si = _m.group(1)

    # 근처역 상세(역명 + 거리, 예: "역삼역 약 350m") — 없으면 역명만
    station_detail = (place.get("nearby_station_text", "") or "").strip() \
        or (place.get("nearby_station", "") or "").strip() \
        or "대중교통·자차 모두 접근 편한 위치"

    replacements = {
        "{업체명}": place.get("name", ""),
        "{주소}": full_addr,
        "{근처역}": place.get("nearby_station", ""),
        "{근처역상세}": station_detail,
        "{시}": si,
        "{구}": gu,
        "{동}": dong,
        "{카테고리}": place.get("category", ""),
        "{앞키워드}": place.get("front_keywords", ""),
        "{태그}": place.get("tags", ""),
        "{업종}": biz_type,
        "{키워드}": effective_keyword,
        "{근처역/교통}": station_detail,
        "{기타 설명}": place.get("category", ""),
    }

    result = template
    for key, val in replacements.items():
        result = result.replace(key, val)
    return result


def _strip_markdown(text: str) -> str:
    """마크다운 기호 제거 (**bold**, *italic*, #, 등)"""
    import re as _re
    text = _re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)  # **bold**, *italic*
    text = _re.sub(r"#{1,6}\s*", "", text)
    text = _re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


_META_PHRASES = (
    "키워드", "만들어", "만들겠", "생성", "결과물", "마무리 문구",
    "다음과 같이", "다음과같이", "리스트", "제공", "참고하여",
    "바탕으로", "추천 문구", "여기 있습니다", "준비했습니다",
    "다음과 같은", "출력합니다", "응답", "예시는",
)


def _is_meta_response(text: str) -> bool:
    """GPT가 인사/설명을 첫 줄에 출력한 메타 응답인지 판별"""
    if not text:
        return True
    if len(text) > 55:  # 마무리 문구 상한(50자)보다 길면 메타/설명 의심
        return True
    for ph in _META_PHRASES:
        if ph in text:
            return True
    return False


def _pick_clean_title(candidates: list, place: dict, keyword: str) -> str:
    """10개 후보 중 블랙리스트 단어가 없는 후보를 랜덤 선택. 없으면 가장 덜 오염된 것을 정제."""
    import random as _random
    blacklist = _title_blacklist(place, keyword)
    # 마크다운 제거 + 마무리 문구 상한(50자, 네이버 제목 100자 내 여유) — 자를 땐 단어 경계에서
    _MAX = 50
    def _prep(c):
        c = _strip_markdown(c)
        import re as _re
        c = _re.split(r"[.。!！?？\n]", c)[0].strip()
        if len(c) > _MAX:
            c = c[:_MAX].rsplit(" ", 1)[0].strip() or c[:_MAX].strip()
        return c.strip()

    # 메타 응답 후보 제외 (원본 텍스트로 판별 후 정제)
    filtered = [c for c in candidates if not _is_meta_response(c)]
    if not filtered:
        filtered = candidates
    cleaned_candidates = [_prep(c) for c in filtered]

    # 1) 블랙리스트 단어가 없는 깨끗한 후보 중 랜덤 선택 (3~50자)
    ok = [c for c in cleaned_candidates if _is_suffix_clean(c, blacklist) and 3 <= len(c) <= _MAX]
    if ok:
        return _random.choice(ok)
    # 2) 정제 후 최소 3자 이상 남는 후보 중 랜덤 선택
    ok2 = []
    for c in cleaned_candidates:
        cleaned = _clean_suffix(c, blacklist)
        if cleaned and 3 <= len(cleaned) <= _MAX:
            ok2.append(cleaned)
    if ok2:
        return _random.choice(ok2)
    return cleaned_candidates[0] if cleaned_candidates else ""


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

    # 제목에서 마크다운 및 특수문자 제거
    title = _strip_markdown(title)
    title = title.replace(" - ", " ").replace("-", " ").replace(":", " ").replace("|", " ").strip()

    tag_match = re.search(r"\[태그\]\s*(.+?)(?:\n|$)", raw_text)
    tags = []
    if tag_match:
        tag_text = tag_match.group(1).strip()
        tags = [t.strip().lstrip("#") for t in re.split(r"[,\s#]+", tag_text) if t.strip()]

    # 태그가 비어있으면 본문에서 #태그 패턴 추출
    # (# 뒤 첫 글자가 한글/영숫자인 것만 — 마크다운 ##/### 헤더가 태그로 잡히는 것 방지)
    if not tags:
        hash_tags = re.findall(r"#([가-힣A-Za-z0-9][^\s#]*)", raw_text)
        if hash_tags:
            tags = [t.strip() for t in hash_tags if t.strip()]

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


def _build_hashtags(place: dict, keyword: str) -> list:
    """지역+업종 기반 네이버 블로그 검색용 해시태그 (구/동/역/시 + 업체명).
    GPT 출력과 무관하게 코드로 생성 — 감성/페르소나(효자효녀 등) 태그 원천 차단."""
    biz = _extract_biz_type(place, keyword)
    if not biz:
        return []
    addr = (place.get("address", "") or "") + " " + (place.get("jibun_address", "") or "")
    dong = (place.get("dong", "") or "").strip()
    if not dong:
        m = re.search(r"([가-힣]{1,4}동)(?:\s|$|[^가-힣])", addr + " ")
        dong = m.group(1) if m else ""
    gu = (place.get("구", "") or "").strip()
    if not gu:
        m = re.search(r"([가-힣]{1,4}구)", addr)
        gu = m.group(1) if m else ""
    metro = ""
    for stem in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
                 "경기", "강원", "충청", "충북", "충남", "전라", "전북", "전남",
                 "경상", "경북", "경남", "제주"]:
        if stem in addr:
            metro = stem
            break
    station = (place.get("nearby_station", "") or "").strip()
    station = re.sub(r"^(?:수인분당|신분당|공항철도|경춘|경의중앙|경강|김포골드|우이신설|신림|GTX-?[A-Z]+|(?:인천)?\d+호선)\s*", "", station)
    if station.endswith("역"):
        station = station[:-1]
    name = (place.get("name", "") or "").strip().replace(" ", "")
    out = []
    def _add(t):
        t = (t or "").strip()
        if t and t not in out:
            out.append(t)
    if gu: _add(f"{gu}{biz}")
    if dong: _add(f"{dong}{biz}")
    if station: _add(f"{station}역{biz}")
    if metro: _add(f"{metro}{biz}")
    _add(f"{biz}추천")          # 업종(키워드)+추천 — 전 업종 공통
    if name: _add(name)
    return out[:7]


def generate_content(provider: str, api_key: str, place: dict, keyword: str, prompt_override: str = None, title_prefix: str = None) -> dict:
    """통합 생성 함수 — GPT 전용 (Gemini는 안정성/가격 이슈로 비활성화).
    provider 인자는 하위호환을 위해 남겨두나 무시됨.
    title_prefix: "dong"/"station"/"gu"로 제목 prefix 형식 강제, None이면 prompts.json 기본값."""
    if prompt_override or title_prefix:
        place = dict(place)
        if prompt_override:
            place["category"] = prompt_override
        if title_prefix:
            place["_override_title_prefix"] = title_prefix
    result = generate_with_gpt(api_key, place, keyword)

    # 해시태그: GPT 출력(페르소나/감성 섞임)을 무시하고 코드로 '지역+업종' 검색태그만 생성.
    # 본문 끝의 GPT 해시태그/[태그] 줄은 제거하고 코드 태그로 깔끔히 교체.
    htags = _build_hashtags(place, keyword)
    if htags:
        body = result.get("body", "") or ""
        body = re.sub(r'(?m)^\s*\[태그\].*$', '', body)   # [태그] 줄 제거
        # 해시태그(#단어)가 2개 이상 들어간 줄은 GPT가 만든 태그 줄 → 통째 제거
        # (첫 단어에 #이 없어도, 줄 어디에 있어도 잡음)
        body = "\n".join(ln for ln in body.split("\n")
                         if len(re.findall(r'#[^\s#]+', ln)) < 2)
        result["body"] = body.rstrip() + "\n\n" + " ".join("#" + t for t in htags)
        result["tags"] = htags

    return result
