# -*- coding: utf-8 -*-
"""네이버 지도 크롤링 모듈 — 모바일 검색(requests) 엔진 + 레거시 Selenium 유틸"""
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
import random as _random

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


# ──────────────────────────────────────────────────────────────────────────
# Throttle(차단) 우회 정책 — 기획서 반영
#   대책1) 구 개수가 많을수록 동시 봇을 낮춰 차단을 회피한다.
#   대책2) 후반부에 '딱 N개'에서 잘린 구(차단 의심)만 마지막에 순차 재시도한다.
# ──────────────────────────────────────────────────────────────────────────
THROTTLE_DISTRICT_THRESHOLD = 10   # 구가 이 개수 이상이면 봇을 안전값으로 자동 하향
THROTTLE_SAFE_WORKERS = 2          # 자동 하향 시 적용할 안전 봇 수 (서울 25구 무손실 검증값)
STRAGGLER_TRIP_COUNT = 5           # 구별 수집이 '딱 이 개수'에서 멈추면 차단 의심으로 판정
STRAGGLER_RETRY_DELAY = (2.0, 4.0) # 스트래글러 순차 재시도 사이 텀(초) — 차단 풀릴 시간 확보


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
                           profile_dir: str = None,
                           auto_throttle: bool = True,
                           straggler_retry: bool = True):
    """여러 지역 키워드를 N개 단위 배치로 병렬 크롤 (requests 기반).

    Throttle(차단) 우회 — 기획서 반영:
      auto_throttle=True   : 구가 THROTTLE_DISTRICT_THRESHOLD개 이상이면
                             max_workers를 THROTTLE_SAFE_WORKERS(2봇)로 자동 하향.
      straggler_retry=True : 메인 크롤 종료 후 '딱 STRAGGLER_TRIP_COUNT개'에서
                             멈춘 차단 의심 구만 순차로 1회 더 재시도(복구).
    """
    import threading as _th
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from collections import Counter as _Counter

    keywords = list(keywords or [])
    if not keywords:
        return list(existing_places or [])

    # ── 대책1: 자동 봇 조절 ──────────────────────────────────────────────
    # 구(키워드)가 많을수록 누적 요청률이 높아져 후반부 throttle이 터진다.
    # 임계치 이상이면 설정값과 무관하게 안전 봇 수로 강제 하향한다.
    _requested_workers = max_workers
    if auto_throttle and len(keywords) >= THROTTLE_DISTRICT_THRESHOLD \
            and max_workers > THROTTLE_SAFE_WORKERS:
        max_workers = THROTTLE_SAFE_WORKERS
        emit_log(
            f"⚙️ [자동 봇조절] 구 {len(keywords)}개 ≥ {THROTTLE_DISTRICT_THRESHOLD}개 "
            f"→ throttle 회피 위해 {_requested_workers}봇 → {max_workers}봇으로 자동 하향"
        )

    max_workers = max(1, min(max_workers, len(keywords)))

    lock = _th.Lock()
    merged = list(existing_places or [])
    collected_names = set((p.get("name") or "").strip() for p in merged if p.get("name"))

    import queue as _q
    kq = _q.Queue()
    for kw in keywords:
        kq.put(kw)

    def _worker_loop(worker_idx):
        import time as _t
        if worker_idx > 0:
            _stagger = worker_idx * 2
            emit_log(f"  [봇{worker_idx+1}] {_stagger}초 후 시작 (동시 요청 분산)")
            _end = _t.time() + _stagger
            while _t.time() < _end:
                if stop_flag():
                    return
                _t.sleep(0.2)

        while True:
            if stop_flag():
                break
            try:
                kw = kq.get_nowait()
            except _q.Empty:
                break
            try:
                def _tagged_progress(cur, scanned, name, results_ref=None, _w=worker_idx):
                    if on_progress:
                        on_progress(cur, scanned, f"[봇{_w+1}] {name}", results_ref)

                emit_log(f"  [봇{worker_idx+1}] {kw} 크롤 시작")
                _kw_existing = list((existing_by_keyword or {}).get(kw, []))
                r = crawl_places(
                    kw,
                    count_per,
                    _tagged_progress,
                    existing_places=_kw_existing,
                    exclude_keywords=exclude_keywords,
                    no_filter=no_filter,
                    on_item=on_item,
                    stop_flag=stop_flag,
                    emit_log=emit_log,
                )
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
                    try:
                        save_batch(snapshot, kw, list(r))
                    except TypeError:
                        save_batch(snapshot)
                except Exception as e:
                    emit_log(f"저장 실패: {e}")
            except Exception as e:
                emit_log(f"  [봇{worker_idx+1}] {kw} 실패 ({str(e)[:60]})")

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_worker_loop, i) for i in range(max_workers)]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                emit_log(f"봇 예외: {e}")

    # ── 대책2: 스트래글러(차단 의심 구) 순차 재시도 ──────────────────────
    # 메인 병렬 크롤이 끝난 뒤, 후반 throttle로 '딱 STRAGGLER_TRIP_COUNT개'에서
    # 잘려 멈춘 구들만 골라 단일 스레드로 텀을 두고 1회 더 복구 시도한다.
    if straggler_retry and not stop_flag():
        _by_kw = _Counter()
        for _p in merged:
            _k = (_p.get("search_keyword") or "").strip()
            if _k:
                _by_kw[_k] += 1

        # '딱 N개'에서 멈춘 구만 차단 의심으로 본다.
        # (목표치 자체가 N 이하면 정상 수집이므로 제외한다.)
        suspects = [
            kw for kw in keywords
            if _by_kw.get(kw, 0) == STRAGGLER_TRIP_COUNT and count_per > STRAGGLER_TRIP_COUNT
        ]

        if suspects:
            emit_log(
                f"🔁 [스트래글러 복구] 차단 의심 구 {len(suspects)}개 "
                f"(딱 {STRAGGLER_TRIP_COUNT}개에서 멈춤) 순차 재시도: {', '.join(suspects)}"
            )
            for kw in suspects:
                if stop_flag():
                    break
                # 차단이 풀릴 시간을 벌기 위해 재시도 사이에 텀을 둔다.
                _delay_end = time.time() + _random.uniform(*STRAGGLER_RETRY_DELAY)
                while time.time() < _delay_end:
                    if stop_flag():
                        break
                    time.sleep(0.2)
                if stop_flag():
                    break

                _before = _by_kw.get(kw, 0)
                # 이미 잡힌 N개는 existing으로 넘겨 이어서 더 긁는다(중복 방지).
                with lock:
                    _kw_existing = [p for p in merged if (p.get("search_keyword") or "").strip() == kw]
                try:
                    emit_log(f"  [복구] {kw} 재시도 (현재 {_before}개)")
                    r = crawl_places(
                        kw,
                        count_per,
                        on_progress,
                        existing_places=list(_kw_existing),
                        exclude_keywords=exclude_keywords,
                        no_filter=no_filter,
                        on_item=on_item,
                        stop_flag=stop_flag,
                        emit_log=emit_log,
                    )
                    recovered = 0
                    with lock:
                        for p in r:
                            n = (p.get("name") or "").strip()
                            if n and n not in collected_names:
                                collected_names.add(n)
                                p["search_keyword"] = kw
                                merged.append(p)
                                recovered += 1
                    _by_kw[kw] = _before + recovered
                    emit_log(
                        f"  [복구] {kw}: {_before}개 → {_before + recovered}개 "
                        f"(복구 +{recovered}{' ⚠️여전히 차단 의심' if recovered == 0 else ' ✅'})"
                    )
                    try:
                        with lock:
                            snapshot = list(merged)
                        try:
                            save_batch(snapshot, kw, list(r))
                        except TypeError:
                            save_batch(snapshot)
                    except Exception as e:
                        emit_log(f"저장 실패: {e}")
                except Exception as e:
                    emit_log(f"  [복구] {kw} 재시도 실패 ({str(e)[:60]})")
        else:
            emit_log(f"🔁 [스트래글러 복구] 차단 의심 구 없음 — 전 구 정상 수집 ✅")

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
                 "Service Worker", "IndexedDB", "databases",
                 "Crashpad", "BrowserMetrics", "BrowserMetrics-spare.pma",
                 "LOCK", "*.log", "*.ldb", "*.sst"}
        def _safe_copy(src, dst):
            try:
                _sh.copy2(src, dst)
            except (PermissionError, OSError):
                pass  # 잠긴 파일 무시
        try:
            _sh.copytree(src_default, dst_default,
                         ignore=_sh.ignore_patterns(*_SKIP),
                         copy_function=_safe_copy)
        except _sh.Error:
            pass  # 일부 파일 복사 실패해도 계속 (부분 복사 상태로 사용)
        except Exception:
            pass
        os.makedirs(dst_default, exist_ok=True)
    else:
        os.makedirs(dst_default, exist_ok=True)
    return dst


