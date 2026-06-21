"""Pixabay 이미지 검색 및 다운로드 모듈"""
import os
import re
import requests
import tempfile


PIXABAY_API_URL = "https://pixabay.com/api/"

# 한국어 업종 → 영어 Pixabay 검색어 매핑
BIZ_TO_EN = {
    "헬스장": ["fitness", "gym fitness", "fitness workout", "dumbbell fitness"],
    "헬스클럽": ["fitness", "gym fitness", "fitness workout", "dumbbell fitness"],
    "피트니스": ["fitness", "gym fitness", "fitness workout", "dumbbell fitness"],
    "피트니스센터": ["fitness", "gym fitness", "fitness workout", "dumbbell fitness"],
    "요가": ["yoga", "yoga studio", "yoga mat", "meditation", "yoga pose"],
    "필라테스": ["pilates", "pilates studio", "pilates reformer", "pilates class"],
    "요양원": ["nursing home building", "senior care facility", "retirement home", "elderly care facility interior", "assisted living"],
    "요양센터": ["senior care facility", "elderly care facility", "retirement home"],
    "요양병원": ["senior hospital", "elderly hospital", "medical care facility", "rehabilitation center"],
    "카페": ["cafe", "coffee shop", "latte art", "coffee beans", "cafe interior", "espresso"],
    "음식점": ["restaurant", "food", "dining", "meal"],
    "식당": ["restaurant", "dining", "food"],
    "한식": ["korean food", "kimchi", "bulgogi", "bibimbap", "korean cuisine"],
    "일식": ["sushi", "ramen", "japanese food", "sashimi"],
    "중식": ["chinese food", "dumpling", "noodles"],
    "양식": ["steak", "pasta", "pizza", "western food"],
    "미용실": ["hair salon", "hairstyle", "barber", "hairdresser"],
    "네일": ["nail art", "manicure", "nail polish"],
    "네일샵": ["nail art", "manicure", "pedicure"],
    "학원": ["classroom", "student", "study", "education", "books"],
    "치과": ["dental clinic", "dentist", "teeth"],
    "병원": ["hospital", "clinic", "doctor", "medical"],
    "약국": ["pharmacy", "drugstore", "medicine"],
    "마트": ["supermarket", "grocery", "shopping"],
    "편의점": ["convenience store", "shop"],
    "베이커리": ["bakery", "bread", "pastry", "croissant"],
    "빵집": ["bakery", "bread", "pastry"],
    "술집": ["pub", "bar", "cocktail"],
    "호프": ["beer", "pub", "bar"],
    "노래방": ["karaoke", "singing", "microphone"],
    "pc방": ["gaming", "gaming cafe", "esport", "gamer"],
    "피시방": ["gaming", "gaming cafe", "esport", "gamer"],
    "세탁소": ["laundry", "washing machine"],
    "부동산": ["real estate", "house", "apartment"],
    "변호사": ["law office", "lawyer attorney", "law firm office", "court gavel"],
    "법률사무소": ["law office", "law firm", "attorney office", "legal office"],
    "법무법인": ["law firm", "attorney office", "law office interior"],
    "법무사": ["law office", "legal office", "document"],
    "회계": ["accounting", "finance", "calculator"],
    "세무사": ["accounting office", "tax office", "calculator"],
    "스튜디오": ["photo studio", "camera"],
    "사진관": ["photo studio", "portrait"],
    # 운동/뷰티
    "골프장": ["golf course", "golf club", "golf green"],
    "골프연습장": ["golf driving range", "indoor golf", "golf practice"],
    "스크린골프": ["indoor golf simulator", "golf simulator", "screen golf"],
    "왁싱샵": ["waxing beauty salon", "body hair removal beauty", "waxing treatment salon", "smooth skin beauty"],
    "왁싱": ["hair removal wax beauty", "body wax treatment", "waxing beauty service", "leg waxing beauty"],
    "메이크업": ["makeup", "beauty makeup", "cosmetics"],
    # 의료
    "안과": ["eye clinic", "ophthalmology", "eye exam"],
    "피부과": ["dermatology clinic", "skin clinic", "skincare clinic"],
    "성형외과": ["plastic surgery clinic", "cosmetic surgery"],
    "통증의학과": ["pain clinic", "rehabilitation clinic", "physical therapy"],
    "동물병원": ["veterinary clinic", "vet hospital", "animal clinic"],
    # 숙박/공간
    "풀빌라": ["pool villa", "luxury villa pool", "private pool resort"],
    "펜션": ["cozy cabin interior lodging", "countryside guesthouse cabin", "rural lodge wooden interior", "wooden cabin guesthouse"],
    "캠핑장": ["camping ground", "camping tent", "glamping"],
    "고시원": ["small dormitory room interior", "budget single room interior", "tiny room interior", "single room dormitory"],
    "원룸텔": ["studio apartment room interior", "one room flat interior", "small apartment interior", "budget apartment room"],
    "공유오피스": ["coworking space interior", "shared office desk workspace", "modern coworking office", "startup office space"],
    "파티룸": ["party room", "event space", "rental space"],
    # 학습/F&B
    "스터디카페": ["study cafe", "study room", "library desk"],
    "맛집": ["restaurant food", "korean restaurant", "dining table"],
    # 자동차
    "카센터": ["auto repair shop", "mechanic garage", "car service"],
    "자동차정비소": ["auto repair shop", "mechanic garage"],
    "타이어": ["tire shop", "car tire", "wheel"],
    "손세차": ["car wash", "hand car wash", "car detailing"],
    "디테일링": ["car detailing", "auto detailing", "car polish"],
    "중고차": ["used car dealership", "car showroom", "used car"],
    "렌터카": ["car rental service automobile", "rental car dealership", "car hire vehicle", "car rental lot"],
    "렌트카": ["car rental service automobile", "rental car dealership", "car hire vehicle", "car rental lot"],
    # 생활/설비
    "누수탐지": ["plumbing repair", "water leak", "pipe repair"],
    "하수구": ["plumbing", "drain pipe", "pipe repair"],
    "인테리어": ["interior design", "home interior", "modern interior"],
    "가전제품": ["home appliances kitchen store", "household appliances refrigerator", "washing machine dryer appliance", "kitchen appliance modern"],
    "안마의자": ["massage chair", "recliner chair"],
    # 청소
    "가구청소": ["home cleaning", "cleaning service", "housekeeping"],
    "쇼파청소": ["sofa deep cleaning service", "couch steam cleaning", "upholstery cleaning sofa couch", "sofa stain removal"],
    "침구류청소": ["mattress cleaning", "bedding cleaning"],
    "에어컨청소": ["air conditioner unit maintenance", "hvac cleaning service", "air conditioning indoor unit", "air conditioner service"],
    # 이사/물류
    "포장이사": ["moving boxes truck relocation", "house moving service boxes", "packing boxes move house", "movers boxes truck"],
    "이사": ["moving boxes", "movers", "home moving"],
    "용달": ["delivery truck", "moving truck"],
    # 반려동물
    "반려동물": ["pet shop", "pet care", "dog cat"],
    "강아지": ["dog grooming", "puppy care", "dog park"],
    "고양이": ["cat cafe", "cat care", "cute cat"],
    # 웨딩
    "웨딩홀": ["wedding hall", "wedding venue", "ballroom"],
    "예식장": ["wedding hall indoor", "wedding ceremony venue", "wedding reception hall", "wedding banquet hall"],
    "웨딩드레스": ["wedding dress", "bridal dress", "wedding gown"],
    # 의료 추가
    "한의원": ["korean traditional medicine clinic", "acupuncture clinic", "oriental medicine", "acupuncture needles"],
    "정형외과": ["orthopedic clinic", "bone joint clinic", "orthopedic surgery", "joint rehabilitation"],
    "내과": ["internal medicine doctor office", "physician clinic room", "medical doctor consultation", "doctor patient clinic"],
    "이비인후과": ["ear nose throat doctor clinic", "ent doctor medical office", "otolaryngology clinic interior"],
    "산부인과": ["obstetrics gynecology clinic", "maternity clinic", "prenatal care", "gynecology doctor"],
    "비뇨의학과": ["urology clinic interior", "urologist medical office", "kidney health medical"],
    "재활의학과": ["physical rehabilitation center", "rehab therapy room", "physiotherapy treatment room"],
    "라식라섹": ["lasik eye surgery clinic", "vision correction eye surgery", "ophthalmology laser eye treatment"],
    "임플란트": ["dental implant surgery", "dental implant clinic", "tooth implant"],
    "치아교정": ["dental braces", "orthodontics teeth", "orthodontic treatment", "teeth alignment"],
    "건강검진": ["health checkup", "medical examination", "health screening", "body checkup"],
    # 뷰티 추가
    "피부관리실": ["facial treatment salon", "skincare beauty salon", "facial spa", "esthetic skin care"],
    "속눈썹연장": ["eyelash extension", "lash extension beauty", "false eyelashes salon"],
    "눈썹문신": ["eyebrow tattoo", "microblading eyebrow", "permanent eyebrow makeup"],
    "반영구화장": ["permanent lip makeup beauty", "eyebrow makeup woman beauty", "eyeliner permanent makeup woman", "brow makeup beauty closeup"],
    "두피케어": ["scalp treatment", "scalp care clinic", "hair scalp health"],
    "탈모클리닉": ["hair loss clinic scalp", "hair regrowth scalp treatment", "alopecia clinic hair loss"],
    "태닝샵": ["sunbed tanning salon", "indoor tanning bed beauty", "tanning bed solarium"],
    # 운동 추가
    "퍼스널트레이닝": ["personal training gym", "personal trainer fitness", "one on one fitness training"],
    "pt샵": ["personal training gym workout", "fitness trainer gym session", "one on one workout gym training"],
    "수영장": ["swimming pool", "indoor swimming pool", "swim lane pool"],
    "태권도": ["taekwondo martial arts", "taekwondo gym", "martial arts dojo"],
    "댄스학원": ["dance studio lesson", "dancing class instructor", "dance practice room studio"],
    "클라이밍": ["rock climbing gym", "indoor climbing wall", "bouldering gym"],
    "복싱": ["boxing gym", "boxing ring", "boxing training"],
    "배드민턴": ["badminton court", "badminton game", "badminton sports"],
    "테니스": ["tennis court", "tennis game", "tennis sports"],
    # 교육 추가
    "영어학원": ["english academy classroom", "english language school", "english learning class"],
    "수학학원": ["math tutoring classroom", "mathematics study", "math education"],
    "피아노학원": ["piano lesson studio", "piano keyboard music class", "piano music school room"],
    "미술학원": ["art class painting studio", "drawing art lesson", "art school painting class"],
    "코딩학원": ["coding class kids", "programming education", "computer coding school"],
    "독서실": ["study hall reading", "quiet study room", "library reading room"],
    # 음식 추가
    "치킨": ["fried chicken", "crispy chicken", "korean fried chicken"],
    "피자": ["pizza restaurant", "pizza slice", "italian pizza"],
    "삼겹살": ["korean bbq pork belly", "grilled pork belly", "korean bbq grill"],
    "고깃집": ["korean bbq restaurant", "grilled meat korean", "bbq grill restaurant"],
    "해산물": ["seafood restaurant", "fresh seafood", "seafood dish"],
    "횟집": ["raw fish sashimi restaurant", "korean sashimi", "fresh fish sliced"],
    "냉면": ["cold noodles korean", "naengmyeon", "korean cold noodle dish"],
    "아이스크림": ["ice cream shop", "gelato shop", "soft serve ice cream"],
    "버블티": ["bubble tea boba shop", "boba milk tea drink", "tapioca pearl tea shop"],
    "디저트카페": ["dessert cafe", "patisserie dessert", "cake dessert shop"],
    "와인바": ["wine bar", "wine glass restaurant", "wine cellar bar"],
    "브런치카페": ["brunch cafe", "brunch food", "cafe brunch menu"],
    # 숙박 추가
    "호텔": ["hotel lobby", "luxury hotel room", "hotel interior"],
    "모텔": ["motel room", "budget hotel room", "inn room"],
    "게스트하우스": ["guesthouse interior", "hostel common room", "backpacker hostel"],
    # 육아 추가
    "키즈카페": ["children playground indoor", "kids playground fun", "children playing indoor"],
    "산후조리원": ["postpartum care center", "maternity care facility", "newborn care room"],
    "어린이집": ["daycare center", "kindergarten classroom", "children daycare"],
    # 반려동물 추가
    "애견호텔": ["dog boarding facility kennel", "pet kennel boarding service", "dog hotel kennel care"],
    "애견미용": ["dog grooming salon", "pet grooming", "dog haircut grooming"],
    "고양이카페": ["cat cafe cats interior", "cats in coffee shop", "cat lounge cafe indoor"],
    # 체험/레저 추가
    "방탈출": ["door key lock room", "room door open lock", "escape door key puzzle"],
    "볼링장": ["bowling alley pins", "bowling lane ball pins", "bowling game alley"],
    "당구장": ["billiards pool hall", "pool table billiards", "snooker billiards"],
    "보드게임카페": ["board game cafe", "board game table", "board games collection"],
    # 생활서비스 추가
    "꽃집": ["flower shop", "florist flowers", "flower bouquet shop"],
    "플라워샵": ["flower shop interior", "florist arrangement", "fresh flowers shop"],
    "공인중개사": ["real estate agent office", "realtor office", "property agent"],
    "방역": ["pest control service", "exterminator service", "pest fumigation"],
    "도배": ["wallpaper installation wall interior", "interior wall covering decoration", "wallpaper hanging home renovation"],
    "세차장": ["car wash automatic", "automatic car wash", "car wash drive through"],
    "무인카페": ["unmanned cafe kiosk", "self service cafe", "automated coffee kiosk"],
    # 법률/금융/전문직 — 한국형 복합 키워드(예: '부산개인회생')도 1단계 부분매칭으로
    # 지역 접두를 무시하고 개념만 잡히도록 키를 직접 등록 (translator 폴백 의존 X)
    "개인회생": ["law office", "lawyer attorney", "legal document signing", "court gavel justice"],
    "개인파산": ["law office", "lawyer consultation", "legal document", "court gavel"],
    "법인회생": ["law office", "corporate lawyer meeting", "legal document", "court gavel"],
    "회생파산": ["law office", "lawyer attorney", "legal document", "court gavel"],
    "파산": ["law office", "lawyer consultation", "legal document", "court gavel"],
    "회생": ["law office", "lawyer attorney", "legal consultation document", "court gavel"],
    "채무조정": ["debt consultation meeting", "financial counseling", "calculator money document"],
    "신용회복": ["financial counseling office", "debt consultation", "finance document calculator"],
    "워크아웃": ["financial counseling", "debt restructuring meeting", "business finance document"],
    "법률상담": ["law office consultation", "lawyer client meeting", "legal advice office"],
    "노무사": ["labor law office", "hr consultation office", "employment contract document"],
    "행정사": ["administrative office document", "government paperwork office", "document filing office"],
    "손해사정": ["insurance claim document", "insurance consultation office", "claim paperwork office"],
    "대출": ["bank loan finance", "money loan document", "financial consultation calculator"],
}

