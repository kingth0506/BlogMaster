# -*- coding: utf-8 -*-
"""10개 키워드 × 100장 픽사베이 추출 → 바탕화면 폴더 저장 (중복제거 OFF 검증용)."""
import json, os, sys, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import image_handler as ih

io = open(1, "w", encoding="utf-8")
def p(*a): print(*a, file=io, flush=True)

OUT = r"C:\Mac\Home\Desktop\픽사베이_100장_테스트"
KWS = ["요양원", "헬스장", "미용실", "치과", "카페",
       "변호사", "필라테스", "동물병원", "네일샵", "펜션"]
PER_KW = 100

users = json.load(open("users.json", encoding="utf-8"))
KEY = ""
for name, u in users.items():
    ks = [k for k in ((u.get("api_keys") or {}).get("pixabay_key_list") or []) if k]
    if ks:
        KEY = ks[0]; break
assert KEY, "픽사베이 키 없음"

def collect(kw):
    """tag_filter 통과한 고유 hit을 PER_KW장까지 수집 (중복제거 set 미사용)."""
    qs = ih._get_en_queries(kw) or [kw]
    tf = ih._tag_filter_for(kw)
    tx = ih._tag_exclude_for(kw)
    seen, hits = set(), []
    for q in qs:
        for page in range(1, 7):
            hs = ih._fetch_hits(KEY, q, page=page, per_page=200)
            if not hs:
                break
            for h in hs:
                hid = h.get("id")
                if hid in seen:
                    continue
                tags = (h.get("tags") or "").lower()
                if tx and any(t in tags for t in tx):
                    continue
                if tf and not any(t in tags for t in tf):
                    continue
                seen.add(hid); hits.append(h)
            if len(hits) >= PER_KW:
                break
        if len(hits) >= PER_KW:
            break
    return hits[:PER_KW]

def download(kw, idx, h):
    folder = os.path.join(OUT, kw)
    url = h.get("webformatURL") or h.get("largeImageURL")
    try:
        r = requests.get(url, timeout=30); r.raise_for_status()
        with open(os.path.join(folder, f"{idx:03d}_{h.get('id')}.jpg"), "wb") as f:
            f.write(r.content)
        return True
    except Exception:
        return False

# 1) 수집
jobs = []
plan = {}
for kw in KWS:
    hits = collect(kw)
    plan[kw] = len(hits)
    os.makedirs(os.path.join(OUT, kw), exist_ok=True)
    for i, h in enumerate(hits, 1):
        jobs.append((kw, i, h))
    p(f"[수집] {kw:8s} 필터통과 고유이미지 {len(hits)}장")

p(f"--- 총 {len(jobs)}장 다운로드 시작 ---")

# 2) 병렬 다운로드
ok = {kw: 0 for kw in KWS}
with ThreadPoolExecutor(max_workers=16) as ex:
    futs = {ex.submit(download, kw, i, h): kw for (kw, i, h) in jobs}
    done = 0
    for f in as_completed(futs):
        done += 1
        if f.result():
            ok[futs[f]] += 1
        if done % 100 == 0:
            p(f"  ...{done}/{len(jobs)} 다운로드됨")

p("=== 최종 결과 (폴더별 저장 장수) ===")
for kw in KWS:
    p(f"  {kw:8s} 수집 {plan[kw]:3d}장 → 저장 {ok[kw]:3d}장")
p(f"저장 위치: {OUT}")
