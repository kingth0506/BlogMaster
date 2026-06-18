# -*- coding: utf-8 -*-
"""세션 jsonl을 사람이 읽을 수 있는 txt로 변환 — 절대 truncate 안 함."""
import json, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = r"C:\Users\taehyunkim\.claude\projects\C--Users-taehyunkim\d17c3f8b-1291-4cb1-9424-4bc4df8baa93.jsonl"
DST_DIR = r"C:\Users\taehyunkim\Desktop\블로그마스터_v1.4.8"
DST = os.path.join(DST_DIR, "대화내용.txt")

os.makedirs(DST_DIR, exist_ok=True)

n_user = 0
n_assistant = 0
total = 0
with open(SRC, "r", encoding="utf-8") as f, open(DST, "w", encoding="utf-8") as out:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        total += 1
        msg = d.get("message", {}) or {}
        role = msg.get("role") or d.get("type", "")
        content = msg.get("content")

        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict):
                    if c.get("type") == "text":
                        parts.append(c.get("text", ""))
                    elif c.get("type") == "tool_use":
                        tn = c.get("name", "")
                        ti = c.get("input", {})
                        # truncate 없이 전체 저장
                        parts.append(f"[도구사용: {tn}] {json.dumps(ti, ensure_ascii=False)}")
                    elif c.get("type") == "tool_result":
                        ic = c.get("content")
                        if isinstance(ic, list):
                            ic = "\n".join([x.get("text", "") for x in ic if isinstance(x, dict)])
                        # truncate 없이 전체 저장
                        parts.append(f"[도구결과] {ic or ''}")
            text = "\n".join(parts)
        else:
            text = ""

        if role == "user":
            n_user += 1
            out.write(f"[유저]\n{text}\n\n")
        elif role == "assistant":
            n_assistant += 1
            out.write(f"[클로드]\n{text}\n\n")

print(f"총 {total} 메시지 / 유저 {n_user} / 클로드 {n_assistant}")
print(f"저장: {DST}")
print(f"크기: {os.path.getsize(DST):,} bytes")