# 세션 중 이미 사용된 Pixabay 이미지 ID (중복 방지)
import threading as _threading
_USED_IMAGE_IDS: set = set()
_USED_IDS_FILE: str = ""  # 설정 시 파일 경로 (영속화)
_USED_IDS_LOCK = _threading.Lock()


def configure_used_ids_file(path: str):
    """Pixabay 이미지 ID 영속화 파일 경로 지정 (계정별).
    지정하면 이후 search_images()가 파일에서 로드·저장."""
    global _USED_IDS_FILE, _USED_IMAGE_IDS
    _USED_IDS_FILE = path
    _USED_IMAGE_IDS = set()
    if path and os.path.exists(path):
        try:
            import json as _json
            with open(path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            _USED_IMAGE_IDS = set(data.get("ids", []))
        except Exception:
            pass


def _save_used_ids():
    if not _USED_IDS_FILE:
        return
    try:
        import json as _json
        os.makedirs(os.path.dirname(_USED_IDS_FILE), exist_ok=True)
        with open(_USED_IDS_FILE, "w", encoding="utf-8") as f:
            _json.dump({"ids": sorted(list(_USED_IMAGE_IDS))}, f)
    except Exception:
        pass


# ── AI 기반 Pixabay 검색어 추출 (gpt-4o-mini, 하이브리드 1순위) ──
_AI_API_KEY: str = ""
_AI_QUERY_CACHE_FILE: str = ""
_AI_QUERY_CACHE: dict = {}
_AI_CACHE_LOCK = _threading.Lock()

# [네이버 SEO 전략 기획자] 설계 — 정밀 타격용 시스템 프롬프트
_PIXABAY_EXTRACT_SYSTEM = (
    "너는 글로벌 이미지 사이트인 픽사베이(Pixabay)의 전용 영문 검색어 추출기야.\n"
    "입력된 한국어 키워드에서 [앞뒤 지역명(시/군/구/동/역명), 상권 명칭, 고유명사]를 완벽하게 감지하여 삭제해라.\n"
    "그다음, 남은 순수 '업종, 공간, 핵심 개념'을 분석하여 픽사베이에 검색했을 때 고화질 실사 사진이 "
    "가장 잘 나올 만한 최적의 영문 단어 3개를 추상화/대체하여 콤마(,)로만 구분해서 출력해라.\n"
    "(설명이나 서론 없이 단어만 출력할 것)\n"
    "- 입력: '부산개인회생' -> 출력: 'lawyer, court, document'\n"
    "- 입력: '역삼동 헬스장' -> 출력: 'gym, fitness, workout'\n"
    "- 입력: '철원 율무밭' -> 출력: 'farm, grain field, agriculture'"
)


def configure_ai_extractor(api_key: str, cache_file: str = ""):
    """OpenAI 키를 주입하면 search_images가 gpt-4o-mini로 검색어를 자동 추출(1순위).
    cache_file 지정 시 키워드→검색어 결과를 영속 캐시(비용·속도 최적화).
    키가 없거나 API 실패/타임아웃 시에는 BIZ_TO_EN 하드코딩 테이블로 자동 폴백."""
    global _AI_API_KEY, _AI_QUERY_CACHE_FILE, _AI_QUERY_CACHE
    _AI_API_KEY = (api_key or "").strip()
    if cache_file:
        _AI_QUERY_CACHE_FILE = cache_file
        try:
            import json as _json
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    _AI_QUERY_CACHE = _json.load(f)
        except Exception:
            _AI_QUERY_CACHE = {}


def _save_ai_cache():
    if not _AI_QUERY_CACHE_FILE:
        return
    try:
        import json as _json
        os.makedirs(os.path.dirname(_AI_QUERY_CACHE_FILE), exist_ok=True)
        with open(_AI_QUERY_CACHE_FILE, "w", encoding="utf-8") as f:
            _json.dump(_AI_QUERY_CACHE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def extract_pixabay_queries(keyword: str, api_key: str = "") -> list:
    """gpt-4o-mini로 한국어 키워드 → 픽사베이 영문 검색어(최대 5개) 추출.
    지역명/고유명사 제거 + 시각적 개념 추상화는 시스템 프롬프트가 담당.
    실패/키없음 시 빈 리스트 반환 → 호출부에서 하드코딩 테이블로 폴백."""
    kw = (keyword or "").strip()
    key = (api_key or _AI_API_KEY or "").strip()
    if not kw or not key:
        return []
    cached = _AI_QUERY_CACHE.get(kw)
    if cached:
        return list(cached)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, timeout=15.0)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _PIXABAY_EXTRACT_SYSTEM},
                {"role": "user", "content": kw},
            ],
            max_tokens=30,
            temperature=0.3,
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception:
        return []
    raw = raw.splitlines()[0] if raw else ""
    queries = []
    for p in raw.split(","):
        w = p.strip().strip("'\"`.").lower()
        # 영문(아스키)만 채택 — 한글/설명이 섞이면 버림
        if w and all(ord(c) < 128 for c in w) and any(c.isalpha() for c in w):
            queries.append(w)
    queries = queries[:5]
    if queries:
        with _AI_CACHE_LOCK:
            _AI_QUERY_CACHE[kw] = queries
            _save_ai_cache()
    return queries


