#!/usr/bin/env python3
"""context_agent.py — 调用 DeerFlow 生成写作任务书。
用法: python3 context_agent.py --chapter 4 [--project-root /path]
输出: 写作任务书纯文本
"""
import argparse, json, subprocess, sys
from pathlib import Path

BRIDGE = Path.home() / "HermesWorkspace" / "deerflow_bridge.py"
PYTHON = Path.home() / "Workspace/Git/deer-flow/backend/.venv/bin/python3"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--project-root", type=str, required=True)
    parser.add_argument("--mode", type=str, default="think")
    args = parser.parse_args()

    root = Path(args.project_root)
    outline_dir = root / "大纲"

    # Find chapter goal from detailed outline
    goal = f"第{args.chapter}章"
    for fname in ["详细大纲", "第1卷-详细大纲"]:
        for suffix in ["", ".md", "-上.md", "-中.md", "-下.md"]:
            p = outline_dir / f"{fname}{suffix}"
            if p.is_file():
                text = p.read_text(encoding="utf-8")
                # Search for chapter section
                import re
                pattern = rf"##?\s*第{args.chapter}章[^\n]*\n(.*?)(?=##?\s*第\d+章|\Z)"
                m = re.search(pattern, text, re.DOTALL)
                if m:
                    goal = f"第{args.chapter}章\n{m.group(1).strip()[:1500]}"
                    break
        if goal != f"第{args.chapter}章":
            break

    # Also get last 3 chapters summary
    summaries = ""
    text_dir = root / "正文"
    ch_files = sorted(text_dir.rglob("第*章*.md"))
    recent = [f for f in ch_files if int(re.search(r'第0*(\d+)章', f.name).group(1)) < args.chapter][-3:]
    for f in recent:
        t = f.read_text(encoding="utf-8")
        first_para = ""
        for line in t.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith(">") and not line.startswith("---") and not line.startswith("-"):
                first_para = line[:150]
                break
        summaries += f"[前章摘要] {first_para}\n"

    # Build prompt
    prompt = f"""你是《你好！迪恩》的写作助手（context-agent）。生成一份300字以内的写作任务书。

=== 本章章纲 ===
{goal}

=== 前几章摘要 ===
{summaries}

=== 全局约束 ===
- 每章开头标注分比进度条（当前50:50）
- 迪恩斯系统吐槽保持诙谐+硬核量化
- 对话占比40%+
- 章末必须具体钩子，不能模糊
- 前5章纯爽文节奏，哲学不露
- 每章2000-2500字"""

    payload = json.dumps({
        "action": "chat",
        "message": prompt,
        "thread_id": f"ctx-ch{args.chapter}",
        "options": {"mode": args.mode}
    })

    result = subprocess.run(
        [str(PYTHON), str(BRIDGE), "task", payload],
        capture_output=True, text=True, timeout=120,
        cwd=Path.home() / "HermesWorkspace"
    )

    for line in result.stdout.strip().split("\n"):
        try:
            d = json.loads(line)
            if d.get("status") == "result":
                print(d.get("text", "").strip())
                return
        except json.JSONDecodeError:
            continue

    print("（context-agent 未返回结果，请手动起草）")


if __name__ == "__main__":
    main()
