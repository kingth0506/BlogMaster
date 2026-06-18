# -*- coding: utf-8 -*-
"""네이버 지도 크롤링 모듈 (Selenium Chrome — API키 불필요)"""
import os
import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import threading as _threading

# ChromeDriver 경로를 한 번만 설치 후 재사용 (멀티스레드 충돌 방지)
_driver_path_lock = _threading.Lock()
_driver_path_cache = None
_uc_create_lock = _threading.Lock()  # undetected_chromedriver 동시 생성 방지

def _get_driver_path():
    global _driver_path_cache
    with _driver_path_lock:
        if _driver_path_cache is None:
            _driver_path_cache = ChromeDriverManager().install()
        return _driver_path_cache


# 시/도 → 구/군(시) 목록 — 전국 17개 시·도 풀세트
SIDO_DISTRICTS = {
    "서울": ["강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구",
           "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구",
           "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구",
           "은평구", "종로구", "중구", "중랑구"],
    "부산": ["강서구", "금정구", "기장군", "남구", "동구", "동래구", "부산진구",
           "북구", "사상구", "사하구", "서구", "수영구", "연제구", "영도구",
           "중구", "해운대구"],
    "대구": ["남구", "달서구", "달성군", "동구", "북구", "서구", "수성구", "중구", "군위군"],
    "인천": ["강화군", "계양구", "남동구", "동구", "미추홀구", "부평구", "서구",
           "연수구", "옹진군", "중구"],
    "광주": ["광산구", "남구", "동구", "북구", "서구"],
    "대전": ["대덕구", "동구", "서구", "유성구", "중구"],
    "울산": ["남구", "동구", "북구", "울주군", "중구"],
    "세종": ["세종시"],
    "경기": ["수원시", "수원시 장안구", "수원시 권선구", "수원시 팔달구", "수원시 영통구",
           "성남시", "성남시 수정구", "성남시 중원구", "성남시 분당구",
           "고양시", "고양시 덕양구", "고양시 일산동구", "고양시 일산서구",
           "용인시", "용인시 처인구", "용인시 기흥구", "용인시 수지구",
           "부천시", "안산시", "안산시 상록구", "안산시 단원구",
           "안양시", "안양시 만안구", "안양시 동안구",
           "남양주시", "화성시", "평택시", "의정부시", "시흥시", "파주시", "광명시",
           "김포시", "군포시", "광주시", "이천시", "양주시", "오산시", "구리시",
           "안성시", "포천시", "의왕시", "하남시", "여주시", "동두천시", "과천시",
           "양평군", "가평군", "연천군"],
    "강원": ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시",
           "홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군",
           "양구군", "인제군", "고성군", "양양군"],
    "충북": ["청주시", "청주시 상당구", "청주시 서원구", "청주시 흥덕구", "청주시 청원구",
           "충주시", "제천시", "보은군", "옥천군", "영동군", "증평군", "진천군",
           "괴산군", "음성군", "단양군"],
    "충남": ["천안시", "천안시 동남구", "천안시 서북구", "공주시", "보령시", "아산시",
           "서산시", "논산시", "계룡시", "당진시", "금산군", "부여군", "서천군",
           "청양군", "홍성군", "예산군", "태안군"],
    "전북": ["전주시", "전주시 완산구", "전주시 덕진구", "군산시", "익산시", "정읍시",
           "남원시", "김제시", "완주군", "진안군", "무주군", "장수군", "임실군",
           "순창군", "고창군", "부안군"],
    "전남": ["목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군",
           "구례군", "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군",
           "영암군", "무안군", "함평군", "영광군", "장성군", "완도군", "진도군", "신안군"],
    "경북": ["포항시", "포항시 남구", "포항시 북구", "경주시", "김천시", "안동시", "구미시",
           "영주시", "영천시", "상주시", "문경시", "경산시", "의성군", "청송군",
           "영양군", "영덕군", "청도군", "고령군", "성주군", "칠곡군", "예천군",
           "봉화군", "울진군", "울릉군"],
    "경남": ["창원시", "창원시 의창구", "창원시 성산구", "창원시 마산합포구",
           "창원시 마산회원구", "창원시 진해구", "진주시", "통영시", "사천시",
           "김해시", "밀양시", "거제시", "양산시", "의령군", "함안군", "창녕군",
           "고성군", "남해군", "하동군", "산청군", "함양군", "거창군", "합천군"],
    "제주": ["제주시", "서귀포시"],
}