def _tokenize_biz(keyword: str) -> list:
    """검색어/카테고리 풀스트링을 의미 토큰으로 분해.
    예: '음식점 > 한식 > 칼국수' → ['음식점','한식','칼국수']
        '강남구 치과' → ['강남구','치과']"""
    k = (keyword or "").strip()
    if not k:
        return []
    for sep in [">", "/", ",", "·", "|"]:
        k = k.replace(sep, " ")
    toks = [t.strip() for t in k.split() if t.strip()]
    return toks


# 광역시·도 + 주요 시(市) 접두(지역명 stem) — '부산개인회생'/'수원개인파산' → 개념만 남김
_METRO_STEMS = [
    # 광역시·특별시·도
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충청", "충북", "충남", "전라", "전북", "전남",
    "경상", "경북", "경남", "제주",
    # 주요 시(글자에 붙는 복합 키워드 대비) — 긴 이름 우선 정렬은 _strip_region에서 처리
    "수원", "성남", "용인", "고양", "안산", "안양", "남양주", "화성",
    "평택", "의정부", "시흥", "파주", "김포", "광명", "군포", "하남",
    "창원", "김해", "양산", "거제", "진주", "청주", "천안", "전주",
    "포항", "구미", "경주", "원주", "춘천", "강릉", "목포", "여수",
    "순천", "익산", "군산", "아산", "당진", "제천", "충주", "공주",
]
# 행정구역 단독 토큰 (시/도/군/구/읍/면/동/리) — '역삼동', '강남구' 등
_ADMIN_TOKEN_RE = re.compile(
    r"^[가-힣]{1,5}(특별자치시|특별자치도|특별시|광역시|시|도|군|구|읍|면|동|리)$"
)


def _strip_region(keyword: str) -> str:
    """키워드에서 지역명(광역시·도 접두 + 행정구역 토큰)을 제거하고 순수 개념/업종만 반환.
    예: '부산개인회생' → '개인회생', '역삼동 헬스장' → '헬스장'.
    BIZ_TO_EN에 이미 등록된 업종 토큰은 절대 제거하지 않음(오제거 방지)."""
    out = []
    for tok in _tokenize_biz(keyword):
        if tok in BIZ_TO_EN:            # 등록된 업종은 그대로 보존
            out.append(tok)
            continue
        if _ADMIN_TOKEN_RE.match(tok):  # 순수 행정구역 토큰은 통째 제거
            continue
        # 지역 접두 제거 (긴 지명 우선, 제거 후 남는 글자가 있을 때만)
        for stem in sorted(_METRO_STEMS, key=len, reverse=True):
            if tok.startswith(stem) and len(tok) > len(stem):
                tok = tok[len(stem):]
                break
        out.append(tok)
    return " ".join(out).strip()


def _get_en_queries(keyword: str) -> list:
    """한국어 키워드/카테고리 → 영어 검색어 리스트
    매핑 실패 시 빈 리스트 반환 (호출부에서 번역 폴백/스킵 처리).
    긴 키 우선 매칭(스터디카페 > 카페), 마지막 토큰 우선(가장 구체적)."""
    k = (keyword or "").strip()
    if not k:
        return []
    kl = k.lower()
    # 1) 풀스트링에서 긴 키부터 부분 매칭
    for ko in sorted(BIZ_TO_EN.keys(), key=len, reverse=True):
        if ko in kl:
            v = BIZ_TO_EN[ko]
            return v if isinstance(v, list) else [v]
    # 2) 토큰화 후 마지막 토큰(가장 구체적인 업종)부터 매칭
    toks = _tokenize_biz(k)
    for tok in reversed(toks):
        tl = tok.lower()
        for ko in sorted(BIZ_TO_EN.keys(), key=len, reverse=True):
            if ko in tl:
                v = BIZ_TO_EN[ko]
                return v if isinstance(v, list) else [v]
    # 2.5) 지역명 제거 후 재매핑 (예: '부산개인회생' → '개인회생')
    cleaned = _strip_region(k)
    if cleaned and cleaned != k:
        cl = cleaned.lower()
        for ko in sorted(BIZ_TO_EN.keys(), key=len, reverse=True):
            if ko in cl:
                v = BIZ_TO_EN[ko]
                return v if isinstance(v, list) else [v]
    # 3) 영문 입력은 그대로 (사용자 오버라이드 케이스)
    if not any(0xAC00 <= ord(c) <= 0xD7A3 for c in k):
        return [k]
    # 4) 매핑 실패 → 빈 리스트 (호출부의 translator로 폴백)
    return []


