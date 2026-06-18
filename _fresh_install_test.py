# -*- coding: utf-8 -*-
"""신규 설치 시뮬레이션 — config.json 없는 상태에서 load_config() 가 Firebase에서 accounts 가져오는지 검증"""
import sys, os, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as _cfg

# CONFIG_FILE을 존재하지 않는 경로로 monkey-patch (신규 설치 시뮬레이션)
fake_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_nonexistent_config.json")
if os.path.exists(fake_path):
    os.remove(fake_path)
original = _cfg.CONFIG_FILE
_cfg.CONFIG_FILE = fake_path
print(f"[1] CONFIG_FILE monkey-patched to non-existent: {fake_path}")
print(f"[1] exists? {os.path.exists(fake_path)}")

for test_user in ["kidth1", "admin"]:
    print(f"\n=== {test_user} 로그인 시뮬레이션 ===")
    _cfg.set_current_user(test_user)
    print(f"  current_user={_cfg.get_current_user()}")
    try:
        cfg = _cfg.load_config()
        accounts = cfg.get("accounts", [])
        non_empty = [a for a in accounts if (a.get("naver_id") or "").strip()]
        print(f"  accounts 총 {len(accounts)}개, 데이터 있는 것 {len(non_empty)}개")
        for i, a in enumerate(accounts):
            nid = a.get("naver_id", "")
            bid = a.get("blog_id", "")
            cat = a.get("blog_category", "")
            mark = "✅" if nid else "  "
            print(f"  {mark} [{i}] naver_id={nid!r:25} blog_id={bid!r:25} cat={cat!r}")
        # API 키 확인
        for kn in _cfg.API_KEY_FIELDS:
            v = cfg.get(kn, [])
            if v:
                first = (v[0] or "")[:20] + "..." if v[0] else ""
                print(f"  {kn}: {len(v)}개 / first={first!r}")

        # 판정
        if test_user == "kidth1":
            if len(non_empty) >= 6:
                print(f"  ✅ 성공 — kidth1 계정 6개 이상 Firebase에서 가져옴")
            else:
                print(f"  ❌ 실패 — kidth1 계정 부족 ({len(non_empty)}개)")
    except Exception as e:
        import traceback
        print(f"  ❌ 예외: {e}")
        traceback.print_exc()

# 복구
_cfg.CONFIG_FILE = original
print(f"\n[복구] CONFIG_FILE → {original}")
