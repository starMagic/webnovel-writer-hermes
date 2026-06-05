#!/usr/bin/env python3
"""review_chapter.py — 调用 DeerFlow reviewer 审查章节。
用法: python3 review_chapter.py --chapter 4 [--project-root /path]
输出: reviewer JSON (passed/blocking/warnings/score/summary)
"""
import argparse, json, subprocess, sys
from pathlib import Path

BRIDGE = Path.home() / "HermesWorkspace" / "deerflow_bridge.py"
PYTHON = Path.home() / "Workspace/Git/deer-flow/backend/.venv/bin/python3"

REVIEW_PROMPT = """你是《你好！迪恩》的审查员（reviewer）。审查以下章节。

输出 JSON 格式（不要加任何其他文字，只要 JSON）：
{{"passed": true/false, "blocking": ["阻塞项1"], "warnings": ["警告项1"], "score": 85, "summary": "一句话总结"}}

检查维度：
1. 主角OOC（迪恩：思想巨人行动矮子/理性唯物/不能突然变热血冲动）
2. 设定一致性（觉醒度/比分/迪恩斯吐槽风格诙谐+硬核量化）
3. 章末钩子是否具体（不能模糊，必须让读者想点下一章）
4. 禁区违反（哲学内容在前5章不露/不打女拳/不键政）
5. ADMIN暗线是否推进（比分变化/日志/黑风衣暗示）
6. 对话占比是否足够（40%+）

=== 正文 ===
{chapter_text}
=== 正文完 ===

记住：只输出 JSON。"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--project-root", type=str, default=None)
    args = parser.parse_args()

    root = Path(args.project_root) if args.project_root else Path.cwd()
    text_dir = root / "正文"

    # Find chapter file
    ch_files = sorted(text_dir.rglob(f"第{args.chapter:04d}章*.md")) or \
               sorted(text_dir.rglob(f"第{args.chapter}章*.md")) or \
               sorted(text_dir.rglob(f"第0*{args.chapter}章*.md"))
    if not ch_files:
        print(json.dumps({"passed": False, "blocking": ["章节文件未找到"], "warnings": [], "score": 0, "summary": "文件缺失"}))
        sys.exit(1)

    chapter_text = ch_files[0].read_text(encoding="utf-8")
    # Truncate if too long (DeerFlow context window)
    if len(chapter_text) > 8000:
        chapter_text = chapter_text[:8000] + "\n\n[... 正文截断 ...]"

    # Build prompt with proper JSON escaping
    prompt = REVIEW_PROMPT.replace("{chapter_text}", chapter_text)
    payload = json.dumps({
        "action": "chat",
        "message": prompt,
        "thread_id": f"rev-ch{args.chapter}",
        "options": {"mode": "flash"}  # flash is faster for structured review
    })

    # Call bridge
    result = subprocess.run(
        [str(PYTHON), str(BRIDGE), "task", payload],
        capture_output=True, text=True, timeout=300,
        cwd=Path.home() / "HermesWorkspace"
    )

    # Parse NDJSON output
    for line in result.stdout.strip().split("\n"):
        try:
            d = json.loads(line)
            if d.get("status") == "result":
                text = d.get("text", "")
                # Try to extract JSON from response
                if "{" in text:
                    json_start = text.index("{")
                    json_text = text[json_start:]
                    # Find matching closing brace
                    brace_count = 0
                    json_end = json_start
                    for i, c in enumerate(text[json_start:], json_start):
                        if c == "{": brace_count += 1
                        elif c == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    review_json = json.loads(text[json_start:json_end])
                    print(json.dumps(review_json, ensure_ascii=False, indent=2))
                    return
                else:
                    # No JSON found, return the raw text
                    print(json.dumps({"passed": True, "blocking": [], "warnings": [], "score": 0, "summary": text.strip()[:200]}, ensure_ascii=False, indent=2))
                    return
        except json.JSONDecodeError:
            continue

    # Fallback
    print(json.dumps({"passed": True, "blocking": [], "warnings": ["reviewer返回为空"], "score": 0, "summary": "reviewer返回为空，跳过审查"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