def _fetch_hits(api_key: str, query: str, page: int = 1, per_page: int = 80) -> list:
    params = {
        "key": api_key,
        "q": query,
        "image_type": "photo",
        "per_page": per_page,
        "lang": "en",
        "safesearch": "true",
        "orientation": "horizontal",
        "page": page,
    }
    try:
        resp = requests.get(PIXABAY_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("hits", [])
    except Exception:
        return []


# 업종별 태그 화이트리스트 — 이 태그가 반드시 포함되어야만 채택
BIZ_TAG_FILTER = {
    # 운동
    "헬스장": ["fitness", "gym", "dumbbell", "workout", "weight"],
    "헬스클럽": ["fitness", "gym", "dumbbell", "workout", "weight"],
    "피트니스": ["fitness", "gym", "dumbbell", "workout", "weight"],
    "피트니스센터": ["fitness", "gym", "dumbbell", "workout", "weight"],
    "요가": ["yoga", "meditation", "pose", "mat"],
    "필라테스": ["pilates", "reformer"],
    "골프장": ["golf", "green", "course", "club"],
    "골프연습장": ["golf", "driving", "range", "practice"],
    "스크린골프": ["golf", "simulator", "indoor"],
    # 요양/의료
    "요양원": ["nursing", "elderly", "senior", "retirement", "assisted", "old age", "grandparent"],
    "요양센터": ["nursing", "elderly", "senior", "retirement", "grandparent"],
    "요양병원": ["hospital", "medical", "rehabilitation", "senior", "elderly", "nursing"],
    "치과": ["dental", "dentist", "teeth", "tooth", "clinic"],
    "병원": ["hospital", "clinic", "doctor", "medical", "health"],
    "약국": ["pharmacy", "medicine", "drug", "drugstore"],
    "안과": ["eye", "ophthalmology", "vision", "eyeball", "iris"],
    "피부과": ["dermatology", "skin", "skincare", "skin treatment"],
    "성형외과": ["surgery", "cosmetic", "cosmetic surgery", "plastic surgery"],
    "통증의학과": ["pain", "rehabilitation", "physical therapy", "therapy"],
    "동물병원": ["veterinary", "vet", "animal", "dog", "cat", "pet"],
    # F&B
    "카페": ["cafe", "coffee"],
    "음식점": ["restaurant", "food", "dining", "meal", "plate"],
    "식당": ["restaurant", "dining", "food", "meal"],
    "한식": ["korean", "kimchi", "bulgogi", "bibimbap", "cuisine"],
    "일식": ["sushi", "ramen", "japanese", "sashimi"],
    "중식": ["chinese", "dumpling", "noodles", "wok"],
    "양식": ["steak", "pasta", "pizza", "western"],
    "베이커리": ["bakery", "bread", "pastry"],
    "빵집": ["bakery", "bread", "pastry"],
    "술집": ["pub", "bar", "cocktail", "beer", "drink"],
    "호프": ["beer", "pub", "bar", "drink"],
    "맛집": ["restaurant", "food", "dining", "meal"],
    # 뷰티
    "미용실": ["hair", "salon", "barber", "hairdresser", "hairstyle"],
    "네일": ["nail", "manicure", "pedicure"],
    "네일샵": ["nail", "manicure", "pedicure"],
    "왁싱샵": ["waxing", "hair removal", "depilation", "wax strip"],
    "왁싱": ["waxing", "hair removal", "depilation", "wax strip"],
    "메이크업": ["makeup", "beauty", "cosmetics", "cosmetic"],
    # 교육
    "학원": ["classroom", "student", "education", "study", "book"],
    "스터디카페": ["study", "library", "desk", "cafe", "student"],
    # 법률/회계
    "변호사": ["law", "legal", "court", "justice", "lawyer", "attorney", "gavel"],
    "법률사무소": ["law", "legal", "court", "justice", "lawyer", "attorney", "gavel"],
    "법무법인": ["law", "legal", "court", "justice", "lawyer", "attorney", "gavel"],
    "법무사": ["law", "legal", "document", "office"],
    "회계": ["accounting", "finance", "calculator", "tax"],
    "세무사": ["accounting", "tax", "calculator", "finance"],
    # 스튜디오
    "스튜디오": ["studio", "camera", "photo", "photography"],
    "사진관": ["studio", "portrait", "camera", "photo"],
    # 숙박/공간
    "풀빌라": ["villa", "pool", "luxury", "resort"],
    "펜션": ["cabin", "cottage", "countryside", "wooden", "lodging"],
    "캠핑장": ["camping", "tent", "glamping", "outdoor"],
    "공유오피스": ["office", "coworking", "desk", "workspace", "work"],
    "고시원": ["room", "interior", "bedroom", "single room", "dormitory"],
    "원룸텔": ["studio", "apartment", "room"],
    "파티룸": ["party", "event", "rental", "room"],
    # 유통
    "마트": ["supermarket", "grocery", "shopping", "market"],
    "편의점": ["convenience", "store", "shop", "retail"],
    "노래방": ["karaoke", "singing", "microphone"],
    "pc방": ["gaming", "gamer", "esport"],
    "피시방": ["gaming", "gamer", "esport"],
    "세탁소": ["laundry", "washing", "laundromat", "dry cleaning"],
    "부동산": ["real estate", "house", "apartment", "property"],
    # 자동차
    "카센터": ["auto", "repair", "mechanic", "garage", "car"],
    "자동차정비소": ["auto", "repair", "mechanic", "garage", "car"],
    "타이어": ["tire", "tyre", "wheel", "car"],
    "손세차": ["car wash", "wash", "car", "detailing"],
    "디테일링": ["detailing", "polish", "car", "auto"],
    "중고차": ["car", "dealership", "showroom", "vehicle"],
    "렌터카": ["rental", "car", "rent", "vehicle", "automobile"],
    "렌트카": ["rental", "car", "rent", "vehicle", "automobile"],
    # 생활/설비
    "누수탐지": ["plumbing", "pipe", "leak", "water", "repair"],
    "하수구": ["plumbing", "drain", "pipe", "repair"],
    "인테리어": ["interior", "design", "home", "decor", "room"],
    "가전제품": ["appliance", "electronics", "home", "device"],
    "안마의자": ["massage", "chair", "recliner", "relax"],
    # 청소
    "가구청소": ["home cleaning", "housekeeping", "cleaning service", "furniture cleaning"],
    "쇼파청소": ["sofa", "cleaning", "upholstery", "couch"],
    "침구류청소": ["mattress", "bedding", "cleaning", "bed"],
    "에어컨청소": ["air conditioner", "air filter", "hvac", "cleaning"],
    # 이사/물류
    "포장이사": ["moving", "movers", "box", "relocation"],
    "이사": ["moving", "movers", "relocation", "house move"],
    "용달": ["delivery", "truck", "moving", "van"],
    # 반려동물
    "반려동물": ["pet", "dog", "cat", "animal"],
    "강아지": ["dog", "puppy", "canine", "pet"],
    "고양이": ["cat", "kitten", "feline", "pet"],
    # 웨딩
    "웨딩홀": ["wedding", "ballroom", "ceremony", "bridal"],
    "예식장": ["wedding", "ceremony", "marriage", "bridal"],
    "웨딩드레스": ["wedding", "dress", "bridal", "gown"],
    # 의료 추가
    "한의원": ["acupuncture", "oriental", "traditional medicine", "herbal"],
    "정형외과": ["orthopedic", "bone", "joint", "rehabilitation", "spine"],
    "내과": ["internal medicine", "physician", "doctor", "medical", "clinic"],
    "이비인후과": ["ear", "nose", "throat", "ent", "otolaryngology"],
    "산부인과": ["maternity", "gynecology", "obstetrics", "prenatal", "pregnant"],
    "비뇨의학과": ["urology", "urologist", "kidney", "bladder"],
    "재활의학과": ["rehabilitation", "therapy", "physical therapy", "physiotherapy"],
    "라식라섹": ["lasik", "eye surgery", "vision correction", "ophthalmology", "eye clinic"],
    "임플란트": ["implant", "dental", "dentist", "tooth"],
    "치아교정": ["braces", "orthodontics", "dental", "teeth alignment"],
    "건강검진": ["checkup", "medical examination", "health screening", "doctor"],
    # 뷰티 추가
    "피부관리실": ["facial", "skincare", "skin treatment", "beauty salon"],
    "속눈썹연장": ["eyelash", "lash extension", "false eyelashes", "lash"],
    "눈썹문신": ["eyebrow", "microblading", "eyebrow tattoo", "permanent makeup"],
    "반영구화장": ["eyebrow", "makeup", "lip makeup", "eyeliner", "brow"],
    "두피케어": ["scalp", "hair treatment", "hair health", "scalp care"],
    "탈모클리닉": ["hair loss", "alopecia", "scalp", "hair regrowth", "hair treatment"],
    "태닝샵": ["tanning", "sunbed", "tan", "suntan", "spray tan"],
    # 운동 추가
    "퍼스널트레이닝": ["personal training", "trainer", "fitness", "gym"],
    "pt샵": ["personal training", "trainer", "fitness studio", "workout"],
    "수영장": ["swimming pool", "swim", "pool", "swimmer"],
    "태권도": ["taekwondo", "martial arts", "kick", "karate"],
    "댄스학원": ["dance", "dancing", "dancer", "dance studio", "choreography"],
    "클라이밍": ["climbing", "bouldering", "rock climbing", "wall climbing"],
    "복싱": ["boxing", "punching bag", "boxing ring", "boxer"],
    "배드민턴": ["badminton", "shuttlecock", "racket", "court"],
    "테니스": ["tennis", "tennis court", "racket", "ball"],
    # 교육 추가
    "영어학원": ["english", "classroom", "language", "education", "student"],
    "수학학원": ["math", "mathematics", "classroom", "study", "education"],
    "피아노학원": ["piano", "piano lesson", "keyboard", "music lesson"],
    "미술학원": ["art", "painting", "drawing", "artwork", "art class"],
    "코딩학원": ["coding", "programming", "computer", "education", "code"],
    "독서실": ["study", "reading", "desk", "quiet", "library"],
    # 음식 추가
    "치킨": ["fried chicken", "chicken", "crispy", "drumstick"],
    "피자": ["pizza", "pizza slice", "italian"],
    "삼겹살": ["pork belly", "bbq", "grilled", "korean bbq"],
    "고깃집": ["bbq", "grilled meat", "korean bbq", "meat"],
    "해산물": ["seafood", "fish", "shrimp", "lobster", "crab"],
    "횟집": ["sashimi", "raw fish", "fish slice", "seafood"],
    "냉면": ["noodles", "cold noodles", "korean", "noodle"],
    "아이스크림": ["ice cream", "gelato", "sorbet", "soft serve"],
    "버블티": ["bubble tea", "boba", "milk tea", "tapioca"],
    "디저트카페": ["dessert", "cake", "pastry", "sweet"],
    "와인바": ["wine", "wine glass", "wine bottle", "bar"],
    "브런치카페": ["brunch", "cafe", "breakfast", "food"],
    # 숙박 추가
    "호텔": ["hotel", "lobby", "hotel room", "luxury"],
    "모텔": ["motel", "hotel room", "inn", "room"],
    "게스트하우스": ["guesthouse", "hostel", "backpacker", "room"],
    # 육아 추가
    "키즈카페": ["kids", "children", "playground", "child", "play area"],
    "산후조리원": ["maternity", "newborn", "baby care", "postnatal"],
    "어린이집": ["daycare", "children", "kindergarten", "classroom"],
    # 반려동물 추가
    "애견호텔": ["dog boarding", "kennel", "pet boarding", "dog kennel"],
    "애견미용": ["dog grooming", "pet grooming", "dog haircut", "grooming"],
    "고양이카페": ["cat", "cafe", "kitten", "cat cafe"],
    # 체험/레저 추가
    "방탈출": ["door", "lock", "key", "room door", "escape"],
    "볼링장": ["bowling", "bowling alley", "bowling lane", "bowling pins"],
    "당구장": ["billiards", "pool table", "snooker", "cue"],
    "보드게임카페": ["board game", "game", "table game", "cards"],
    # 생활서비스 추가
    "꽃집": ["flower", "florist", "bouquet", "floral"],
    "플라워샵": ["flower", "florist", "arrangement", "bouquet"],
    "공인중개사": ["real estate", "realtor", "property", "house"],
    "방역": ["pest control", "exterminator", "fumigation", "insecticide"],
    "도배": ["wallpaper", "wall decoration", "interior wall", "home renovation"],
    "세차장": ["car wash", "car", "wash", "clean car"],
    "무인카페": ["cafe", "coffee", "kiosk", "self service"],
}

# 업종별 제외 태그 — 이 태그가 들어있으면 무조건 거르기
_COMMON_EXCLUDE = ["animal", "wildlife", "zoo", "nature", "landscape", "outdoor", "flower", "plant",
                   "food", "meal", "dish", "recipe", "restaurant",
                   "fashion", "runway", "model", "portrait", "selfie",
                   "toddler", "newborn", "baby", "child", "kid", "children"]

BIZ_TAG_EXCLUDE = {
    # 운동
    "헬스장": ["gymnast", "rhythmic", "dance", "dancer", "ballet", "yoga", "pilates", "cheerlead",
              "child", "kid", "children", "toddler", "baby", "school",
              "soccer", "basketball", "volleyball", "football", "tennis", "swimming",
              "martial", "boxing", "karate", "taekwondo", "judo", "mma",
              "bicycle", "cycling", "bike", "cycle", "cyclist",
              "cosmetic", "cream", "skincare", "lotion", "food", "restaurant"],
    "헬스클럽": ["gymnast", "rhythmic", "dance", "dancer", "ballet", "yoga", "pilates", "cheerlead",
               "child", "kid", "children", "toddler", "baby", "school",
               "soccer", "basketball", "volleyball", "football", "tennis", "swimming",
               "martial", "boxing", "karate", "taekwondo", "judo", "mma",
               "bicycle", "cycling", "bike", "cycle", "cyclist",
               "cosmetic", "cream", "skincare", "lotion", "food", "restaurant"],
    "피트니스": ["gymnast", "rhythmic", "dance", "ballet", "yoga", "pilates", "child", "kid",
               "bicycle", "cycling", "bike", "cycle", "cyclist",
               "cosmetic", "cream", "food", "restaurant"],
    "피트니스센터": ["gymnast", "rhythmic", "dance", "ballet", "yoga", "pilates", "child", "kid",
                  "bicycle", "cycling", "bike", "cycle", "cyclist",
                  "cosmetic", "cream", "food", "restaurant"],
    "요가": ["rhythmic gymnast", "child", "kid", "bicycle", "cycling",
            "cosmetic", "cream", "food", "restaurant"],
    "필라테스": ["rhythmic gymnast", "child", "kid", "bicycle", "cycling", "yoga",
               "food", "restaurant", "cosmetic"],
    "골프장": ["mini golf", "child", "kid", "indoor", "simulator",
             "cosmetic", "food", "fashion"],
    "골프연습장": ["golf course", "outdoor golf", "child", "kid",
               "cosmetic", "food", "fashion"],
    "스크린골프": ["outdoor golf", "golf course", "child", "kid",
               "food", "restaurant"],
    # 요양/의료
    "요양원": ["animal", "wildlife", "zoo", "jungle", "beach", "ocean", "mountain", "forest", "landscape",
              "toddler", "newborn", "baby",
              "cosmetic", "cream", "skincare", "lotion", "moisturizer", "beauty product",
              "toothbrush", "toothpaste", "dental",
              "food", "restaurant", "meal", "recipe",
              "fashion", "model", "portrait", "selfie"],
    "요양센터": ["animal", "wildlife", "zoo", "beach", "ocean", "mountain", "landscape",
               "toddler", "newborn", "baby",
               "cosmetic", "cream", "skincare", "lotion",
               "toothbrush", "toothpaste", "dental",
               "food", "restaurant", "fashion", "model", "portrait"],
    "요양병원": ["animal", "wildlife", "zoo", "beach", "ocean", "mountain", "landscape",
               "toddler", "newborn", "baby",
               "cosmetic", "cream", "skincare", "lotion",
               "toothbrush", "toothpaste",
               "food", "restaurant", "fashion", "model"],
    "치과": ["animal", "wildlife", "food", "restaurant", "fashion", "cosmetic",
            "toddler", "baby", "landscape", "flower", "plant",
            "shark", "jewellery", "jewelry", "chain", "accessory", "accessories",
            "portrait", "makeup", "selfie",
            "dinosaur", "dino", "prehistoric", "fossil", "reptile", "crocodile"],
    "병원": ["animal", "wildlife", "food", "restaurant", "fashion", "cosmetic", "beauty",
            "landscape", "flower", "plant", "toddler", "baby"],
    "약국": ["animal", "wildlife", "food", "restaurant", "fashion", "cosmetic", "beauty",
            "landscape", "flower", "plant"],
    "안과": ["makeup", "eyebrow", "mascara", "eyeliner", "eyeshadow", "cosmetic", "beauty",
            "animal", "wildlife", "food", "restaurant", "fashion", "landscape",
            "insect", "fly", "bug", "compound eye", "macro", "entomology", "invertebrate"],
    "피부과": ["animal", "wildlife", "food", "restaurant", "fashion", "landscape", "flower",
             "toddler", "baby", "cosmetic product", "cream jar", "lotion bottle",
             "syringe", "injection", "needle", "drug", "addict", "addiction", "punk"],
    "성형외과": ["animal", "wildlife", "food", "restaurant", "landscape", "flower",
               "toddler", "baby", "recycling", "waste", "garbage", "trash", "bin",
               "manufacturing", "processing", "factory",
               "soap", "bath soap", "soap bar", "lotion", "cream jar", "skincare product"],
    "통증의학과": ["animal", "wildlife", "food", "restaurant", "fashion", "cosmetic",
               "landscape", "flower", "toddler", "baby"],
    "동물병원": ["food", "restaurant", "fashion", "cosmetic", "landscape", "flower",
              "toddler", "baby"],
    # F&B
    "카페": ["animal", "wildlife", "landscape", "flower only", "plant only",
            "fashion", "cosmetic", "fitness", "gym"],
    "음식점": ["animal", "wildlife", "landscape", "flower", "plant",
             "fashion", "cosmetic", "fitness", "gym",
             "computer", "technology", "electronics", "circuit", "motherboard", "hardware", "cpu", "processor", "chip"],
    "식당": ["animal", "wildlife", "landscape", "flower", "plant",
            "fashion", "cosmetic", "fitness", "gym",
            "computer", "technology", "electronics", "circuit", "motherboard", "hardware", "cpu"],
    "한식": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness"],
    "일식": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness"],
    "중식": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness"],
    "양식": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness"],
    "베이커리": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
              "raw wheat", "grain field"],
    "빵집": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
            "raw wheat", "grain field"],
    "술집": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
            "child", "kid", "toddler", "baby"],
    "호프": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
            "child", "kid", "toddler", "baby"],
    "맛집": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
            "raw ingredient only"],
    # 뷰티
    "미용실": ["animal", "wildlife", "landscape", "food", "restaurant", "fitness",
             "nail", "manicure", "waxing", "cosmetic product",
             "ao dai", "traditional dress", "fashion show", "runway", "fashion model"],
    "네일": ["animal", "wildlife", "landscape", "food", "restaurant", "fitness",
            "hair salon", "waxing", "fetish", "erotic", "sexy", "lingerie"],
    "네일샵": ["animal", "wildlife", "landscape", "food", "restaurant", "fitness",
             "hair salon", "waxing", "fetish", "erotic", "sexy", "lingerie"],
    "왁싱샵": ["animal", "wildlife", "landscape", "food", "restaurant", "fitness",
             "nail", "hair salon", "moon", "lunar", "astronomy", "night sky",
             "car", "vehicle", "auto", "automobile", "wax car", "car wash",
             "easter", "egg", "eggs", "tradition", "decorative"],
    "왁싱": ["animal", "wildlife", "landscape", "food", "restaurant", "fitness",
            "nail", "hair salon", "moon", "lunar", "astronomy", "night sky", "moonlight",
            "car", "vehicle", "auto", "automobile", "wax car", "car wash",
            "easter", "egg", "eggs", "tradition", "decorative"],
    "메이크업": ["animal", "wildlife", "landscape", "food", "restaurant", "fitness",
              "nail", "hair salon", "waxing"],
    # 교육
    "학원": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "toddler", "baby"],
    "스터디카페": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby"],
    # 법률/회계
    "변호사": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
             "cosmetic", "fitness", "toddler", "baby",
             "police", "policeman", "policemen", "cop", "enforcement", "officer badge", "badge"],
    "법률사무소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
               "cosmetic", "fitness", "toddler", "baby",
               "police", "policeman", "policemen", "cop", "enforcement", "badge"],
    "법무법인": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby",
              "police", "policeman", "cop", "enforcement", "badge"],
    "법무사": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "toddler", "baby",
            "police", "policeman", "policemen", "cop", "enforcement", "officer badge", "badge"],
    "회계": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
           "cosmetic", "fitness", "toddler", "baby"],
    "세무사": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "toddler", "baby"],
    # 스튜디오
    "스튜디오": ["music studio", "recording studio", "band", "microphone", "music",
              "animal", "wildlife", "landscape", "food", "restaurant", "fitness"],
    "사진관": ["music studio", "recording", "band", "microphone",
             "animal", "wildlife", "landscape", "food", "restaurant", "fitness"],
    # 숙박/공간
    "풀빌라": ["public pool", "swimming competition", "water park", "child", "kid",
             "food", "restaurant", "fashion", "cosmetic", "fitness"],
    "펜션": ["urban", "city", "skyscraper", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "toddler", "baby"],
    "캠핑장": ["urban", "city", "food only", "fashion", "cosmetic", "fitness",
             "toddler", "baby"],
    "고시원": ["luxury", "hotel lobby", "resort", "food", "restaurant", "fashion",
             "cosmetic", "fitness", "baby", "child", "toddler", "newborn",
             "abandoned", "decay", "ruins", "derelict", "grunge",
             "railway", "railroad", "train track", "track"],
    "원룸텔": ["luxury", "hotel lobby", "resort", "food", "restaurant", "fashion",
            "cosmetic", "fitness"],
    "공유오피스": ["home office", "living room", "food", "restaurant", "fashion",
               "cosmetic", "fitness", "toddler", "baby"],
    "파티룸": ["outdoor party", "garden party", "child birthday", "kid party",
             "food only", "fashion", "cosmetic", "fitness"],
    # 유통
    "마트": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
           "toddler", "baby"],
    "편의점": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
            "toddler", "baby"],
    "노래방": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
             "cosmetic", "fitness", "toddler", "baby",
             "fireworks", "neon sign", "festival", "new year", "pyrotechnics", "concert outdoor"],
    "pc방": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "toddler", "baby",
            "cpu", "processor", "chip", "motherboard", "hardware", "circuit", "component",
            "football", "soccer", "boots", "cleats", "chuteira", "futebol",
            "dart", "darts", "pub game", "board game", "chess", "checkerboard",
            "playing cards", "poker", "gambling", "domino", "dominoes", "card game",
            "game bird", "partridge", "quail", "pheasant", "bird", "poultry"],
    "피시방": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
             "cosmetic", "fitness", "toddler", "baby",
             "cpu", "processor", "chip", "motherboard", "hardware", "circuit", "component",
             "football", "soccer", "boots", "cleats", "chuteira", "futebol",
             "dart", "darts", "pub game", "board game", "chess", "checkerboard",
             "playing cards", "poker", "gambling", "domino", "dominoes", "card game",
             "game bird", "partridge", "quail", "pheasant", "bird", "poultry"],
    "세탁소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
             "cosmetic", "fitness", "toddler", "baby"],
    "부동산": ["animal", "wildlife", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "toddler", "baby"],
    # 자동차
    "카센터": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "racing", "formula", "supercar", "toddler", "baby"],
    "자동차정비소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
                "cosmetic", "fitness", "racing", "formula", "supercar",
                "abandoned", "decay", "ruins", "derelict", "dilapidated", "broken building"],
    "타이어": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "bicycle tire", "cycle", "motorcycle only",
            "motorbike", "motorcycle", "scooter", "moped", "bicycle", "bike wheel"],
    "손세차": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "racing", "toddler", "baby"],
    "디테일링": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "racing", "toddler", "baby"],
    "중고차": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "racing", "formula", "supercar", "toddler", "baby"],
    "렌터카": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "racing", "formula", "toddler", "baby",
            "photo studio", "photo background", "santorini", "studio backdrop"],
    "렌트카": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "racing", "formula", "toddler", "baby",
            "photo studio", "photo background", "studio backdrop"],
    # 생활/설비
    "누수탐지": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby"],
    "하수구": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "toddler", "baby"],
    "인테리어": ["animal", "wildlife", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "exterior", "facade", "building exterior", "toddler", "baby"],
    "가전제품": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby"],
    "안마의자": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby"],
    # 청소
    "가구청소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby",
              "car wash", "garage", "car", "vehicle", "automobile", "pressure wash"],
    "쇼파청소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby"],
    "침구류청소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
               "cosmetic", "fitness", "toddler", "baby"],
    "에어컨청소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
               "cosmetic", "fitness", "toddler", "baby",
               "airplane", "aircraft", "plane", "aviation", "aviator", "airliner", "fuselage",
               "laundry", "clothespins", "essential oils",
               "virus", "corona", "coronavirus", "covid", "pathogen", "epidemic"],
    # 이사/물류
    "포장이사": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby"],
    "이사": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
           "cosmetic", "fitness", "toddler", "baby", "child", "kid",
           "nature photo", "beach", "iceland", "wallpaper", "scenic", "playing", "leisure",
           "bicycle", "cycling", "cycle", "bike"],
    "용달": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
           "cosmetic", "fitness", "toddler", "baby", "racing"],
    # 반려동물
    "반려동물": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape"],
    "강아지": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape", "cat", "kitten"],
    "고양이": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape", "dog", "puppy"],
    # 웨딩
    "웨딩홀": ["animal", "wildlife", "landscape", "food only", "fashion", "cosmetic", "fitness",
             "toddler", "baby", "outdoor wedding", "conference", "forum", "auditorium",
             "meeting", "lecture", "seminar", "latin dance", "salsa", "tango", "dance performance",
             "ballroom dance", "dancing competition"],
    "예식장": ["animal", "wildlife", "landscape", "food only", "cosmetic", "fitness",
            "toddler", "baby", "outdoor wedding", "conference", "forum", "auditorium",
            "meeting", "lecture", "seminar"],
    "웨딩드레스": ["animal", "wildlife", "landscape", "food", "cosmetic", "fitness",
               "toddler", "baby", "tuxedo only", "suit only"],
    # 의료 추가
    "한의원": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
             "toddler", "baby"],
    "정형외과": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby", "animal", "wildlife"],
    "내과": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
           "toddler", "baby", "animal", "wildlife",
           "dentist", "dental", "teeth", "oral hygiene", "tooth"],
    "이비인후과": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
               "toddler", "baby", "animal", "wildlife",
               "cutlery", "kitchen", "cooking utensils",
               "dentist", "dental", "oral", "teeth", "tooth"],
    "산부인과": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "animal", "wildlife"],
    "비뇨의학과": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
               "toddler", "baby", "animal", "wildlife",
               "helicopter", "rescue", "ambulance helicopter", "aviation", "aircraft"],
    "재활의학과": ["food", "restaurant", "fashion", "cosmetic", "landscape",
               "toddler", "baby", "animal", "wildlife",
               "syringe", "injection", "needle", "drug addict", "addiction", "drug"],
    "라식라섹": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby", "animal", "wildlife", "insect", "fly", "macro",
              "cnc", "wood engraving", "laser engraver", "laser cutting", "machine tool", "industrial laser",
              "manufacturing", "factory", "laser machine"],
    "임플란트": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby", "animal", "wildlife",
              "shark", "dinosaur", "dino", "crocodile", "jewellery"],
    "치아교정": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby", "animal", "wildlife",
              "shark", "dinosaur", "dino", "jewellery"],
    "건강검진": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby", "animal", "wildlife"],
    # 뷰티 추가
    "피부관리실": ["food", "restaurant", "fitness", "landscape", "toddler", "baby",
               "animal", "wildlife", "nail", "hair only", "waxing"],
    "속눈썹연장": ["food", "restaurant", "fashion", "fitness", "landscape", "toddler", "baby",
               "animal", "wildlife"],
    "눈썹문신": ["food", "restaurant", "fashion", "fitness", "landscape", "toddler", "baby",
              "animal", "wildlife", "nail"],
    "반영구화장": ["food", "restaurant", "fashion", "fitness", "landscape", "toddler", "baby",
               "animal", "wildlife"],
    "두피케어": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby", "animal", "wildlife"],
    "탈모클리닉": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
               "toddler", "baby", "animal", "wildlife",
               "flower", "wildflower", "garden", "floral", "plant", "bloom", "blossom",
               "grapefruit", "coconut", "citrus", "fruit", "shampoo product", "bottle flatlay"],
    "태닝샵": ["food", "restaurant", "cosmetic", "fitness", "landscape",
             "toddler", "baby", "animal", "wildlife",
             "buddha", "bronze statue", "temple", "monument", "religious", "hongkong", "asia landmark",
             "morocco", "leather tannery", "leather tanning", "tannery", "hide", "rawhide"],
    # 운동 추가
    "퍼스널트레이닝": ["food", "restaurant", "fashion", "cosmetic", "landscape",
                 "toddler", "baby", "animal", "wildlife",
                 "yoga", "pilates", "dance", "swimming"],
    "pt샵": ["food", "restaurant", "fashion", "cosmetic", "landscape",
           "toddler", "baby", "animal", "wildlife"],
    "수영장": ["food", "restaurant", "fashion", "cosmetic", "landscape",
             "toddler", "baby", "animal", "wildlife"],
    "태권도": ["food", "restaurant", "fashion", "cosmetic", "landscape",
             "toddler", "baby", "animal", "wildlife",
             "dance", "yoga", "pilates"],
    "댄스학원": ["food", "restaurant", "fashion", "cosmetic", "landscape",
              "toddler", "baby", "animal", "wildlife",
              "library", "bookshelf", "books", "reading", "study hall"],
    "클라이밍": ["food", "restaurant", "fashion", "cosmetic", "landscape",
              "toddler", "baby", "animal", "wildlife"],
    "복싱": ["food", "restaurant", "fashion", "cosmetic", "landscape",
           "toddler", "baby", "animal", "wildlife",
           "yoga", "pilates", "dance", "swimming"],
    "배드민턴": ["food", "restaurant", "fashion", "cosmetic", "landscape",
              "toddler", "baby", "animal", "wildlife"],
    "테니스": ["food", "restaurant", "fashion", "cosmetic", "landscape",
             "toddler", "baby", "animal", "wildlife"],
    # 교육 추가
    "영어학원": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby", "animal", "wildlife"],
    "수학학원": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby", "animal", "wildlife"],
    "피아노학원": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
               "toddler", "baby", "animal", "wildlife",
               "concert", "performance", "orchestra", "stage",
               "university", "college campus", "textbook", "study books"],
    "미술학원": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby", "animal", "wildlife",
              "music studio", "recording studio", "audio equipment", "sound mixer",
              "microphone", "mixing board", "music production"],
    "코딩학원": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby", "animal", "wildlife",
              "cpu", "processor", "chip", "motherboard", "hardware", "circuit"],
    "독서실": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
             "toddler", "baby", "animal", "wildlife"],
    # 음식 추가
    "치킨": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
           "live chicken", "farm chicken", "rooster", "hen"],
    "피자": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness"],
    "삼겹살": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
             "live pig", "farm pig", "piglet"],
    "고깃집": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
             "live animal", "farm animal"],
    "해산물": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
             "live fish", "aquarium", "underwater"],
    "횟집": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
           "live fish", "aquarium", "underwater swimming"],
    "냉면": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness"],
    "아이스크림": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
               "toddler", "baby"],
    "버블티": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
            "herbal", "herbal tea", "medicinal herbs", "herbs medicine", "oriental medicine tea", "aroma"],
    "디저트카페": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness"],
    "와인바": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
            "toddler", "baby", "child", "kid", "vineyard only", "wine making"],
    "브런치카페": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness"],
    # 숙박 추가
    "호텔": ["animal", "wildlife", "landscape", "food", "fashion", "cosmetic", "fitness",
           "toddler", "baby"],
    "모텔": ["animal", "wildlife", "landscape", "food", "fashion", "cosmetic", "fitness",
           "toddler", "baby"],
    "게스트하우스": ["animal", "wildlife", "landscape", "food", "fashion", "cosmetic", "fitness",
                "toddler", "baby"],
    # 육아 추가
    "키즈카페": ["animal", "wildlife", "landscape", "food", "fashion", "cosmetic", "fitness",
             "japan", "japanese", "traditional japanese", "outdoor cafe", "adult only"],
    "산후조리원": ["animal", "wildlife", "landscape", "food", "fashion", "cosmetic", "fitness"],
    "어린이집": ["animal", "wildlife", "landscape", "food", "fashion", "cosmetic", "fitness"],
    # 반려동물 추가
    "애견호텔": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby",
              "hotel lobby", "hotel room", "luxury hotel", "armchair", "bedroom suite"],
    "애견미용": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
              "toddler", "baby", "cat", "kitten"],
    "고양이카페": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
               "toddler", "baby", "dog", "puppy",
               "japan", "japanese", "traditional japanese", "outdoor", "garden"],
    # 체험/레저 추가
    "방탈출": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
             "toddler", "baby", "animal", "wildlife",
             "casino", "slot machine", "gambling", "poker chips", "jackpot", "vending machine",
             "outdoor", "nature", "field", "park", "forest"],
    "볼링장": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
             "toddler", "baby", "animal", "wildlife",
             "cricket", "cricket ball", "cricket bat", "baseball", "softball", "rounders"],
    "당구장": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
             "toddler", "baby", "animal", "wildlife",
             "dart", "poker", "playing cards"],
    "보드게임카페": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
                "toddler", "baby", "animal", "wildlife",
                "video game", "console", "gaming pc"],
    # 생활서비스 추가
    "꽃집": ["food", "restaurant", "fashion", "cosmetic", "fitness",
           "toddler", "baby", "animal", "wildlife",
           "field flower", "wildflower", "wedding bouquet only"],
    "플라워샵": ["food", "restaurant", "fashion", "cosmetic", "fitness",
              "toddler", "baby", "animal", "wildlife"],
    "공인중개사": ["food", "restaurant", "fashion", "cosmetic", "fitness",
               "toddler", "baby", "animal", "wildlife"],
    "방역": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
           "toddler", "baby"],
    "도배": ["food", "restaurant", "fashion", "cosmetic", "fitness",
           "toddler", "baby", "animal", "wildlife",
           "desktop background", "nature wallpaper", "hd wallpaper", "computer wallpaper",
           "sunbed", "souvenir", "garden", "beach", "scenic wallpaper"],
    "세차장": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape",
             "toddler", "baby", "animal", "wildlife"],
    "무인카페": ["animal", "wildlife", "landscape", "fashion", "cosmetic", "fitness",
              "toddler", "baby"],
    # 법률/금융/전문직 — 결과 hit 태그에 아래 중 하나는 반드시 포함돼야 채택
    "개인회생": ["law", "lawyer", "legal", "court", "attorney", "justice", "document", "contract", "gavel"],
    "개인파산": ["law", "lawyer", "legal", "court", "attorney", "document", "gavel"],
    "법인회생": ["law", "lawyer", "legal", "court", "business", "document", "gavel"],
    "회생파산": ["law", "lawyer", "legal", "court", "document", "gavel"],
    "파산": ["law", "lawyer", "legal", "court", "document", "gavel"],
    "회생": ["law", "lawyer", "legal", "court", "document", "gavel"],
    "채무조정": ["finance", "debt", "money", "consulting", "document", "calculator", "counseling"],
    "신용회복": ["finance", "debt", "money", "consulting", "document", "calculator"],
    "워크아웃": ["finance", "business", "debt", "document", "meeting"],
    "법률상담": ["law", "lawyer", "legal", "consultation", "office", "document"],
    "노무사": ["law", "labor", "office", "document", "business", "contract"],
    "행정사": ["office", "document", "paperwork", "government", "filing"],
    "손해사정": ["insurance", "document", "claim", "office", "paperwork"],
    "대출": ["finance", "money", "bank", "loan", "document", "calculator"],
}


