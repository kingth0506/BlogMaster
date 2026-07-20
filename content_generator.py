# -*- coding: utf-8 -*-
"""AI 기반 블로그 글 생성 모듈 — 프롬프트 시스템 연동"""
import re
import json as _json
import random
import threading
import openai
from prompts import get_prompt_for_keyword


# ── 도입부 중복 방지: 최근 첫 문장 시그니처를 기억해두고 겹치면 다시 뽑는다 ──
_seen_lock = threading.Lock()

def _openings_path():
    from app_paths import data_file
    return data_file("recent_openings.json")

def _opening_sig(text: str) -> str:
    """첫 문장 시작부 시그니처 — 공백/문장부호 제거 후 앞 16자."""
    first = (text or "").strip().split("\n")[0]
    s = re.sub(r"[\s.,!?~…\"'()\[\]·]+", "", first)
    return s[:16]

def _split_title(text: str):
    """본문 끝의 '===제목===' 다음 줄 문구를 제목 suffix로 분리. (body, suffix) 반환."""
    if not text:
        return "", ""
    parts = re.split(r'\n?\s*===\s*제목\s*===\s*\n?', text, maxsplit=1)
    if len(parts) == 2:
        body = parts[0].rstrip()
        suffix = parts[1].strip().split("\n")[0].strip().strip('"\'').strip()
        return body, suffix
    return text, ""


def _check_reserve_opening(sig: str) -> bool:
    """sig가 이미 있으면 True(중복). 없으면 즉시 등록(예약)하고 False. (병렬 생성 안전)"""
    if not sig:
        return False
    with _seen_lock:
        path = _openings_path()
        try:
            from app_paths import safe_load_json as _slj
            seen = _slj(path, default=[], max_mb=10)
            if not isinstance(seen, list):
                seen = []
        except Exception:
            seen = []
        if sig in seen:
            return True
        seen.append(sig)
        seen = seen[-500:]   # 최근 500개만 유지
        try:
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(seen, f, ensure_ascii=False)
        except Exception:
            pass
        return False


# ── 글마다 다른 결을 주기 위한 '변형 지시' (기본 프롬프트는 그대로, 스타일만 랜덤) ──
# ★ 공통 시점: '그냥 가봤다' 후기가 아니라, 필요해서 좋은 곳을 찾아 헤매다 이곳을 발견한 느낌.
# 첫 문장 '형태(모드)'만 랜덤 지정 — 예시 문장은 주지 않는다(베껴서 반복되는 것 방지).
_VAR_OPENING = [
    "첫 문장을 속마음·혼잣말 톤으로 열어라.",
    "첫 문장을 짧고 강한 한마디로 열어라.",
    "첫 문장을 독자에게 던지는 질문으로 열어라.",
    "첫 문장을 구체적인 장면·행동 묘사로 열어라.",
    "첫 문장을 결론부터 던지며 열어라.",
    "첫 문장을 주변 사람과의 대화·조언으로 열어라.",
    "첫 문장을 겪던 고민의 핵심으로 바로 들어가 열어라.",
    "첫 문장을 계기가 된 사건으로 열어라.",
]
# 첫 부분의 '내용 각도'를 랜덤으로 — 알맹이가 달라져 첫 문장이 자연히 갈린다(베낄 문장 없음).
_VAR_INTRO_ANGLE = [
    "비용이 부담돼 망설였던 마음",
    "시간이 없어 급했던 상황",
    "처음이라 뭘 모르던 막막함",
    "후기를 믿기 어려웠던 의심",
    "주변에 물어봐도 답이 없던 답답함",
    "여러 번 실망한 뒤라 신중해진 태도",
    "가까운 곳부터 알아보던 기준",
    "실력·전문성을 가장 중요하게 봤던 점",
    "가족·지인의 권유가 계기가 된 점",
    "더 미룰 수 없어 결심하게 된 순간",
]
_VAR_TONE = [
    "전체 말투는 친근하고 다정한 구어체로.",
    "전체 말투는 차분하고 신뢰감 있는 정보 전달형으로.",
    "전체 말투는 활기차고 생동감 있게.",
    "전체 말투는 담백하고 깔끔하게, 군더더기 없이.",
    "전체 말투는 친구에게 추천하듯 솔직하게.",
]
_VAR_STRUCTURE = [
    "장점을 먼저 풀고 뒤에서 상세 정보를 정리하는 순서로.",
    "정보·특징을 먼저 정리하고 뒤에서 느낌·추천으로 마무리하는 순서로.",
    "이야기 흐름(스토리텔링)으로 자연스럽게 이어가되 중간중간 핵심 정보를 녹여라.",
    "핵심 포인트 몇 가지를 중심으로 각 포인트를 풀어가는 구성으로.",
]
_VAR_EMPHASIS = [
    "이번 글은 '분위기·공간'을 특히 강조하라.",
    "이번 글은 '서비스·응대'를 특히 강조하라.",
    "이번 글은 '접근성·위치·편의'를 특히 강조하라.",
    "이번 글은 '가격·구성·가성비'를 특히 강조하라.",
    "이번 글은 '전문성·경험'을 특히 강조하라.",
]