BIZ_SYNONYMS = {
    # 법률/행정/전문직
    "변호사": ["변호사", "법률사무소", "로펌", "법무법인"],
    "변호사사무실": ["변호사", "법률사무소", "로펌", "법무법인"],
    "변호사사무소": ["변호사", "법률사무소", "로펌", "법무법인"],
    "이혼변호사": ["이혼변호사", "이혼전문변호사", "가사전문변호사", "이혼법무법인", "법률사무소", "로펌", "법무법인"],
    "형사변호사": ["형사변호사", "형사전문변호사", "형사법무법인", "법률사무소", "로펌", "법무법인"],
    "음주운전변호사": ["음주운전변호사", "교통사고변호사", "형사전문변호사", "법률사무소", "법무법인"],
    "개인회생": ["개인회생", "개인파산", "법인파산", "회생신청", "파산신청", "법무법인", "법률사무소"],
    "법무사": ["법무사", "법무사사무소"],
    "세무사": ["세무사", "세무회계", "양도소득세", "상속세", "세금신고", "세금상담"],
    "회계사": ["회계사", "회계", "회계법인", "공인회계사"],
    "법인설립": ["법인설립", "법인등기", "사업자등록", "법인설립대행", "세무사", "법무사"],
    "관세사": ["관세사", "관세법인", "관세사사무소"],
    "변리사": ["변리사", "특허사무소", "특허법인"],
    "노무사": ["노무사", "공인노무사", "노무법인", "인사노무", "부당해고", "임금체불"],
    "감정평가사": ["감정평가사", "감정평가", "감정평가법인"],
    "행정사": ["행정사", "행정사사무소", "행정사법인"],
    "손해사정사": ["손해사정사", "손해사정", "손해사정법인"],
    "건축사": ["건축사", "건축사사무소", "건축설계사무소"],

    # 금융/대출/보험
    "대출": ["대출", "담보대출", "아파트담보대출", "사업자대출", "법인대출", "신용대출", "주택담보대출", "대환대출"],
    "보험": ["보험", "보험설계", "보험상담", "운전자보험", "치아보험", "암보험", "보험대리점"],

    # 의료
    "병원": ["병원", "의원", "클리닉", "종합병원"],
    "의원": ["의원", "병원", "클리닉"],
    "치과": ["치과", "치과의원", "치과병원", "임플란트", "교정", "라미네이트", "투명교정", "치아미백"],
    "한의원": ["한의원", "한방병원", "한방", "한방클리닉", "교통사고한의원", "다이어트한약", "추나요법"],
    "약국": ["약국"],
    "안과": ["안과", "안과의원", "안과병원", "라식", "라섹", "렌즈삽입", "스마일라식", "백내장"],
    "피부과": ["피부과", "피부과의원", "피부클리닉", "피부관리", "울쎄라", "필러", "보톡스", "리프팅", "써마지"],
    "성형외과": ["성형외과", "성형외과의원", "미용성형", "안면윤곽", "눈매교정", "쌍꺼풀", "가슴성형", "지방흡입"],
    "탈모": ["탈모", "탈모클리닉", "탈모치료", "두피케어", "두피관리", "탈모전문"],
    "모발이식": ["모발이식", "탈모클리닉", "탈모치료", "헤어라인교정", "두피케어", "모발이식클리닉"],
    "통증의학과": ["통증의학과", "통증클리닉", "재활의학과", "정형외과", "도수치료"],
    "동물병원": ["동물병원", "수의원"],

    # 복지/돌봄
    "요양원": ["요양원", "노인요양시설", "실버타운", "노인복지", "노인요양"],

    # 운동/뷰티
    "헬스장": ["헬스장", "휘트니스", "피트니스", "짐", "웨이트트레이닝"],
    "필라테스": ["필라테스", "필라테스전문", "요가필라테스"],
    "요가": ["요가", "요가원", "요가스튜디오"],
    "골프장": ["골프장", "골프클럽", "컨트리클럽", "CC"],
    "골프연습장": ["골프연습장", "인도어골프", "실내골프", "스크린골프"],
    "스크린골프": ["스크린골프", "실내골프", "골프연습장"],
    "미용실": ["미용실", "헤어샵", "헤어살롱", "헤어숍", "미용"],
    "왁싱샵": ["왁싱", "왁싱샵", "브라질리언왁싱"],
    "네일샵": ["네일", "네일샵", "네일아트", "네일케어"],
    "네일아트": ["네일", "네일샵", "네일아트", "네일케어"],
    "메이크업": ["메이크업", "메이크업샵", "뷰티", "웨딩메이크업"],

    # 숙박/공간
    "풀빌라": ["풀빌라", "풀빌라펜션", "독채펜션", "빌라"],
    "펜션": ["펜션", "독채펜션", "풀빌라"],
    "캠핑장": ["캠핑장", "오토캠핑장", "글램핑", "캠핑"],
    "고시원": ["고시원", "고시텔", "원룸텔", "셰어하우스"],
    "원룸텔": ["원룸텔", "고시원", "고시텔"],
    "공유오피스": ["공유오피스", "사무실임대", "비즈니스센터", "소호사무실"],
    "파티룸": ["파티룸", "모임공간", "이벤트룸", "렌탈스튜디오"],
    "스튜디오": ["스튜디오", "사진스튜디오", "촬영스튜디오", "대여스튜디오"],

    # 학습/F&B
    "학원": ["학원", "교습소"],
    "스터디카페": ["스터디카페", "독서실", "학습카페"],
    "카페": ["카페", "커피", "로스터리", "커피숍", "커피전문점"],
    "맛집": [
        "한식", "양식", "일식", "중식", "레스토랑", "음식점", "분식",
        "고깃집", "횟집", "고기", "구이", "요리", "냉면", "국수",
        "카페", "디저트", "곱창", "막창", "닭갈비", "닭요리", "닭볶음탕",
        "피자", "파스타", "백반", "가정식", "해물", "생선", "우동", "소바",
        "라멘", "돈가스", "덮밥", "분식", "치킨", "삼겹살", "소고기",
        "맥주", "호프", "바", "와인", "이자카야", "베이커리", "빵",
        "브런치", "샐러드", "버거", "스테이크", "타코", "쌀국수",
    ],

    # 자동차
    "카센터": ["카센터", "자동차정비소", "자동차정비", "정비공장", "정비소"],
    "자동차정비소": ["자동차정비소", "자동차정비", "카센터", "정비공장", "정비소"],
    "타이어": ["타이어", "타이어전문점", "자동차타이어"],
    "손세차": ["손세차", "세차장", "디테일링", "카워시"],
    "디테일링": ["디테일링", "카디테일링", "손세차", "자동차용품"],
    "중고차": ["중고차", "중고차매매", "자동차매매", "자동차매매상사"],
    "렌터카": ["렌터카", "렌트카", "자동차대여"],
    "렌트카": ["렌트카", "렌터카", "자동차대여"],

    # 생활/설비
    "누수탐지": ["누수탐지", "누수공사", "수도공사", "배관"],
    "하수구": ["하수구", "배관", "하수공사", "수도공사", "설비"],
    "싱크대": ["싱크대", "싱크대막힘", "싱크대수리", "싱크대교체", "배관", "설비"],
    "변기": ["변기", "변기교체", "변기수리", "양변기", "변기막힘", "화장실설비"],
    "보일러": ["보일러", "보일러수리", "보일러교체", "보일러설치", "난방공사", "온수"],
    "열쇠": ["열쇠", "출장열쇠", "열쇠수리", "열쇠복사", "잠금장치", "24시열쇠", "키수리"],
    "도어락": ["도어락", "디지털도어락", "도어락설치", "도어락교체", "스마트도어락", "번호키"],
    "인테리어": ["인테리어", "실내인테리어", "인테리어디자인", "홈인테리어", "아파트리모델링", "상가인테리어", "주방리모델링", "사무실인테리어"],
    "에어컨설치": ["에어컨설치", "에어컨이전설치", "에어컨교체", "에어컨공사", "에어컨"],
    "TV설치": ["TV설치", "벽걸이TV", "벽걸이TV설치", "가전설치", "TV브라켓"],
    "가전제품": ["가전제품", "가전매장", "전자제품", "가전"],
    "렌탈": ["렌탈", "정수기렌탈", "음식물처리기렌탈", "정수기", "렌탈서비스", "정수기설치"],
    "안마의자": ["안마의자", "마사지체어"],

    # 청소
    "입주청소": ["입주청소", "이사청소", "청소대행", "가사도우미", "홈클리닝", "전문청소"],
    "가구청소": ["청소", "가구청소", "홈클리닉"],
    "쇼파청소": ["쇼파청소", "소파청소", "가구청소", "홈클리닉"],
    "침구류청소": ["침구청소", "침구류청소", "매트리스청소"],
    "에어컨청소": ["에어컨청소", "에어컨세척", "가전청소"],

    # 이사/물류
    "포장이사": ["포장이사", "이사", "이삿짐", "용달이사", "이삿짐센터"],
    "이사": ["이사", "이삿짐", "포장이사", "용달", "이삿짐센터", "보관이사", "사무실이사"],
    "용달": ["용달", "용달이사", "소형이사"],

    # 반려동물
    "반려동물": ["반려동물", "애견", "펫샵", "애묘", "동물용품"],
    "강아지": ["애견", "강아지", "반려견", "펫샵", "애견카페", "애견미용", "애견호텔", "애견유치원"],
    "고양이": ["고양이", "애묘", "반려묘", "고양이카페", "고양이호텔"],

    # 웨딩
    "웨딩홀": ["웨딩홀", "예식장", "웨딩", "컨벤션"],
    "예식장": ["예식장", "웨딩홀", "웨딩"],
    "웨딩드레스": ["웨딩드레스", "드레스샵", "웨딩샵"],

    # 창업
    "창업": ["창업", "무인카페창업", "스터디카페창업", "밀키트창업", "편의점창업", "프랜차이즈", "창업상담"],

    # 부동산
    "부동산": ["부동산", "공인중개사"],
}


