"""Pixabay 이미지 검색 및 다운로드 모듈"""
import os
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
                  translator=None) -> list[dict]:
    """Pixabay 이미지 검색 — 키워드 관련성 우선.

    translator: 한글 → 영어 콜백 (호출부에서 주입, 예: GPT 번역).
                BIZ_TO_EN 매핑 실패 시 마지막 토큰을 영어로 변환해 사용.
    매핑·번역 모두 실패하면 빈 리스트 반환 (엉뚱한 사진 가져오지 않음)."""
    import random

    queries = _get_en_queries(keyword)
    # 매핑 실패 시 번역 콜백으로 영어 검색어 생성
    if not queries and translator:
        toks = _tokenize_biz(keyword)
        last = toks[-1] if toks else keyword.strip()
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
    tag_filter = _tag_filter_for(keyword)
    tag_exclude = _tag_exclude_for(keyword)

    def _hit_matches(h):
        tags = (h.get("tags") or "").lower()
        if tag_exclude and any(t in tags for t in tag_exclude):
            return False
        if not tag_filter:
            return True
        return any(t in tags for t in tag_filter)

    pool = []
    seen_ids_in_pool = set()
    target = count * 4

    # 1차: tag_filter 통과한 결과만 수집 (관련성 우선)
    for q in queries:
        for page in range(1, 4):
            hits = _fetch_hits(api_key, q, page=page)
            if not hits:
                break
            for h in hits:
                hid = h.get("id")
                if hid and hid not in seen_ids_in_pool and hid not in _USED_IMAGE_IDS and _hit_matches(h):
                    seen_ids_in_pool.add(hid)
                    pool.append(h)
            if len(pool) >= target:
                break
        if len(pool) >= target:
            break

    # 2차: 부족하면 _USED_IMAGE_IDS 캐시만 클리어해서 같은 필터로 다시 시도
    # (tag_filter는 절대 풀지 않음 — 풀면 엉뚱한 사진 들어옴)
    if len(pool) < count and _USED_IMAGE_IDS:
        _USED_IMAGE_IDS.clear()
        for q in queries:
            for page in range(1, 4):
                hits = _fetch_hits(api_key, q, page=page)
                if not hits:
                    break
                for h in hits:
                    hid = h.get("id")
                    if hid and hid not in seen_ids_in_pool and _hit_matches(h):
                        seen_ids_in_pool.add(hid)
                        pool.append(h)
                if len(pool) >= target:
                    break
            if len(pool) >= target:
                break

    if not pool:
        return []

    if len(pool) > count:
        pool = random.sample(pool, count)

    results = []
    with _USED_IDS_LOCK:
        for hit in pool[:count]:
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
        margin = 12
        x = w - tw - margin
        y = h - th - margin
        # 그림자
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 160))
        # 흰색 텍스트
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 220))

        result = Image.alpha_composite(img, overlay).convert("RGB")
        result.save(img_path, "JPEG", quality=92)
    except Exception as e:
        print(f"워터마크 실패: {e}")


def download_images(api_key: str, keyword: str, count: int = 5,
                    watermark_text: str = "", translator=None) -> list[str]:
    """이미지를 검색하고 임시 폴더에 다운로드, 파일 경로 리스트 반환.
    translator: BIZ_TO_EN 매핑 실패 시 한글→영어 번역 콜백."""
    images = search_images(api_key, keyword, count, translator=translator)
    if not images:
        return []

    temp_dir = tempfile.mkdtemp(prefix="naver_blog_")
    paths = []

    for i, img in enumerate(images):
        try:
            resp = requests.get(img["large_url"], timeout=30)
            resp.raise_for_status()

            ext = "jpg"
            file_path = os.path.join(temp_dir, f"image_{i+1}.{ext}")
            with open(file_path, "wb") as f:
                f.write(resp.content)
            if watermark_text:
                add_watermark(file_path, watermark_text)
            paths.append(file_path)
        except Exception as e:
            print(f"이미지 다운로드 실패 ({i+1}): {e}")

    return paths