def _variation_directive() -> str:
    """매 호출마다 랜덤 조합 — 같은 업체·키워드라도 글의 결이 달라지게.
    출력 형식(소제목/이미지 마커 등)은 절대 바꾸지 말 것을 명시."""
    parts = [
        random.choice(_VAR_TONE),
        random.choice(_VAR_STRUCTURE),
        random.choice(_VAR_EMPHASIS),
        "같은 표현·문장 구조를 반복하지 말고 어휘를 다양하게 바꿔라.",
    ]
    random.shuffle(parts)
    # 고정 시점 앵커 — 모든 글이 '필요해서 찾다가 발견' 프레임을 갖도록
    anchor = ("글 전체를 '필요해서 좋은 곳을 찾아 여기저기 알아보고 비교하다가 결국 이곳을 "
              "발견하게 된' 시점으로 풀어라. 단순히 '가봤어요'가 아니라, 찾아 헤맨 끝에 만난 느낌을 살려라.")
    # 도입부: '형태(모드)' + '내용 각도'를 랜덤으로 → 첫 문장이 매번 갈림 (베낄 예시는 주지 않음)
    opening = (random.choice(_VAR_OPENING)
               + " 도입에 '" + random.choice(_VAR_INTRO_ANGLE) + "'을(를) 녹여라.")
    fixed = [
        opening,
        "★첫 문장을 '최근/요즘/얼마 전/며칠 전/요새/근래/저는/저도' 같은 흔한 말로 시작하지 마라. "
        "매 글의 첫 문장을 서로 완전히 다르게 열어라(같은 시작어 반복 금지).",
        "분량은 공백 포함 2000자 이상(50문장 이상)으로 충분히 길고 풍부하게 써라. 절대 짧게 끝내지 마라.",
    ]
    return ("\n\n[이번 글 작성 스타일 — 아래 지시를 반영하되, 위에서 요구한 "
            "글자수·소제목·이미지 마커 등 출력 형식은 그대로 유지하라]\n- "
            + "\n- ".join(fixed) + "\n- " + "\n- ".join(parts))


# ── 업종 관점 격리 (다른 업종 소재 침범 0) ─────────────────────────
_ELDERCARE = ("요양원", "요양병원", "실버타운", "주야간", "데이케어", "노인요양", "노인", "실버", "치매", "요양")
_CHILDCARE = ("어린이집", "유치원", "키즈", "소아", "아동", "놀이학교", "영유아", "유아")

