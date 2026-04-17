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
    "필라테스": ["pilates", "pilates studio", "reformer", "stretching"],
    "요양원": ["nursing home", "elderly care", "senior", "caregiver"],
    "요양센터": ["elderly care", "senior living", "nursing"],
    "요양병원": ["hospital", "senior hospital", "medical care"],
    "카페": ["cafe", "coffee shop", "latte art", "coffee beans", "cafe interior", "espresso"],
    "음식점": ["restaurant", "food", "dining", "plate", "meal"],
    "식당": ["restaurant", "dining", "food plate"],
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
    "노래방": ["karaoke", "neon"],
    "pc방": ["pc gaming", "computer", "gaming cafe"],
    "피시방": ["pc gaming", "computer", "gaming cafe"],
    "세탁소": ["laundry", "washing machine"],
    "부동산": ["real estate", "house", "apartment"],
    "변호사": ["law office", "lawyer", "court"],
    "회계": ["accounting", "finance", "calculator"],
    "스튜디오": ["photo studio", "camera"],
    "사진관": ["photo studio", "portrait"],
}

# 세션 중 이미 사용된 Pixabay 이미지 ID (중복 방지)
_USED_IMAGE_IDS: set = set()


def _get_en_queries(keyword: str) -> list:
    """한국어 키워드(제목의 메인키워드) → 영어 검색어 리스트
    한국어 업종이 아닌 영문/일반 단어가 들어오면 그대로 쿼리로 사용."""
    k = (keyword or "").strip()
    kl = k.lower()
    for ko, en_list in BIZ_TO_EN.items():
        if ko in kl:
            return en_list if isinstance(en_list, list) else [en_list]
    # 한국어 업종 매칭 실패 → 입력 문자열 자체를 쿼리로 사용 (사용자 오버라이드/영문 키워드)
    if k and not any(0xAC00 <= ord(c) <= 0xD7A3 for c in k):
        return [k]
    return ["interior business shop"]


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
    "헬스장": ["fitness"],
    "피트니스": ["fitness"],
    "요가": ["yoga"],
    "필라테스": ["pilates", "reformer"],
    "카페": ["cafe", "coffee"],
    "베이커리": ["bakery", "bread", "pastry"],
    "빵집": ["bakery", "bread", "pastry"],
}

# 업종별 제외 태그 — 이 태그가 들어있으면 무조건 거르기
BIZ_TAG_EXCLUDE = {
    "헬스장": ["gymnast", "rhythmic", "dance", "dancer", "ballet", "yoga", "pilates", "cheerlead",
              "child", "kid", "children", "toddler", "baby", "school", "team sport",
              "soccer", "basketball", "volleyball", "football", "tennis", "swimming",
              "martial", "boxing", "karate", "taekwondo", "judo", "mma"],
    "피트니스": ["gymnast", "rhythmic", "dance", "ballet", "yoga", "pilates", "child", "kid"],
    "요가": ["rhythmic gymnast", "child", "kid"],
    "필라테스": ["rhythmic gymnast", "child", "kid"],
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


def search_images(api_key: str, keyword: str, count: int = 5) -> list[dict]:
    """Pixabay 이미지 검색 — 여러 쿼리 + 랜덤 페이지 + 중복ID 필터"""
    import random

    queries = _get_en_queries(keyword)
    random.shuffle(queries)
    tag_filter = _tag_filter_for(keyword)
    tag_exclude = _tag_exclude_for(keyword)

    def _hit_matches(h):
        tags = (h.get("tags") or "").lower()
        # 제외 태그 중 하나라도 있으면 탈락
        if tag_exclude and any(t in tags for t in tag_exclude):
            return False
        if not tag_filter:
            return True
        return any(t in tags for t in tag_filter)

    pool = []
    seen_ids_in_pool = set()
    # 여러 쿼리/페이지로 후보 풀 구성 (최대 페이지 확장)
    for q in queries:
        for page in range(1, 8):  # 페이지 1~7 전부 훑기
            hits = _fetch_hits(api_key, q, page=page)
            for h in hits:
                hid = h.get("id")
                if hid and hid not in seen_ids_in_pool and hid not in _USED_IMAGE_IDS and _hit_matches(h):
                    seen_ids_in_pool.add(hid)
                    pool.append(h)
            if len(pool) >= count * 5:
                break
        if len(pool) >= count * 5:
            break

    # 풀이 count보다 적으면 exclude만 지키고 tag_filter 없이 재시도
    if len(pool) < count:
        for q in queries:
            for page in range(1, 5):
                hits = _fetch_hits(api_key, q, page=page)
                for h in hits:
                    hid = h.get("id")
                    if hid in seen_ids_in_pool or hid in _USED_IMAGE_IDS:
                        continue
                    tags = (h.get("tags") or "").lower()
                    if tag_exclude and any(t in tags for t in tag_exclude):
                        continue
                    seen_ids_in_pool.add(hid)
                    pool.append(h)
                    if len(pool) >= count * 3:
                        break
                if len(pool) >= count * 3:
                    break
            if len(pool) >= count * 3:
                break

    if not pool:
        # 최후의 수단: 아무 필터 없이
        _USED_IMAGE_IDS.clear()
        pool = _fetch_hits(api_key, queries[0], page=1)

    if len(pool) > count:
        pool = random.sample(pool, count)

    results = []
    for hit in pool[:count]:
        _USED_IMAGE_IDS.add(hit.get("id"))
        results.append({
            "id": hit["id"],
            "url": hit["webformatURL"],
            "large_url": hit["largeImageURL"],
            "tags": hit.get("tags", ""),
            "width": hit["webformatWidth"],
            "height": hit["webformatHeight"],
        })

    return results


def download_images(api_key: str, keyword: str, count: int = 5) -> list[str]:
    """이미지를 검색하고 임시 폴더에 다운로드, 파일 경로 리스트 반환"""
    images = search_images(api_key, keyword, count)
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
            paths.append(file_path)
        except Exception as e:
            print(f"이미지 다운로드 실패 ({i+1}): {e}")

    return paths