def _match_biz(biz_type: str, category: str) -> bool:
    """업종 필터 매칭 — 양방향 포함 + 유의어 + 2자 접두 완화"""
    if not biz_type:
        return True
    if not category:
        return True  # 카테고리 못 읽으면 필터 통과 (수집 우선)
    b, c = biz_type.strip(), category.strip()
    # 직접 포함
    if b in c or c in b:
        return True
    # 유의어 사전
    for syn in BIZ_SYNONYMS.get(b, []):
        if syn in c or c in syn:
            return True
    # 2자 접두 매칭 (변호사↔변호, 치과↔치과 등)
    if len(b) >= 2 and b[:2] in c:
        return True
    if len(c) >= 2 and c[:2] in b:
        return True
    return False


def expand_keyword_to_districts(keyword: str) -> list:
    """'서울 요양원'처럼 시/도 + 업종만 있는 키워드를 '서울 강남구 요양원' 식으로 전 구 확장.
    확장 불가 시 원본 1개 리스트 반환."""
    parts = (keyword or "").strip().split()
    if len(parts) != 2:
        return [keyword]
    sido, biz = parts
    dists = SIDO_DISTRICTS.get(sido)
    if not dists:
        return [keyword]
    return [f"{sido} {d} {biz}" for d in dists]


_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
]