def _tag_filter_for(keyword: str):
    k = (keyword or "").lower()
    for ko, tags in BIZ_TAG_FILTER.items():
        if ko in k:
            return tags
    return None


def _tag_exclude_for(keyword: str):
    k = (keyword or "").lower()
    for ko, tags in BIZ_TAG_EXCLUDE.items():
        if ko in k:
            return tags
    return None


def search_images(api_key: str, keyword: str, count: int = 5,
                  translator=None, ai_api_key=None, manual_queries=None) -> list[dict]:
    """Pixabay 이미지 검색 — 키워드 관련성 우선.

    translator: 한글 → 영어 콜백 (호출부에서 주입, 예: GPT 번역).
                BIZ_TO_EN 매핑 실패 시 마지막 토큰을 영어로 변환해 사용.
    매핑·번역 모두 실패하면 빈 리스트 반환 (엉뚱한 사진 가져오지 않음)."""
    import random

    # ── Pixabay 검색어 우선순위 체인 (명문화) ──
    # 0순위: 사용자가 UI에 직접 입력한 수동 검색어 → AI/테이블/번역 전부 건너뛰고 그대로 사용
    manual = [q.strip() for q in (manual_queries or []) if q and q.strip()]
    if manual:
        queries = manual
        _override = True
    else:
        _override = False
        # 1순위: AI(gpt-4o-mini) 추출 — 지역/고유명사 제거 + 시각 개념 추상화 (신종 키워드 대응)
        queries = extract_pixabay_queries(keyword, ai_api_key or _AI_API_KEY)
        # 2순위 폴백: 하드코딩 매핑 테이블 (API 장애/타임아웃/키없음 대비 비상용)
        if not queries:
            queries = _get_en_queries(keyword)
        # 3순위 폴백: 단순 번역 콜백
        if not queries and translator:
            # 지역명을 먼저 발라낸 뒤 번역 (예: '부산개인회생'을 통째 번역하면
            # 'Busan...'이 되어 바다 사진이 나오던 버그 차단 — 순수 개념만 번역)
            cleaned_kw = _strip_region(keyword) or (keyword or "")
            toks = _tokenize_biz(cleaned_kw)
            last = toks[-1] if toks else cleaned_kw.strip()
            if last:
                try:
                    en = (translator(last) or "").strip()
                    if en and not any(0xAC00 <= ord(c) <= 0xD7A3 for c in en):
                        queries = [en]
                except Exception:
                    pass
    if not queries:
        # 키워드 관련 영어 검색어를 만들 수 없음 — 엉뚱한 사진을 가져오느니 빈 리스트 반환
        return []

    random.shuffle(queries)
    # 수동 오버라이드 시에는 업종 태그 필터를 적용하지 않음 (사용자 의도를 그대로 존중)
    tag_filter = None if _override else _tag_filter_for(keyword)
    tag_exclude = None if _override else _tag_exclude_for(keyword)

    # ── 후보 풀을 넉넉히 수집 (per_page=200으로 요청 수 최소화) ──
    all_hits = []
    seen_ids_in_pool = set()
    target_pool = max(count * 8, 80)
    for q in queries:
        for page in range(1, 4):
            hits = _fetch_hits(api_key, q, page=page, per_page=200)
            if not hits:
                break
            for h in hits:
                hid = h.get("id")
                if hid and hid not in seen_ids_in_pool:
                    seen_ids_in_pool.add(hid)
                    all_hits.append(h)
            if len(all_hits) >= target_pool:
                break
        if len(all_hits) >= target_pool:
            break

    if not all_hits:
        return []

    def _excluded(h):
        tags = (h.get("tags") or "").lower()
        return bool(tag_exclude and any(t in tags for t in tag_exclude))

    def _matches(h):
        tags = (h.get("tags") or "").lower()
        return (not tag_filter) or any(t in tags for t in tag_filter)

    # ── 우선순위 티어 분류 ──
    #  관련성(필터통과) 강 → 약, 그리고 신선(미사용) → 사용됨 순으로 채운다.
    #  _USED_IMAGE_IDS는 "차단"이 아니라 "신선한 것 우선"용 소프트 신호일 뿐 —
    #  풀이 말라도 절대 0장이 안 나오게 한다(예전 평생-중복금지 버그 제거).
    fresh_strong, used_strong, medium, weak = [], [], [], []
    for h in all_hits:
        hid = h.get("id")
        ex = _excluded(h)
        if _matches(h) and not ex:
            (used_strong if hid in _USED_IMAGE_IDS else fresh_strong).append(h)
        elif not ex:
            medium.append(h)
        else:
            weak.append(h)

    for bucket in (fresh_strong, used_strong, medium, weak):
        random.shuffle(bucket)

    ordered = fresh_strong + used_strong + medium + weak
    selected = ordered[:count]
    # 후보 자체가 count보다 적으면 있는 것을 반복해서라도 무조건 count장 채움
    if selected and len(selected) < count:
        i = 0
        while len(selected) < count:
            selected.append(ordered[i % len(ordered)])
            i += 1

    results = []
    with _USED_IDS_LOCK:
        for hit in selected:
            _USED_IMAGE_IDS.add(hit.get("id"))
            results.append({
                "id": hit.get("id"),
                "url": hit.get("webformatURL", ""),
                "large_url": hit.get("largeImageURL", ""),
                "tags": hit.get("tags", ""),
                "width": hit.get("webformatWidth", 0),
                "height": hit.get("webformatHeight", 0),
            })
        _save_used_ids()
    return results


