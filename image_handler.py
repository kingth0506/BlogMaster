"""Pixabay 이미지 검색 및 다운로드 모듈"""
import os
import requests
import tempfile


PIXABAY_API_URL = "https://pixabay.com/api/"

# 한국어 업종 → 영어 Pixabay 검색어 매핑
BIZ_TO_EN = {
    "헬스장": ["fitness", "gym fitness", "fitness workout", "dumbbell fitness"],
    "피트니스": ["fitness", "gym fitness", "fitness workout", "dumbbell fitness"],
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
    "왁싱샵": ["waxing salon", "beauty salon", "skincare"],
    "왁싱": ["waxing", "beauty salon"],
    "메이크업": ["makeup", "beauty makeup", "cosmetics"],
    # 의료
    "안과": ["eye clinic", "ophthalmology", "eye exam"],
    "피부과": ["dermatology clinic", "skin clinic", "skincare clinic"],
    "성형외과": ["plastic surgery clinic", "cosmetic surgery"],
    "통증의학과": ["pain clinic", "rehabilitation clinic", "physical therapy"],
    "동물병원": ["veterinary clinic", "vet hospital", "animal clinic"],
    # 숙박/공간
    "풀빌라": ["pool villa", "luxury villa pool", "private pool resort"],
    "펜션": ["pension cabin", "wooden cabin", "countryside lodging"],
    "캠핑장": ["camping ground", "camping tent", "glamping"],
    "고시원": ["small studio room", "dormitory", "compact room"],
    "원룸텔": ["studio apartment", "compact studio"],
    "공유오피스": ["coworking space", "shared office", "modern office"],
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
    "렌터카": ["car rental", "rental car"],
    "렌트카": ["car rental", "rental car"],
    # 생활/설비
    "누수탐지": ["plumbing repair", "water leak", "pipe repair"],
    "하수구": ["plumbing", "drain pipe", "pipe repair"],
    "인테리어": ["interior design", "home interior", "modern interior"],
    "가전제품": ["home appliance", "electronics store", "appliance showroom"],
    "안마의자": ["massage chair", "recliner chair"],
    # 청소
    "가구청소": ["home cleaning", "cleaning service", "housekeeping"],
    "쇼파청소": ["sofa cleaning", "upholstery cleaning", "home cleaning"],
    "침구류청소": ["mattress cleaning", "bedding cleaning"],
    "에어컨청소": ["air conditioner cleaning", "ac cleaning", "air filter"],
    # 이사/물류
    "포장이사": ["moving service", "moving boxes", "movers"],
    "이사": ["moving boxes", "movers", "home moving"],
    "용달": ["delivery truck", "moving truck"],
    # 반려동물
    "반려동물": ["pet shop", "pet care", "dog cat"],
    "강아지": ["dog grooming", "puppy care", "dog park"],
    "고양이": ["cat cafe", "cat care", "cute cat"],
    # 웨딩
    "웨딩홀": ["wedding hall", "wedding venue", "ballroom"],
    "예식장": ["wedding hall", "wedding ceremony"],
    "웨딩드레스": ["wedding dress", "bridal dress", "wedding gown"],
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
    "피트니스": ["fitness", "gym", "dumbbell", "workout", "weight"],
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
    "안과": ["eye", "ophthalmology", "vision", "clinic"],
    "피부과": ["dermatology", "skin", "skincare", "clinic"],
    "성형외과": ["plastic", "surgery", "cosmetic", "clinic"],
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
    "왁싱샵": ["waxing", "beauty", "salon", "skin"],
    "왁싱": ["waxing", "beauty", "skin"],
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
    "고시원": ["dormitory", "studio", "room", "compact"],
    "원룸텔": ["studio", "apartment", "room"],
    "공유오피스": ["coworking", "office", "shared", "workspace"],
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
    "렌터카": ["rental", "car", "rent", "vehicle"],
    "렌트카": ["rental", "car", "rent", "vehicle"],
    # 생활/설비
    "누수탐지": ["plumbing", "pipe", "leak", "water", "repair"],
    "하수구": ["plumbing", "drain", "pipe", "repair"],
    "인테리어": ["interior", "design", "home", "decor", "room"],
    "가전제품": ["appliance", "electronics", "home", "device"],
    "안마의자": ["massage", "chair", "recliner", "relax"],
    # 청소
    "가구청소": ["cleaning", "housekeeping", "clean", "service"],
    "쇼파청소": ["sofa", "cleaning", "upholstery", "couch"],
    "침구류청소": ["mattress", "bedding", "cleaning", "bed"],
    "에어컨청소": ["air conditioner", "ac", "air filter", "hvac"],
    # 이사/물류
    "포장이사": ["moving", "movers", "box", "relocation"],
    "이사": ["moving", "movers", "box", "relocation"],
    "용달": ["delivery", "truck", "moving", "van"],
    # 반려동물
    "반려동물": ["pet", "dog", "cat", "animal"],
    "강아지": ["dog", "puppy", "canine", "pet"],
    "고양이": ["cat", "kitten", "feline", "pet"],
    # 웨딩
    "웨딩홀": ["wedding", "venue", "ballroom", "ceremony"],
    "예식장": ["wedding", "ceremony", "hall", "venue"],
    "웨딩드레스": ["wedding", "dress", "bridal", "gown"],
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
    "피트니스": ["gymnast", "rhythmic", "dance", "ballet", "yoga", "pilates", "child", "kid",
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
            "toddler", "baby", "landscape", "flower", "plant"],
    "병원": ["animal", "wildlife", "food", "restaurant", "fashion", "cosmetic", "beauty",
            "landscape", "flower", "plant", "toddler", "baby"],
    "약국": ["animal", "wildlife", "food", "restaurant", "fashion", "cosmetic", "beauty",
            "landscape", "flower", "plant"],
    "안과": ["makeup", "eyebrow", "mascara", "eyeliner", "eyeshadow", "cosmetic", "beauty",
            "animal", "wildlife", "food", "restaurant", "fashion", "landscape"],
    "피부과": ["animal", "wildlife", "food", "restaurant", "fashion", "landscape", "flower",
             "toddler", "baby", "cosmetic product", "cream jar", "lotion bottle"],
    "성형외과": ["animal", "wildlife", "food", "restaurant", "landscape", "flower",
               "toddler", "baby"],
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
             "nail", "manicure", "waxing", "cosmetic product"],
    "네일": ["animal", "wildlife", "landscape", "food", "restaurant", "fitness",
            "hair salon", "waxing"],
    "네일샵": ["animal", "wildlife", "landscape", "food", "restaurant", "fitness",
             "hair salon", "waxing"],
    "왁싱샵": ["animal", "wildlife", "landscape", "food", "restaurant", "fitness",
             "nail", "hair salon"],
    "왁싱": ["animal", "wildlife", "landscape", "food", "restaurant", "fitness",
            "nail", "hair salon"],
    "메이크업": ["animal", "wildlife", "landscape", "food", "restaurant", "fitness",
              "nail", "hair salon", "waxing"],
    # 교육
    "학원": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "toddler", "baby"],
    "스터디카페": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby"],
    # 법률/회계
    "변호사": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
             "cosmetic", "fitness", "toddler", "baby"],
    "법률사무소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
               "cosmetic", "fitness", "toddler", "baby"],
    "법무법인": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby"],
    "법무사": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "toddler", "baby"],
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
             "cosmetic", "fitness"],
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
            "cpu", "processor", "chip", "motherboard", "hardware", "circuit", "component"],
    "피시방": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
             "cosmetic", "fitness", "toddler", "baby",
             "cpu", "processor", "chip", "motherboard", "hardware", "circuit", "component"],
    "세탁소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
             "cosmetic", "fitness", "toddler", "baby"],
    "부동산": ["animal", "wildlife", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "toddler", "baby"],
    # 자동차
    "카센터": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "racing", "formula", "supercar", "toddler", "baby"],
    "자동차정비소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
                "cosmetic", "fitness", "racing", "formula", "supercar"],
    "타이어": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "bicycle tire", "cycle", "motorcycle only"],
    "손세차": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "racing", "toddler", "baby"],
    "디테일링": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "racing", "toddler", "baby"],
    "중고차": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "racing", "formula", "supercar", "toddler", "baby"],
    "렌터카": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "racing", "formula", "toddler", "baby"],
    "렌트카": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
            "cosmetic", "fitness", "racing", "formula", "toddler", "baby"],
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
              "cosmetic", "fitness", "toddler", "baby"],
    "쇼파청소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby"],
    "침구류청소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
               "cosmetic", "fitness", "toddler", "baby"],
    "에어컨청소": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
               "cosmetic", "fitness", "toddler", "baby"],
    # 이사/물류
    "포장이사": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
              "cosmetic", "fitness", "toddler", "baby"],
    "이사": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
           "cosmetic", "fitness", "toddler", "baby"],
    "용달": ["animal", "wildlife", "landscape", "food", "restaurant", "fashion",
           "cosmetic", "fitness", "toddler", "baby", "racing"],
    # 반려동물
    "반려동물": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape"],
    "강아지": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape", "cat", "kitten"],
    "고양이": ["food", "restaurant", "fashion", "cosmetic", "fitness", "landscape", "dog", "puppy"],
    # 웨딩
    "웨딩홀": ["animal", "wildlife", "landscape", "food only", "fashion", "cosmetic", "fitness",
             "toddler", "baby", "outdoor wedding"],
    "예식장": ["animal", "wildlife", "landscape", "food only", "cosmetic", "fitness",
            "toddler", "baby", "outdoor wedding"],
    "웨딩드레스": ["animal", "wildlife", "landscape", "food", "cosmetic", "fitness",
               "toddler", "baby", "tuxedo only", "suit only"],
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