def crawl_places_parallel(keywords: list, count_per: int, on_progress=None,
                           existing_places: list = None,
                           existing_by_keyword: dict = None,
                           exclude_keywords: list = None,
                           max_workers: int = 3,
                           stop_flag=lambda: False,
                           emit_log=lambda m: None,
                           save_batch=lambda items: None,
                           on_item=None,
                           no_filter: bool = False,
                           profile_dir: str = None):
    """여러 지역 키워드를 N개 단위 배치로 병렬 크롤.
    - 1배치 = N개 키워드를 N개 독립 드라이버로 동시 처리
    - 배치 완료 → 결과 누적·save_batch 콜백 호출 → 드라이버 전부 종료 → 다음 배치
    - 각 배치마다 새 드라이버 (세션·UA 재분리해 감지 회피)"""
    import threading as _th
    from concurrent.futures import ThreadPoolExecutor, as_completed

    keywords = list(keywords or [])
    if not keywords:
        return list(existing_places or [])

    max_workers = max(1, min(max_workers, len(keywords)))

    lock = _th.Lock()
    merged = list(existing_places or [])
    collected_names = set((p.get("name") or "").strip() for p in merged if p.get("name"))

    # 공유 큐 방식 — 워커가 끝나면 다음 키워드 바로 pull, 드라이버는 워커 수명 내내 재사용
    import queue as _q
    kq = _q.Queue()
    for kw in keywords:
        kq.put(kw)

    def _worker_loop(worker_idx):
        import time as _t, shutil as _sh
        drv = None
        # 봇별 시작 시간 엇갈리기 — 동시 접속 시 네이버 차단 방지 (봇1 기준 15초 간격)
        if worker_idx > 0:
            _stagger = worker_idx * 15
            emit_log(f"  [봇{worker_idx+1}] {_stagger}초 후 시작 (동시 접속 차단 방지)")
            _end = _t.time() + _stagger
            while _t.time() < _end:
                if stop_flag(): return
                _t.sleep(0.2)
        # 워커별 프로필 복사 (로그인 세션 격리)
        _worker_profile = None
        if profile_dir:
            try:
                _worker_profile = _clone_profile_for_crawl(profile_dir, worker_idx)
            except Exception as _pe:
                emit_log(f"  [봇{worker_idx+1}] 프로필 복사 실패 ({str(_pe)[:50]}) — 비로그인 모드")
        # 드라이버 생성 재시도 (Windows 병렬 Chrome 시작 race 대응)
        for _attempt in range(3):
            try:
                drv = _make_driver(browser="chrome", profile_dir=_worker_profile)
                break
            except Exception as e:
                if _attempt < 2:
                    emit_log(f"  [봇{worker_idx+1}] 드라이버 생성 재시도 {_attempt+2}/3 ({str(e)[:50]})")
                    _t.sleep(3 + worker_idx * 2)
                else:
                    emit_log(f"  [봇{worker_idx+1}] 드라이버 생성 실패: {e}")
                    return
        if drv is None:
            return
        try:
            while True:
                if stop_flag(): break
                try:
                    kw = kq.get_nowait()
                except _q.Empty:
                    break
                try:
                    # on_progress에 봇 번호 태그 추가
                    def _tagged_progress(cur, scanned, name, results_ref=None, _w=worker_idx):
                        if on_progress:
                            on_progress(cur, scanned, f"[봇{_w+1}] {name}", results_ref)
                    emit_log(f"  [봇{worker_idx+1}] {kw} 크롤 시작")
                    # 키워드 간 프레임 초기화 + 네이버 홈 경유 (쿠키 유지 — 로그인 세션 보존)
                    try: drv.switch_to.default_content()
                    except Exception: pass
                    try: drv.get("https://www.naver.com")
                    except Exception: pass
                    import time as _t
                    # 1.5초 대기 — 중단 즉시 반응 (0.2초 단위)
                    _wait_end = _t.time() + 1.5
                    while _t.time() < _wait_end:
                        if stop_flag(): break
                        _t.sleep(0.2)
                    if stop_flag(): break
                    # 키워드별 독립 크롤 — 이전 저장 데이터 이어서 수집
                    _kw_existing = list((existing_by_keyword or {}).get(kw, []))
                    r = crawl_places(kw, count_per, _tagged_progress,
                                     existing_places=_kw_existing,
                                     exclude_keywords=exclude_keywords,
                                     no_filter=no_filter,
                                     driver=drv,
                                     on_item=on_item,
                                     stop_flag=stop_flag,
                                     emit_log=emit_log)
                    new_items = []
                    with lock:
                        for p in r:
                            n = (p.get("name") or "").strip()
                            if n and n not in collected_names:
                                collected_names.add(n)
                                p["search_keyword"] = kw
                                merged.append(p)
                                new_items.append(p)
                    emit_log(f"  [봇{worker_idx+1}] {kw} 완료 (수집 {len(r)}개, 신규 +{len(new_items)}개)")
                    try:
                        with lock:
                            snapshot = list(merged)
                        # save_batch(snapshot, keyword, raw_items_for_this_keyword)
                        try:
                            save_batch(snapshot, kw, list(r))
                        except TypeError:
                            save_batch(snapshot)
                    except Exception as e:
                        emit_log(f"저장 실패: {e}")
                except Exception as e:
                    is_conn_err = any(x in str(e) for x in ("10061", "10054", "Connection refused", "Connection aborted", "ConnectionReset", "WinError", "disconnected"))
                    if is_conn_err:
                        emit_log(f"  [봇{worker_idx+1}] 연결 거부 — {kw} 재수집 대기열에 추가")
                        kq.put(kw)  # 실패 키워드 다시 큐에
                    else:
                        emit_log(f"  [봇{worker_idx+1}] {kw} 실패 ({str(e)[:60]})")
                    try: drv.quit()
                    except Exception: pass
                    drv = None
                    # 드라이버 재생성 (실패 시 워커 종료 → 나머지 봇들이 큐 처리)
                    for _ra in range(3):
                        try:
                            drv = _make_driver(browser="chrome", profile_dir=_worker_profile)
                            break
                        except Exception:
                            if _ra < 2: _t.sleep(3)
                            else:
                                emit_log(f"  [봇{worker_idx+1}] 드라이버 재생성 실패 — 봇 종료")
                                return
        finally:
            try:
                if drv: drv.quit()
            except Exception: pass
            if _worker_profile:
                try: _sh.rmtree(_worker_profile, ignore_errors=True)
                except Exception: pass

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_worker_loop, i) for i in range(max_workers)]
        for f in as_completed(futures):
            try: f.result()
            except Exception as e: emit_log(f"봇 예외: {e}")
    return merged


def _clone_profile_for_crawl(base_profile_dir: str, worker_idx: int) -> str:
    """로그인 프로필을 워커별 임시 디렉토리로 복사 (병렬 실행 시 프로필 충돌 방지).
    Cache 계열 대용량 폴더는 제외하고 쿠키/설정만 복사."""
    import tempfile as _tf, shutil as _sh
    dst = os.path.join(_tf.gettempdir(), "blogmaster_crawl", f"w{worker_idx}")
    src_default = os.path.join(base_profile_dir, "Default")
    dst_default = os.path.join(dst, "Default")
    if os.path.exists(dst):
        _sh.rmtree(dst, ignore_errors=True)
    if os.path.isdir(src_default):
        _SKIP = {"Cache", "GPUCache", "DawnCache", "ShaderCache",
                 "Code Cache", "VideoDecodeStats", "CacheStorage",
                 "Service Worker", "IndexedDB", "databases"}
        _sh.copytree(src_default, dst_default,
                     ignore=_sh.ignore_patterns(*_SKIP),
                     copy_function=_sh.copy2)
    else:
        os.makedirs(dst_default, exist_ok=True)
    return dst