def _harden_perspective(prompt: str, place: dict, keyword: str) -> str:
    """프롬프트의 '★ 글쓴이 관점' 섹션을 해당 업종 전용으로 교체.
    다른 업종 소재(특히 요양원·어르신)를 프롬프트에서 제거 + 강한 금지 → 오염 0."""
    biz = " ".join(str(place.get(k, "")) for k in ("category", "업종", "search_keyword")) + " " + str(keyword or "")
    is_elder = any(w in biz for w in _ELDERCARE)
    is_child = any(w in biz for w in _CHILDCARE)
    if is_elder:
        persp = ("글쓴이는 '가족'이며, 부모님·할머니·할아버지(어르신)를 모실 곳을 찾는 입장에서 쓴다. "
                 "어르신 돌봄에 관한 글이므로 가족 시점이 자연스럽다.")
        ban = ""
    elif is_child:
        persp = "글쓴이는 '부모'이며, 자녀를 위해 이곳을 찾는 입장에서 쓴다."
        ban = "★★★ 절대 금지: 요양원·어르신·부모님 돌봄 등 노인 돌봄 소재를 단 한 문장도 넣지 마라."
    else:
        persp = "글쓴이는 '본인'이며, 본인이 직접 이용/해결하려고 이곳을 찾는 입장에서 쓴다."
        ban = ("★★★ 절대 금지: 요양원·어르신·부모님·조부모·노인 돌봄·자녀 돌봄 등 이 업종과 무관한 "
               "다른 업종/소재를 단 한 문장, 단 한 단어도 넣지 마라. 다른 업종 이야기가 들어가면 실패한 글이다.")
    block = (f"### ★ 글쓴이 관점 (엄격 — 이것만 따르라)\n"
             f"이 글은 오직 '{keyword}' 그 자체에 관한 글이다. {persp}\n"
             + (ban + "\n" if ban else "") + "\n")
    secs = re.split(r'(?=### )', prompt)
    out, replaced = [], False
    for s in secs:
        if s.startswith('### ★ 글쓴이 관점'):
            out.append(block); replaced = True
        else:
            out.append(s)
    if not replaced:
        out.insert(0, block)
    return "".join(out)


