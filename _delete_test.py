# -*- coding: utf-8 -*-
"""F8 전체삭제 로직 단독 테스트 — main.py의 _purge_places_from_logs 그대로 흉내."""
import sys, os, io, json, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LOG_DIR = "logs/kidth1"

# 백업 (테스트라 원본 보존)
BACKUP = "logs/kidth1_backup_before_delete_test"
if os.path.exists(LOG_DIR) and not os.path.exists(BACKUP):
    shutil.copytree(LOG_DIR, BACKUP)
    print(f"[백업] {BACKUP} 에 복사")

def place_key(p):
    return (p.get("name", ""), p.get("address", "") or p.get("jibun_address", ""))

# 1) 전체 로드
all_places = []
files = [f for f in os.listdir(LOG_DIR) if f.endswith(".json") and not f.startswith("._")]
print(f"\n[1] {len(files)}개 파일에서 places 로드")
for fn in files:
    fp = os.path.join(LOG_DIR, fn)
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", []) if isinstance(data, dict) else []
    print(f"  {fn}: {len(items)}개")
    all_places.extend(items)

print(f"\n전체 places: {len(all_places)}개")
keys = {place_key(p) for p in all_places}
print(f"고유 keys: {len(keys)}개 (예: {list(keys)[0] if keys else None})")

# 2) purge 시뮬레이션 (실제 파일 수정 없이 dry-run)
print(f"\n[2] purge 시뮬레이션 (dry-run)")
removed_total = 0
file_actions = []
for fn in files:
    fp = os.path.join(LOG_DIR, fn)
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", []) or []
    kept = [p for p in items if place_key(p) not in keys]
    diff = len(items) - len(kept)
    if diff == 0:
        file_actions.append((fn, "no_match", len(items)))
        continue
    removed_total += diff
    if not kept:
        file_actions.append((fn, "would_delete", len(items)))
    else:
        file_actions.append((fn, f"would_rewrite({len(items)}→{len(kept)})", diff))

for fn, action, n in file_actions:
    print(f"  {fn}: {action} ({n})")

print(f"\n총 제거 예정: {removed_total}개")

# 3) 검증 — 첫 번째 place의 key로 실제 매칭되는지 직접 확인
if all_places:
    sample = all_places[0]
    sk = place_key(sample)
    print(f"\n[3] 샘플 매칭 확인")
    print(f"  샘플 place: name={sample.get('name')!r}, address={sample.get('address')!r}, jibun={sample.get('jibun_address')!r}")
    print(f"  샘플 key: {sk}")
    print(f"  keys에 포함됨: {sk in keys}")

# 백업 복원 (테스트라 원본 손대지 않음)
print(f"\n[참고] 실제 파일은 변경 안 됨 (dry-run). 원본 그대로.")