def add_watermark(img_path: str, text: str) -> None:
    """이미지 우측 하단에 업체명 워터마크 삽입 (PIL)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return
    try:
        img = Image.open(img_path).convert("RGBA")
        w, h = img.size
        font_size = max(18, w // 30)
        font = None
        for font_path in [
            r"C:\Windows\Fonts\malgun.ttf",
            r"C:\Windows\Fonts\gulim.ttc",
            r"C:\Windows\Fonts\arial.ttf",
        ]:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except Exception:
                    continue
        if font is None:
            font = ImageFont.load_default()

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        margin = max(14, w // 60)
        pad = max(8, font_size // 4)
        x = w - tw - margin
        y = h - th - margin
        # 반투명 어두운 배경 박스 — 어떤 사진(밝은/복잡한) 위에서도 업체명이 확실히 보이게
        box = [x - pad, y - pad, x + tw + pad, y + th + pad]
        try:
            draw.rounded_rectangle(box, radius=pad, fill=(0, 0, 0, 140))
        except Exception:
            draw.rectangle(box, fill=(0, 0, 0, 140))
        # 그림자 + 흰색 텍스트 (선명하게)
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 200))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 245))

        result = Image.alpha_composite(img, overlay).convert("RGB")
        result.save(img_path, "JPEG", quality=92)
    except Exception as e:
        print(f"워터마크 실패: {e}")


def _diversify_image(img_path: str, allow_flip: bool = True) -> None:
    """네이버 이미지 중복도 회피용 미세 변형.
    가장자리 랜덤 크롭 + 밝기/채도 미세 조정 (+ 선택적 좌우반전)으로
    원본 픽사베이 이미지를 재사용해도 픽셀/지각해시(pHash)가 달라지게 한다.
    워터마크만으로는 네이버 유사도 검출을 못 피하므로 이 변형을 함께 적용."""
    try:
        from PIL import Image, ImageEnhance
    except ImportError:
        return
    import random
    try:
        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        lx = int(w * random.uniform(0.0, 0.06))
        ty = int(h * random.uniform(0.0, 0.06))
        rx = w - int(w * random.uniform(0.0, 0.06))
        by = h - int(h * random.uniform(0.0, 0.06))
        if rx - lx > w * 0.5 and by - ty > h * 0.5:
            img = img.crop((lx, ty, rx, by)).resize((w, h))
        img = ImageEnhance.Brightness(img).enhance(random.uniform(0.93, 1.07))
        img = ImageEnhance.Color(img).enhance(random.uniform(0.94, 1.06))
        if allow_flip and random.random() < 0.5:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        img.save(img_path, "JPEG", quality=92)
    except Exception:
        pass


def download_images(api_key: str, keyword: str, count: int = 5,
                    watermark_text: str = "", translator=None, ai_api_key=None,
                    manual_queries=None) -> list[str]:
    """이미지를 검색·다운로드하고 파일 경로 리스트 반환. **무조건 count장을 채워 반환**한다
    (다운로드 실패/풀 부족 시 받은 이미지를 복제해서라도 채움 — 0장 절대 금지).
    각 이미지에 중복도 회피용 미세 변형 + 업체명 워터마크를 적용한다.
    우선순위: manual_queries(사용자 직접 입력) > ai_api_key(gpt-4o-mini) > 하드코딩 테이블 > translator."""
    # 다운로드 실패에 대비해 후보를 넉넉히 확보
    images = search_images(api_key, keyword, max(count * 4, count + 5),
                           translator=translator, ai_api_key=ai_api_key,
                           manual_queries=manual_queries)
    if not images:
        return []

    temp_dir = tempfile.mkdtemp(prefix="naver_blog_")
    paths = []
    n = 0
    for img in images:
        if len(paths) >= count:
            break
        n += 1
        file_path = os.path.join(temp_dir, f"image_{n}.jpg")
        ok = False
        for url in (img.get("large_url"), img.get("url")):  # large 실패 시 webformat 재시도
            if not url:
                continue
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                with open(file_path, "wb") as f:
                    f.write(resp.content)
                ok = True
                break
            except Exception as e:
                print(f"이미지 다운로드 재시도 ({n}): {e}")
        if not ok:
            continue
        _diversify_image(file_path)              # 중복도 회피 미세 변형 (워터마크 전)
        if watermark_text:
            add_watermark(file_path, watermark_text)
        paths.append(file_path)

    # 무조건 count장 보장 — 후보 소진/다운로드 실패로 모자라면 복제(+재변형)해서 채움
    if paths and len(paths) < count:
        import shutil as _sh
        i = 0
        while len(paths) < count:
            src = paths[i % len(paths)]
            dst = os.path.join(temp_dir, f"image_dup_{len(paths) + 1}.jpg")
            try:
                _sh.copyfile(src, dst)
                _diversify_image(dst, allow_flip=False)  # 복제본도 살짝 다르게 (워터마크 글자 보존 위해 반전 X)
                paths.append(dst)
            except Exception:
                break
            i += 1

    return paths