def login_for_crawl(naver_id: str, naver_pw: str, profile_dir: str, emit_log=None) -> bool:
    """naver_id/pw로 로그인 후 profile_dir에 세션 저장. 성공 True, 실패 False."""
    from selenium.webdriver.common.by import By as _By
    from selenium.webdriver.support.ui import WebDriverWait as _WDW
    from selenium.webdriver.support import expected_conditions as _EC
    import time as _t

    os.makedirs(profile_dir, exist_ok=True)
    driver = None
    try:
        for _lk in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
            _lp = os.path.join(profile_dir, _lk)
            if os.path.exists(_lp):
                try: os.remove(_lp)
                except: pass
        _o = Options()
        _o.add_argument(f"--user-data-dir={profile_dir}")
        _o.add_argument("--window-size=1920,1080")
        _o.add_argument("--no-sandbox")
        _o.add_argument("--disable-gpu")
        _o.add_argument("--disable-dev-shm-usage")
        _o.add_argument("--disable-blink-features=AutomationControlled")
        _o.add_experimental_option("excludeSwitches", ["enable-automation"])
        service = Service(_get_driver_path())
        driver = webdriver.Chrome(service=service, options=_o)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })

        # 기존 세션 확인
        driver.get("https://www.naver.com")
        _t.sleep(2)
        try:
            driver.find_element(_By.CSS_SELECTOR, "a[href*='logout']")
            if emit_log: emit_log(f"[{naver_id}] 기존 로그인 세션 확인")
            return True
        except Exception:
            pass

        # 로그인 진행
        driver.get("https://nid.naver.com/nidlogin.login")
        _WDW(driver, 10).until(_EC.presence_of_element_located((_By.ID, "id")))
        _t.sleep(0.5)
        driver.execute_script(
            "const i=document.getElementById('id'),p=document.getElementById('pw'),"
            "s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
            "s.call(i,arguments[0]);i.dispatchEvent(new Event('input',{bubbles:true}));"
            "s.call(p,arguments[1]);p.dispatchEvent(new Event('input',{bubbles:true}));",
            naver_id, naver_pw
        )
        _t.sleep(0.3)
        _WDW(driver, 5).until(_EC.presence_of_element_located((_By.ID, "log.login"))).click()
        _t.sleep(2)

        # 새 기기 등록 처리
        try:
            btn = driver.find_element(_By.CSS_SELECTOR, "button.btn_cancel, button[class*='confirm'], a[class*='btn_confirm']")
            if btn.is_displayed():
                btn.click()
                _t.sleep(1)
        except Exception:
            pass

        # 로그인 확인 (최대 60초 — 캡챠 수동 처리 포함)
        try:
            _WDW(driver, 60).until(lambda d: "nid.naver.com" not in d.current_url)
            if emit_log: emit_log(f"[{naver_id}] 로그인 성공")
            _t.sleep(1)
            return True
        except Exception:
            if emit_log: emit_log(f"[{naver_id}] 로그인 실패 (시간 초과)")
            return False

    except Exception as e:
        if emit_log: emit_log(f"[{naver_id}] 로그인 오류: {e}")
        return False
    finally:
        try:
            if driver: driver.quit()
        except Exception:
            pass