def generate_with_gpt(api_key: str, place: dict, keyword: str, engine: str = "gpt") -> dict:
    """블로그 글 생성 — engine='deepseek' / 'gpt' / 'gemini'. (제미나이는 OpenAI 호환 엔드포인트 사용)"""
    if engine == "deepseek":
        client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        model = "deepseek-chat"
    elif engine == "gemini":
        client = openai.OpenAI(api_key=api_key,
                               base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
        model = "gemini-2.5-flash"
    else:
        client = openai.OpenAI(api_key=api_key)
        model = "gpt-4o-mini"
    # 지역 확장 크롤링: 이 업체가 수집된 실제 검색 키워드(예: "강남구 파스타") 우선
    keyword = place.get("search_keyword") or keyword
    prompt_data = get_prompt_for_keyword(keyword)
    prompt = _fill_prompt(prompt_data.get("blog", ""), place, keyword)
    prompt = _harden_perspective(prompt, place, keyword)   # ★ 업종 관점 격리 (다른 업종 소재 침범 0)
    prompt = prompt + _variation_directive()   # 글마다 다른 스타일 지시 (반복 방지)
    # 제목을 같은 호출에서 함께 생성 (별도 호출 제거로 API 호출 절감, 품질 동일)
    prompt = prompt + ("\n\n[제목 출력] 본문을 모두 쓴 뒤 맨 마지막에 별도 줄로 '===제목===' 을 출력하고, "
                       "그 다음 줄에 제목 마무리 문구 1개만 15자 이내로 써라. "
                       "지역명·업종·업체명·해시태그·기호는 넣지 말고, 검색자가 클릭하고 싶은 간결하고 진정성 있는 문구로.")

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
        _kw = dict(
            model=model,
            messages=[
                {"role": "system", "content": "너는 블로그 글쓰기 전문가다. 주어진 지시사항에 따라 블로그 본문만 작성한다. 평가·칭찬·설명·인사 없이 오직 블로그 본문 텍스트만 출력한다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
            max_tokens=4096,
        )
        # 제미나이(OpenAI 호환)는 frequency/presence_penalty 미지원 → 딥시크·GPT에만 적용
        if engine != "gemini":
            _kw["frequency_penalty"] = 0.25
            _kw["presence_penalty"] = 0.2
        response = client.chat.completions.create(**_kw)
    except Exception as e:
        _low = str(e).lower()
        # 제미나이 무료 한도 초과 (RESOURCE_EXHAUSTED / 429 / rate limit)
        if engine == "gemini" and ("resource_exhausted" in _low or "rate limit" in _low
                or "quota" in _low or "429" in _low):
            raise RuntimeError("제미나이 무료 사용 한도를 초과했습니다. 잠시 후 다시 시도하거나, "
                               "내일(한도 초기화 후) 다시 이용해주세요. (또는 딥시크·챗GPT 키 사용)") from e
        # 딥시크/GPT 잔액(크레딧) 소진
        if ("insufficient_quota" in _low or "exceeded your current quota" in _low
                or "insufficient balance" in _low or "insufficient_balance" in _low
                or ("quota" in _low and "exceed" in _low) or "billing_not_active" in _low):
            raise RuntimeError("API 크레딧(잔액)이 부족합니다. 사용 중인 API 키에 결제·충전을 해주세요.") from e
        raise RuntimeError(f"AI API 호출 실패: {e}") from e

    if not response.choices:
        raise RuntimeError("AI 응답 없음 (choices 비어있음)")
    raw_text = response.choices[0].message.content or ""
    if not raw_text.strip():
        raise RuntimeError("AI 응답 본문이 비어있음")

    # 본문에서 제목 문구 분리 (같은 호출로 받은 것)
    raw_text, title_suffix = _split_title(raw_text)

    # ★ 첫머리 상투적 시간부사 제거 — "최근/요즘/얼마 전" 등으로 시작하는 습관 강제 차단
    _LEAD = r'^\s*(?:최근에|최근\s|요즘에|요즘|요새|근래에|근래|얼마\s*전,?|며칠\s*전,?)\s*'
    def _strip_lead(t):
        try:
            return re.sub(_LEAD, '', (t or '').lstrip(), count=1)
        except Exception:
            return t or ''
    raw_text = _strip_lead(raw_text)

    # ★ 도입부 중복 방지 — 첫 문장이 최근 글과 겹치면 다시 뽑는다 (최대 2회). 병렬 생성 안전.
    sig = _opening_sig(raw_text)
    tries = 0
    while _check_reserve_opening(sig) and tries < 2:
        tries += 1
        first_line = raw_text.strip().split("\n")[0][:30]
        try:
            _rgkw = dict(
                model=model,
                messages=[
                    {"role": "system", "content": "너는 블로그 글쓰기 전문가다. 블로그 본문만 출력한다."},
                    {"role": "user", "content": prompt + f"\n\n★★첫 문장을 반드시 \"{first_line}\"와 완전히 다른 표현·다른 시작으로 열어라. 앞부분이 조금이라도 겹치면 안 된다."},
                ],
                temperature=1.0,
                max_tokens=4096,
            )
            if engine != "gemini":
                _rgkw["frequency_penalty"] = 0.3
                _rgkw["presence_penalty"] = 0.3
            rg = client.chat.completions.create(**_rgkw)
            nt = (rg.choices[0].message.content or "").strip()
            if nt:
                nt, nts = _split_title(nt)
                if nts:
                    title_suffix = nts
                raw_text = _strip_lead(nt)
                sig = _opening_sig(raw_text)
        except Exception:
            break

    # ★ 길이 보강 — 짧으면 한 번 '한두 단락만' 이어 써서 1500자+ 보장 (과증식 방지로 가볍게)
    # 코드 해시태그로 교체되며 약간 짧아지므로 1550자 버퍼로 트리거
    try:
        if len(raw_text) < 1550:
            cont = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "너는 블로그 글쓰기 전문가다. 블로그 본문만 출력한다."},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": raw_text},
                    {"role": "user", "content": f"방금 글이 약 {len(raw_text)}자로 살짝 짧다. 같은 업체·같은 시점·같은 말투로, 더 구체적인 내용 한두 단락만 자연스럽게 이어 써서 전체가 1800자 정도가 되게 해라. 이미 쓴 내용 반복 금지. 마무리 인사·해시태그·이미지 마커([이미지])·제목(===제목===)은 새로 붙이지 말고 이어지는 본문 문장만 출력해라."},
                ],
                temperature=0.9,
                max_tokens=900,
            )
            more = (cont.choices[0].message.content or "").strip()
            if more:
                more, _ = _split_title(more)   # 혹시 제목 붙어오면 제거
                raw_text = raw_text.rstrip() + "\n\n" + more
    except Exception:
        pass

    # 디버그: 응답도 저장
    try:
        dbg2 = _os.path.join(_os.path.dirname(__file__), "last_response.txt")
        with open(dbg2, "w", encoding="utf-8") as _f:
            _f.write(raw_text or "")
    except Exception:
        pass
    # 제목은 본문 호출에서 함께 받은 title_suffix 사용 (별도 GPT 호출 제거)
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
            # 제목 형식 — ★순서 고정: 주요키워드(지역+업종) → 업체명 → 수식어(마무리 문구).
            # 구분 기호만 랜덤으로 다양화 (업체명/수식어 순서는 절대 뒤바뀌지 않음)
            templates = [
                "{p} {n} {c}",
                "{p} {n} - {c}",
                "{p}, {n} {c}",
                "{p} {n}, {c}",
            ]
            return random.choice(templates).format(p=prefix, n=name, c=clean).strip()

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
            temperature=0.95,
            frequency_penalty=0.4,   # 제목 표현 다양화
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
        "image_count": 3,  # 무조건 3장 고정
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
    # 핵심 태그(검색 가치 큰 것 — 가능하면 포함) + 선택 풀
    core, pool = [], []
    if dong: core.append(f"{dong}{biz}")
    if gu: core.append(f"{gu}{biz}")
    if station: pool.append(f"{station}역{biz}")
    if metro: pool.append(f"{metro}{biz}")
    pool.append(f"{biz}추천")
    if dong: pool.append(f"{dong}{biz}추천")
    if gu: pool.append(f"{gu}{biz}추천")
    pool.append(biz)
    if name: pool.append(name)
    # 중복 제거(코어 기준)
    seen = set(core)
    pool = [t for t in pool if t and not (t in seen or seen.add(t))]
    # 개수 랜덤(5~8), 순서 랜덤
    target = random.randint(5, 8)
    random.shuffle(pool)
    chosen = core + pool[:max(0, target - len(core))]
    random.shuffle(chosen)
    return chosen[:8]