def _make_driver(user_agent: str = None, browser: str = "chrome", profile_dir: str = None, headless: bool = True):
    """새 드라이버 생성 (병렬 워커용). browser='chrome' | 'edge'
    profile_dir 있으면 undetected_chromedriver + 로그인 세션 사용."""
    import random as _rnd
    import os as _os

    # 로그인 프로필 모드 — undetected_chromedriver 사용
    if profile_dir:
        try:
            import undetected_chromedriver as _uc
            for _lk in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
                _lp = os.path.join(profile_dir, _lk)
                if os.path.exists(_lp):
                    try: os.remove(_lp)
                    except: pass
            try:
                _lp = os.path.join(profile_dir, "Default", "LOCK")
                if os.path.exists(_lp): os.remove(_lp)
            except: pass
            _o = _uc.ChromeOptions()
            _o.add_argument(f"--user-data-dir={profile_dir}")
            _o.add_argument("--window-size=1920,1080")
            _o.add_argument("--disable-gpu")
            _o.add_argument("--no-sandbox")
            _o.add_argument("--disable-dev-shm-usage")
            _o.add_argument("--disable-extensions")
            _o.add_argument("--mute-audio")
            _o.add_argument("--disable-background-networking")
            _o.add_argument("--disable-default-apps")
            _o.add_argument("--disable-sync")
            _o.add_argument("--disable-features=AudioServiceOutOfProcess,TranslateUI")
            with _uc_create_lock:  # 동시 생성 시 chromedriver 패치 race 방지
                return _uc.Chrome(options=_o, headless=headless)
        except Exception:
            pass  # undetected_chromedriver 없거나 실패 → 일반 드라이버로 fallback

    def _build_options(headless_flag=None):
        if browser == "edge":
            from selenium.webdriver.edge.options import Options as EdgeOptions
            opts = EdgeOptions()
        else:
            opts = Options()
        if headless_flag and not _os.environ.get("CRAWL_VISIBLE"):
            opts.add_argument(headless_flag)
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--window-size=1920,1080")
        # 저사양 PC 메모리 절약 옵션 — 네이버 지도는 이미지/JS 기반 UI라 이미지 비활성화 금지
        # (imagesEnabled=false 시 목록 로딩 자체가 깨짐 — 0개 수집됨)
        opts.add_argument("--disable-features=AudioServiceOutOfProcess,TranslateUI")
        opts.add_argument("--mute-audio")
        opts.add_argument("--disable-background-networking")
        opts.add_argument("--disable-default-apps")
        opts.add_argument("--disable-sync")
        ua = user_agent or _rnd.choice(_UA_POOL)
        opts.add_argument(f"user-agent={ua}")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        return opts

    def _create(opts):
        if browser == "edge":
            d = webdriver.Edge(options=opts)
        else:
            service = Service(_get_driver_path())
            d = webdriver.Chrome(service=service, options=opts)
        d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return d

    if _os.environ.get("CRAWL_VISIBLE") or not headless:
        return _create(_build_options())

    return _create(_build_options("--headless"))