def _make_driver(user_agent: str = None, browser: str = "chrome", profile_dir: str = None, headless: bool = True):
    """새 드라이버 생성 (병렬 워커용). browser='chrome' | 'edge'
    profile_dir 있으면 undetected_chromedriver + 로그인 세션 사용.
    profile_dir 없으면 undetected_chromedriver + selenium-stealth 적용."""
    import random as _rnd
    import os as _os

    _visible = _os.environ.get("CRAWL_VISIBLE") or not headless

    # 로그인 프로필 모드 — 일반 Selenium + profile_dir (uc 버전 충돌 우회)
    if profile_dir:
        for _lk in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
            _lp = os.path.join(profile_dir, _lk)
            if os.path.exists(_lp):
                try: os.remove(_lp)
                except: pass
        try:
            _lp = os.path.join(profile_dir, "Default", "LOCK")
            if os.path.exists(_lp): os.remove(_lp)
        except: pass
        try:
            _o = Options()
            _o.add_argument(f"--user-data-dir={profile_dir}")
            _o.add_argument("--window-size=1920,1080")
            _o.add_argument("--no-sandbox")
            _o.add_argument("--disable-gpu")
            _o.add_argument("--disable-dev-shm-usage")
            _o.add_argument("--disable-extensions")
            _o.add_argument("--mute-audio")
            _o.add_argument("--disable-background-networking")
            _o.add_argument("--disable-default-apps")
            _o.add_argument("--disable-sync")
            _o.add_argument("--disable-blink-features=AutomationControlled")
            _o.add_argument("--disable-features=AudioServiceOutOfProcess,TranslateUI")
            if not _visible:
                _o.add_argument("--headless")
            _o.add_experimental_option("excludeSwitches", ["enable-automation"])
            _svc = Service(_get_driver_path())
            _d = webdriver.Chrome(service=_svc, options=_o)
            _d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            })
            return _d
        except Exception:
            pass

    # 비로그인 모드 — undetected_chromedriver + selenium-stealth
    try:
        import undetected_chromedriver as _uc
        from selenium_stealth import stealth
        _o = _uc.ChromeOptions()
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
        ua = user_agent or _rnd.choice(_UA_POOL)
        _o.add_argument(f"user-agent={ua}")
        with _uc_create_lock:
            d = _uc.Chrome(options=_o, headless=False if _visible else headless)
        stealth(d,
            languages=["ko-KR", "ko"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)
        return d
    except Exception:
        pass  # selenium-stealth 또는 uc 실패 → 일반 드라이버로 fallback

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

    if _visible:
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
                 force_visible: bool = False,
                 with_station: bool = True,
                 station_delay: float = 0.8) -> list[dict]:
    """네이버 모바일 검색에서 키워드로 업체 크롤링 (requests + BeautifulSoup).

    existing_places가 주어지면 그 업체들은 스킵하고 이어서 크롤 (재개 모드).
    exclude_keywords 중 하나라도 업체명/카테고리/주소에 포함되면 제외.
    driver/profile_dir/force_visible 인자는 하위 호환용으로 남겨 두며 사용하지 않는다.
    no_filter=True 시 업종/지역 필터 미적용 (키워드 기반 전체 수집)."""
    from naver_crawler import fetch_all_places, fetch_nearby_station, resolve_nearby_station

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

    results = list(existing_places or [])
    collected_names = set()
    for _p in results:
        _n = (_p.get("name") or "").strip()
        if _n:
            collected_names.add(_n)
    scanned = 0
    for _i, _p in enumerate(results, start=1):
        _p["index"] = _i

    remaining = max(0, count - len(results))
    if remaining <= 0:
        return results

    try:
        if stop_flag():
            raise InterruptedError("중단됨")
        if emit_log:
            emit_log(f"모바일 검색 크롤: {keyword} (목표 {remaining}개 추가)")

        # 필터로 걸러질 수 있으므로 여유 있게 더 요청
        fetch_target = remaining + (remaining // 2) + 10
        raw_items = fetch_all_places(
            keyword,
            count=fetch_target,
            stop_flag=stop_flag,
            emit_log=emit_log,
        )

        if not raw_items and emit_log:
            emit_log("<span style='color:#f59e0b'>⚠️ 수집결과 0개 — 모바일 검색 응답 없음 또는 차단</span>")

        for raw in raw_items:
            if stop_flag():
                raise InterruptedError("중단됨")
            if len(results) >= count:
                break

            name = (raw.get("name") or "").strip()
            if not name or name in collected_names:
                continue

            category = (raw.get("category") or "").strip()
            short_addr = (raw.get("address") or "").strip()
            jibun_addr = (raw.get("jibun_address") or "").strip()
            dong = (raw.get("동") or raw.get("dong") or "").strip() or _extract_dong(jibun_addr or short_addr)
            si = (raw.get("시") or "").strip()
            gu = (raw.get("구") or "").strip()
            nearby_station = (raw.get("nearby_station") or "").strip()
            place_id = (raw.get("place_id") or "").strip()
            px, py = raw.get("x"), raw.get("y")

            scanned += 1

            if exclude_keywords and any(ex in f"{name} {category}" for ex in exclude_keywords):
                collected_names.add(name)
                continue

            haystack = f"{name} {category} {short_addr} {jibun_addr}"
            if not _url_mode and area_filter and area_filter not in haystack:
                collected_names.add(name)
                continue

            # 업종(카테고리) 자동 탈락은 하지 않는다.
            # 정책: 검색 지역에서 나온 업체는 '다 수집'하고, 불필요한 건 2차(제외 키워드)로만 삭제.
            # (예: 헬스장 검색 시 '스포츠시설'로 분류된 PT/짐도 대부분 헬스장이므로 버리지 않음)

            if exclude_keywords and any(ex in haystack for ex in exclude_keywords):
                collected_names.add(name)
                continue

            # 근처 역 — 이름추출 + 좌표 최단거리 하이브리드 (요청 0, 즉시)
            station_info = {}
            if with_station:
                station_info = resolve_nearby_station(name, px, py)
                if station_info.get("station"):
                    nearby_station = station_info["station"]

            _st_dist = station_info.get("distance_m")
            _st_text = ""
            if station_info.get("station"):
                _st_text = nearby_station + (f" 약 {_st_dist}m" if _st_dist else "")

            place = {
                "index": len(results) + 1,
                "name": name,
                "address": short_addr,
                "jibun_address": jibun_addr,
                "category": category,
                "category_2": "",
                "nearby_station": nearby_station,
                "nearby_station_distance": _st_dist if _st_dist else "",
                "nearby_station_text": _st_text,
                "nearby_station_source": station_info.get("source", ""),
                "front_keywords": _generate_front_keywords(area_filter, biz_type, dong),
                "tags": _generate_tags(dong, biz_type, area_filter, nearby_station),
                "pixabay_keywords": _generate_pixabay_keywords(area_filter, biz_type, dong),
                "dong": dong,
                "시": si,
                "구": gu,
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
    except Exception as e:
        if on_progress:
            try:
                on_progress(len(results), scanned, f"오류: {e}", results)
            except Exception:
                pass
        if emit_log:
            emit_log(f"크롤 오류: {e}")

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


def _click_next_page(driver, stop_flag=lambda: False, current_page: int = 0) -> bool:
    """ActionChains 실제 마우스 클릭으로 다음 페이지 이동 (JS 직접 click 봇감지 회피)."""
    from selenium.webdriver.common.action_chains import ActionChains
    try:
        next_num = str(current_page + 1) if current_page > 0 else None
        SEL = "a, button, span[role], li[role], div[role='button'], span[role='button']"
        candidates = driver.find_elements(By.CSS_SELECTOR, SEL)

        def _ac_click(el):
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'nearest'});", el)
                time.sleep(0.2)
            except Exception:
                pass
            ActionChains(driver).move_to_element(el).pause(_random.uniform(0.1, 0.3)).click().perform()

        # 1) JS — 조상 5단계까지 올라가며 숫자 3개 이상인 컨테이너 찾아 페이지 번호 클릭
        if next_num:
            try:
                result = driver.execute_script("""
                    var nextTxt = arguments[0];
                    var all = Array.from(document.querySelectorAll('a,button,span,li,div'))
                        .filter(function(el) { return (el.textContent||'').trim() === nextTxt; });
                    for (var i = 0; i < all.length; i++) {
                        var el = all[i];
                        var ancestor = el.parentNode;
                        for (var d = 0; d < 5 && ancestor; d++) {
                            var numDesc = Array.from(ancestor.querySelectorAll('*'))
                                .filter(function(c) { return /^\\d+$/.test((c.textContent||'').trim()); });
                            if (numDesc.length >= 3) {
                                el.scrollIntoView({block:'nearest'});
                                el.click();
                                return 'pg:' + nextTxt;
                            }
                            ancestor = ancestor.parentNode;
                        }
                    }
                    return null;
                """, next_num)
                if result:
                    time.sleep(_random.uniform(0.4, 0.7))
                    return result
            except Exception:
                pass

        # 2) > 화살표 버튼 (페이지네이션 영역 내 화살표 문자 or aria-label)
        try:
            result = driver.execute_script("""
                var arrows = ['>', '›', '▶', '»', '→'];
                var all = Array.from(document.querySelectorAll('a,button,span,li,div'));
                for (var i = 0; i < all.length; i++) {
                    var el = all[i];
                    var txt = (el.textContent || '').trim();
                    var label = (el.getAttribute('aria-label') || '').trim();
                    var disabled = el.getAttribute('aria-disabled') === 'true' || el.hasAttribute('disabled');
                    if (disabled) continue;
                    if (label === '다음' || label === '다음 페이지' || label === 'next') {
                        el.scrollIntoView({block:'nearest'});
                        el.click();
                        return 'arrow:label';
                    }
                    if (arrows.indexOf(txt) !== -1) {
                        var p = el.parentNode;
                        for (var d = 0; d < 4 && p; d++) {
                            var nums = Array.from(p.querySelectorAll('*'))
                                .filter(function(c) { return /^\\d+$/.test((c.textContent||'').trim()); });
                            if (nums.length >= 2) {
                                el.scrollIntoView({block:'nearest'});
                                el.click();
                                return 'arrow:' + txt;
                            }
                            p = p.parentNode;
                        }
                    }
                }
                return null;
            """)
            if result:
                time.sleep(_random.uniform(0.4, 0.7))
                return result
        except Exception:
            pass

        # 3) "다음" 텍스트 버튼
        try:
            result = driver.execute_script("""
                var all = document.querySelectorAll('a,button,span,li,div');
                for (var i = 0; i < all.length; i++) {
                    var el = all[i];
                    var txt = (el.textContent || '').trim();
                    var label = (el.getAttribute('aria-label') || '').trim();
                    var disabled = el.getAttribute('aria-disabled') === 'true' || el.hasAttribute('disabled');
                    if (!disabled && (txt === '다음' || txt === '다음 페이지' || label === '다음' || label === '다음 페이지')) {
                        el.scrollIntoView({block:'nearest'});
                        el.click();
                        return 'next-btn';
                    }
                }
                return null;
            """)
            if result:
                time.sleep(_random.uniform(0.4, 0.7))
                return result
        except Exception:
            pass

        # 4) ActionChains fallback — 번호 버튼
        if next_num:
            SEL = "a, button, span[role], li[role], div[role='button'], span[role='button']"
            candidates = driver.find_elements(By.CSS_SELECTOR, SEL)
            for el in candidates:
                try:
                    txt = (el.text or "").strip()
                    if txt == next_num:
                        try: displayed = el.is_displayed()
                        except: displayed = True
                        if displayed:
                            _ac_click(el)
                            time.sleep(_random.uniform(0.3, 0.6))
                            return f"num:{next_num}"
                except Exception:
                    continue

        return False
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
    """{'keyword': str, 'items': list} 반환. 구버전 호환.
    파일이 비정상적으로 크거나(폭주) 깨졌으면 백업 후 빈 결과 반환 — 앱이 멈추지 않음."""
    import os as _os
    empty = {"keyword": "", "items": []}
    try:
        if _os.path.getsize(filepath) > 80 * 1024 * 1024:  # 80MB 초과 = 비정상
            try:
                _os.replace(filepath, filepath + ".corrupt.bak")
            except Exception:
                pass
            return empty
    except Exception:
        pass
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        try:
            _os.replace(filepath, filepath + ".corrupt.bak")
        except Exception:
            pass
        return empty
    if isinstance(data, list):
        return {"keyword": "", "items": data}
    return data if isinstance(data, dict) else empty
