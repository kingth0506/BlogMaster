# -*- coding: utf-8 -*-
"""세션 jsonl → 바탕화면 txt (모든 user/assistant 메시지 원문 보존)"""
import json
import os
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SRC = r"C:/Users/kidth/.claude/projects/C--Users-kidth/a2184f9b-0bb8-4b3d-838c-111ba319dca5.jsonl"
DST = r"C:/Users/kidth/OneDrive/Desktop/블로그마스터422/블로그마스터_대화전체_원문.txt"

def _flatten_content(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for item in c:
            if isinstance(item, dict):
                t = item.get("type")
                if t == "text":
                    parts.append(item.get("text", ""))
                elif t == "tool_use":
                    inp = item.get("input", {})
                    parts.append(f"[TOOL_USE {item.get('name','')}] {json.dumps(inp, ensure_ascii=False)[:2000]}")
                elif t == "tool_result":
                    content = item.get("content", "")
                    if isinstance(content, list):
                        content = "\n".join(_flatten_content(x) for x in content)
                    parts.append(f"[TOOL_RESULT] {str(content)[:5000]}")
                elif t == "thinking":
                    parts.append(f"[THINKING] {item.get('thinking','')}")
                elif t == "image":
                    parts.append("[IMAGE]")
                else:
                    parts.append(f"[{t}]")
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(c)


def main():
    if not os.path.exists(SRC):
        print("jsonl not found")
        return
    lines = []
    with open(SRC, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            try:
                o = json.loads(raw)
            except Exception:
                continue
            t = o.get("type")
            if t == "user":
                msg = o.get("message", {}) or {}
                c = _flatten_content(msg.get("content", ""))
                lines.append(f"=== [사용자] ===\n{c}\n")
            elif t == "assistant":
                msg = o.get("message", {}) or {}
                c = _flatten_content(msg.get("content", ""))
                lines.append(f"=== [Claude] ===\n{c}\n")
            elif t == "system":
                pass  # 시스템 리마인더는 스킵 (너무 많아서)
    with open(DST, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"저장 완료: {DST} ({os.path.getsize(DST)//1024} KB, 메시지 {len(lines)}개)")

if __name__ == "__main__":
    main()