def crawl_places(keyword: str, count: int = 100, on_progress=None,
                 existing_places: list = None,
                 exclude_keywords: list = None,
                 driver=None,
                 on_item=None,
                 direct_url: str = None,
                 no_filter: bool = False,
                 stop_flag=lambda: False,
                 profile_dir: str = None,
                 emit_log=None,
                 force_visible: bool = False) -> list[dict]:
    """네이버 지도에서 키워드로 업체 크롤링 (Chrome).
    existing_places가 주어지면 그 업체들은 스킵하고 이어서 크롤 (재개 모드).
    exclude_keywords 중 하나라도 업체명/카테고리/주소에 포함되면 제외.
    driver 제공 시 재사용 (종료 안 함). None이면 새로 생성 + 종료.
    no_filter=True 시 업종/지역 필터 미적용 (키워드 기반 전체 수집)."""
    exclude_keywords = [k.strip() for k in (exclude_keywords or []) if k and k.strip()]

    _url_mode = bool(direct_url) or no_filter
    if _url_mode:
        area = ""
        biz_type = keyword.strip() if keyword else ""
        area_filter = ""
    else:
        parts = keyword.strip().split()
        area = parts[0] if len(parts) >= 2 else ""
        biz_type = parts[-1] if len(parts) >= 2 else keyword
        if len(parts) >= 3:
            area = " ".join(parts[:-1])
            biz_type = parts[-1]
        area_filter = parts[-2] if len(parts) >= 3 else (parts[0] if len(parts) >= 2 else "")

    # driver 재사용 지원
    _own_driver = driver is None
    if _own_driver:
        driver = _make_driver(profile_dir=profile_dir, headless=not force_visible)

    results = list(existing_places or [])
    collected_names = set()
    for _p in results:
        _n = (_p.get("name") or "").strip()
        if _n:
            collected_names.add(_n)
    scanned = 0
    # 재개 시 인덱스 정합성 유지
    for _i, _p in enumerate(results, start=1):
        _p["index"] = _i

    # 중단 가능한 짧은 sleep (0.2초마다 체크)
    def _sleep_or_stop(secs):
        end = time.time() + float(secs)
        while time.time() < end:
            if stop_flag():
                raise InterruptedError("중단됨")
            time.sleep(min(0.2, end - time.time()))

    try:
        if stop_flag(): raise InterruptedError("중단됨")
        if direct_url:
            driver.get(direct_url)
        else:
            from urllib.parse import quote as _quote
            driver.get(f"https://map.naver.com/p/search/{_quote(keyword)}?searchType=place")
        _sleep_or_stop(4)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
        )
        driver.switch_to.frame("searchIframe")
        _sleep_or_stop(2)

        # 네이버 차단 감지 + 25초 대기 재시도 (최대 1회)
        try:
            if "서비스 이용에 제한" in driver.find_element(By.TAG_NAME, "body").text:
                _bmsg = f"<span style='color:#ef4444'>⛔ [봇] {keyword} — 네이버 차단 감지, 25초 대기 후 재시도...</span>"
                if emit_log: emit_log(_bmsg)
                driver.switch_to.default_content()
                _sleep_or_stop(25)
                from urllib.parse import quote as _quote
                driver.get(f"https://map.naver.com/p/search/{_quote(keyword)}?searchType=place")
                _sleep_or_stop(4)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
                )
                driver.switch_to.frame("searchIframe")
                _sleep_or_stop(2)
                if "서비스 이용에 제한" in driver.find_element(By.TAG_NAME, "body").text:
                    _fmsg = f"<span style='color:#ef4444'>⛔ [봇] {keyword} — 차단 지속, 수집 불가</span>"
                    if emit_log: emit_log(_fmsg)
        except InterruptedError:
            raise
        except Exception:
            pass

        # 업체 아이템 셀렉터 (Naver 2026-06 업데이트 — 신/구 UI 동시 지원)
        # 신 UI: li.naf7A.sv5z6 (2026-06 정찰 확인). 클래스명은 자주 바뀌므로 fallback 다수
        ITEM_SEL = ("li.Fh8nG, li.UEzoS, li.VLTHu, li[class*='UEzoS'], li.DWs4Q, "
                    "li.naf7A, li[class*='naf7A'], li.sv5z6, "
                    "#_pcmap_list_scroll_container ul > li[class]")

        # iframe JS 렌더링 완료 대기 — 고정 sleep 대신 실제 아이템 출현까지 대기
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ITEM_SEL))
            )
        except Exception:
            pass
        NAME_SEL = ("span.moQ_p, span.TYaxT, a.place_bluelink, span.YwYLL, span.q2LdB, "
                    "span.O_Uah, a span.O_Uah, "
                    ".pui__ek7lQY span, [class*='place_bluelink'] span, "
                    "div.H0S1k span, div.KgfA6 span, "
                    "a[role='button'] > span:first-child")
        CAT_SEL = ("span.ulItq, span.dThr8, span.KCMnt, span.YzBgS, span.lHBM6, "
                    "span.D_oCM, span.RGyAk")

        def _extract_name_cat_fallback(it):
            """신 UI에서 셀렉터 매칭 실패 시 li 텍스트 줄 분석으로 추출.
            li.text 형태: '업체명\\n카테고리\\n영업상태\\n...주소...'.
            첫 줄=이름, 둘째 줄=카테고리 가정."""
            try:
                full = (it.text or "").strip()
            except Exception:
                return "", ""
            if not full:
                return "", ""
            lines = [l.strip() for l in full.split("\n") if l.strip()]
            if not lines:
                return "", ""
            n = lines[0]
            c = lines[1] if len(lines) > 1 else ""
            # 카테고리 라인이 시간/주소처럼 보이면 비움
            if any(p in c for p in ("현재 위치에서", "km", "진료", "영업", "정보 더보기", "더보기", ":", "분 ")):
                c = ""
            # 이름이 너무 길면 (다른 정보가 섞임) 첫 10단어로 자르기
            if len(n) > 60:
                n = n.split()[0:6]
                n = " ".join(n)
            return n, c

        no_new_pages = 0  # 연속으로 새 결과 0개인 페이지 수
        while len(results) < count:
            if stop_flag(): raise InterruptedError("중단됨")
            if on_progress:
                try:
                    on_progress(len(results), scanned, "목록 수집 중...", results)
                except InterruptedError:
                    raise

            items = driver.find_elements(By.CSS_SELECTOR, ITEM_SEL)
            results_before_page = len(results)

            for idx in range(len(items)):
                if stop_flag(): raise InterruptedError("중단됨")
                if len(results) >= count:
                    break
                try:
                    items = driver.find_elements(By.CSS_SELECTOR, ITEM_SEL)
                    if idx >= len(items):
                        break
                    item = items[idx]

                    # 이름 — 셀렉터 매칭 안 되면 li 텍스트 줄 fallback
                    name = ""
                    try:
                        name = item.find_element(By.CSS_SELECTOR, NAME_SEL).text.strip()
                    except Exception:
                        pass
                    if not name:
                        name, _cat_fb = _extract_name_cat_fallback(item)
                    if not name or name in collected_names:
                        continue

                    # 카테고리
                    category = ""
                    try:
                        category = item.find_element(By.CSS_SELECTOR, CAT_SEL).text.strip()
                    except Exception:
                        pass
                    if not category:
                        _name_fb, _cat_fb2 = _extract_name_cat_fallback(item)
                        category = _cat_fb2

                    scanned += 1

                    # 제외 키워드 1차 (이름+카테고리)
                    if exclude_keywords and any(ex in f"{name} {category}" for ex in exclude_keywords):
                        collected_names.add(name)
                        continue

                    # 검색 목록 카드의 텍스트에서 미리 동 추출 (예: "27km · 서울 강남구 논현동")
                    list_card_text = ""
                    try:
                        list_card_text = item.text or ""
                    except Exception:
                        pass

                    # 업체 상세 열기 (entryIframe에서 주소/지번/근처역 추출)
                    short_addr, jibun_addr, nearby_station = "", "", ""
                    place_id = ""
                    try:
                        # 셀렉터 매칭 안 되면 li 자체를 클릭 (신 UI에선 li 클릭으로도 상세 열림)
                        try:
                            name_el = item.find_element(By.CSS_SELECTOR, NAME_SEL)
                        except Exception:
                            name_el = item
                        driver.execute_script("arguments[0].click();", name_el)
                        _sleep_or_stop(1.0)

                        driver.switch_to.default_content()
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#entryIframe"))
                        )
                        # place_id: 현재 URL 또는 entryIframe src에서 추출
                        try:
                            ifr = driver.find_element(By.CSS_SELECTOR, "iframe#entryIframe")
                            src = ifr.get_attribute("src") or ""
                            mpid = re.search(r"/place/(\d+)", src) or re.search(r"/place/(\d+)", driver.current_url)
                            if mpid:
                                place_id = mpid.group(1)
                        except Exception:
                            pass
                        driver.switch_to.frame("entryIframe")
                        _sleep_or_stop(0.8)

                        body_text = driver.find_element(By.TAG_NAME, "body").text

                        # 주소: 서울 XX구 XX동 (도로명 또는 지번 첫 줄)
                        addr_match = re.search(
                            r"((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)\s+\S+[시군구]\s+\S+(?:로|길|동|리|가)[^\n]*)",
                            body_text,
                        )
                        if addr_match:
                            short_addr = addr_match.group(1).strip()
                        else:
                            m2 = re.search(r"(\S+[구군]\s+\S+(?:동|리))", body_text)
                            if m2:
                                short_addr = m2.group(1).strip()

                        # 지번: 우선 검색 목록 카드 텍스트에서 동 추출 (가장 확실)
                        # 예: "27km · 서울 강남구 논현동" 또는 "강남구 논현동"
                        if list_card_text:
                            m = re.search(
                                r"((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)?\s*\S+[시군구]\s+\S+(?:동|리))(?:\s|$|[·•\-])",
                                list_card_text + " ",
                            )
                            if m:
                                jibun_addr = m.group(1).strip()

                        # 폴백: entryIframe body_text에서 추출 시도
                        if not jibun_addr:
                            jibun_match = re.search(
                                r"지번\s*[:\n]?\s*((?:\S+[구군]\s+)?\S+(?:동|리)(?:\s+[\d\-]+)?[^\n]*)",
                                body_text,
                            )
                            if jibun_match:
                                jibun_addr = jibun_match.group(1).strip()

                        # 근처역
                        station_match = re.search(r"(\S+역)\s*\d+번\s*출구", body_text)
                        if station_match:
                            raw_station = station_match.group(1)
                            cleaned = re.sub(r"^[\d호선GTX\-A-Za-z]+", "", raw_station)
                            nearby_station = cleaned if cleaned.endswith("역") else raw_station

                        driver.switch_to.default_content()
                        driver.switch_to.frame("searchIframe")
                    except Exception:
                        try:
                            driver.switch_to.default_content()
                            driver.switch_to.frame("searchIframe")
                        except Exception:
                            pass
                        continue

                    # 지역 필터 — URL 모드는 스킵
                    if not _url_mode and area_filter and area_filter not in short_addr:
                        collected_names.add(name)
                        continue

                    # 제외 키워드 2차 (주소 포함)
                    if exclude_keywords:
                        _haystack = f"{name} {category} {short_addr}"
                        if any(ex in _haystack for ex in exclude_keywords):
                            collected_names.add(name)
                            continue

                    dong = _extract_dong(short_addr)
                    place = {
                        "index": len(results) + 1,
                        "name": name,
                        "address": short_addr,
                        "jibun_address": jibun_addr,
                        "category": category,
                        "nearby_station": nearby_station,
                        "front_keywords": _generate_front_keywords(area_filter, biz_type, dong),
                        "tags": _generate_tags(dong, biz_type, area_filter, nearby_station),
                        "pixabay_keywords": _generate_pixabay_keywords(area_filter, biz_type, dong),
                        "dong": dong,
                        "place_id": place_id,
                    }
                    collected_names.add(name)
                    results.append(place)

                    if on_item:
                        try:
                            on_item(place, results, keyword)
                        except Exception:
                            pass

                    if on_progress:
                        try:
                            on_progress(len(results), scanned, name, results)
                        except InterruptedError:
                            raise

                except InterruptedError:
                    raise
                except Exception:
                    continue

            # 이 페이지에서 새 결과 없으면 종료
            if len(results) == results_before_page:
                no_new_pages += 1
                if no_new_pages >= 2:
                    break
            else:
                no_new_pages = 0

            # 스크롤
            prev_item_count = len(driver.find_elements(By.CSS_SELECTOR, ITEM_SEL))
            scroll_tries = 0
            while scroll_tries < 5:
                if stop_flag(): raise InterruptedError("중단됨")
                driver.execute_script(
                    "let el = document.querySelector('#_pcmap_list_scroll_container') || "
                    "document.querySelector('.Ryr1F') || document.querySelector('[class*=scroll]');"
                    "if(el) el.scrollTop += 1000; else window.scrollBy(0, 1000);"
                )
                _sleep_or_stop(1.5)
                new_item_count = len(driver.find_elements(By.CSS_SELECTOR, ITEM_SEL))
                if new_item_count > prev_item_count:
                    prev_item_count = new_item_count
                    break
                scroll_tries += 1

            # 스크롤 후에도 새 항목 없으면 다음 페이지로 이동
            items_after = driver.find_elements(By.CSS_SELECTOR, ITEM_SEL)
            if len(items_after) <= len(items):
                if stop_flag(): raise InterruptedError("중단됨")
                if on_progress:
                    try:
                        on_progress(len(results), scanned, "다음 페이지 이동 중...", results)
                    except InterruptedError:
                        raise
                # 스크롤을 맨 아래로 내려서 페이지 버튼 보이게
                driver.execute_script(
                    "let el = document.querySelector('.Ryr1F') || document.querySelector('[class*=scroll]');"
                    "if(el) el.scrollTop = el.scrollHeight; else window.scrollTo(0, document.body.scrollHeight);"
                )
                _sleep_or_stop(1)
                if not _click_next_page(driver, stop_flag=stop_flag):
                    # 다음 페이지 없음 — 수집 종료
                    break
                # 페이지 로딩 대기 (stop_flag 체크)
                _sleep_or_stop(3)
                # 새 페이지 로딩 후 업체 항목 대기 — 0.5초씩 폴링하며 stop_flag 체크
                for _ in range(20):
                    if stop_flag():
                        raise InterruptedError("중단됨")
                    if driver.find_elements(By.CSS_SELECTOR, ITEM_SEL):
                        break
                    time.sleep(0.5)
                _sleep_or_stop(1)
            else:
                # 스크롤로 새 항목 로드됐지만 목표치 이미 달성했으면 다음 페이지 불필요
                if len(results) >= count:
                    break

    except InterruptedError:
        raise
    except Exception as e:
        if on_progress:
            try:
                on_progress(len(results), scanned, f"오류: {e}", results)
            except Exception:
                pass
    finally:
        # 0개 '새로' 수집 시 디버그 덤프 (기존 existing_places 제외)
        _base_count = len(list(existing_places or []))
        if len(results) <= _base_count:
            try:
                import tempfile, datetime as _dt
                _dir = os.path.join(tempfile.gettempdir(), "crawl_debug")
                os.makedirs(_dir, exist_ok=True)
                _ts = _dt.datetime.now().strftime("%H%M%S")
                _safe_kw = re.sub(r"[^가-힣A-Za-z0-9_]", "_", keyword)[:30]
                _base = os.path.join(_dir, f"{_ts}_{_safe_kw}")
                try: driver.switch_to.default_content()
                except Exception: pass
                try:
                    with open(_base + ".html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                except Exception: pass
                try: driver.save_screenshot(_base + ".png")
                except Exception: pass
                try:
                    driver.switch_to.frame("searchIframe")
                    with open(_base + "_iframe.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    driver.switch_to.default_content()
                except Exception: pass
                print(f"[DEBUG DUMP] {_base}", flush=True)
            except Exception:
                pass
        if _own_driver:
            try: driver.quit()
            except Exception: pass

    # 헤드리스 모드에서 0개 수집 → 봇 감지 의심, 크롬창 띄워서 재시도
    if not results and _own_driver and not force_visible:
        if emit_log:
            emit_log("<span style='color:#f59e0b'>⚠️ 수집결과 0개 — 네이버의 봇감지 차단으로 인해 크롬창 띄웁니다</span>")
        return crawl_places(keyword, count, on_progress,
                            existing_places=existing_places,
                            exclude_keywords=exclude_keywords,
                            driver=None,
                            on_item=on_item,
                            direct_url=direct_url,
                            no_filter=no_filter,
                            stop_flag=stop_flag,
                            profile_dir=profile_dir,
                            emit_log=emit_log,
                            force_visible=True)

    return results


_stations_cache = None

def _get_stations() -> list:
    global _stations_cache
    if _stations_cache is None:
        stations_file = os.path.join(os.path.dirname(__file__), "stations.json")
        try:
            with open(stations_file, "r", encoding="utf-8") as f:
                _stations_cache = json.load(f)
        except Exception:
            _stations_cache = []
    return _stations_cache


def _click_next_page(driver, stop_flag=lambda: False) -> bool:
    try:
        result = driver.execute_script("""
            // 페이지 번호 버튼들 찾기
            let pages = document.querySelectorAll('.zRM9F a, [class*="paginator"] a');
            let currentNum = 0;

            // 현재 페이지 번호 찾기
            for(let p of pages) {
                if(p.getAttribute('aria-current') === 'page' || p.classList.contains('OxGdy')) {
                    currentNum = parseInt(p.textContent.trim());
                    break;
                }
            }

            // 다음 페이지 번호 클릭
            if(currentNum > 0) {
                for(let p of pages) {
                    let num = parseInt(p.textContent.trim());
                    if(num === currentNum + 1) {
                        p.click();
                        return true;
                    }
                }
            }

            // "다음" 버튼 클릭
            for(let p of pages) {
                let label = p.getAttribute('aria-label') || p.textContent || '';
                if(label.includes('다음') && p.getAttribute('aria-disabled') !== 'true') {
                    p.click();
                    return true;
                }
            }

            return false;
        """)
        if result:
            # stop_flag 체크하면서 3초 대기
            end = time.time() + 3
            while time.time() < end:
                if stop_flag():
                    raise InterruptedError("중단됨")
                time.sleep(0.2)
        return bool(result)
    except InterruptedError:
        raise
    except Exception:
        return False


def _extract_dong(address: str) -> str:
    if not address:
        return ""
    match = re.search(r"[구군]\s+(\S+동)\b", address)
    if match:
        return match.group(1)
    return ""


def _dedup(items: list) -> str:
    """중복 제거 후 쉼표로 합침"""
    seen = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return ",".join(seen)


def _generate_front_keywords(area: str, biz_type: str, dong: str) -> str:
    kw = []
    if area and biz_type:
        kw.append(f"{area}{biz_type}")
    if dong:
        kw.append(dong)
    return _dedup(kw)


def _generate_tags(dong: str, biz_type: str, area: str, station: str = "") -> str:
    tags = []
    if dong and biz_type:
        tags.append(f"{dong}{biz_type}")
    if area and biz_type:
        tags.append(f"{area}{biz_type}")
    if station and biz_type:
        station_clean = station[:-1] if station.endswith("역") else station
        tags.append(f"{station_clean}{biz_type}")
        tags.append(f"{station}{biz_type}")
    return _dedup(tags)


def _generate_pixabay_keywords(area: str, biz_type: str, dong: str) -> str:
    kw = []
    if area and biz_type:
        kw.append(f"{area}{biz_type}")
    if dong and biz_type:
        kw.append(f"{dong}{biz_type}")
    return _dedup(kw) if kw else biz_type


def save_results(results: list[dict], filepath: str, keyword: str = ""):
    data = {"keyword": keyword, "items": results}
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_results(filepath: str) -> dict:
    """{'keyword': str, 'items': list} 반환. 구버전 호환."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"keyword": "", "items": data}
    return data