def generate_content(provider: str, api_key: str, place: dict, keyword: str, prompt_override: str = None, title_prefix: str = None, deepseek_key: str = None, gpt_key: str = None, gemini_key: str = None, engine: str = None) -> dict:
    """통합 생성 함수 — 사용자가 선택한 엔진(engine)으로 생성.
    engine: 'deepseek' / 'gpt' / 'gemini'. 선택 엔진 실패(크레딧/한도)면 그대로 에러(안내용).
    title_prefix: "dong"/"station"/"gu"로 제목 prefix 형식 강제, None이면 prompts.json 기본값."""
    if prompt_override or title_prefix:
        place = dict(place)
        if prompt_override:
            place["category"] = prompt_override
        if title_prefix:
            place["_override_title_prefix"] = title_prefix
    # 선택 엔진 → 키 매핑
    keymap = {"deepseek": deepseek_key, "gpt": gpt_key, "gemini": gemini_key}
    eng = (engine or "").strip().lower()
    if eng not in ("deepseek", "gpt", "gemini") or not keymap.get(eng):
        # 엔진 미지정/키없음 → 있는 키 아무거나 (하위호환: 딥시크>GPT>제미나이)
        eng = next((e for e in ("deepseek", "gpt", "gemini") if keymap.get(e)), None)
    if not eng:
        raise RuntimeError("선택한 엔진의 API 키가 없습니다. 설정에서 API 키를 입력해주세요.")
    result = generate_with_gpt(keymap[eng], place, keyword, engine=eng)

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
