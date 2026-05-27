# .opencode/scripts/publisher/__init__.py
"""小说自动发布 — CLI 入口。

用法:
  python publisher/__init__.py --project-root <path> setup-auth --platform fanqie
  python publisher/__init__.py --project-root <path> list-books --platform fanqie
  python publisher/__init__.py --project-root <path> create-book --platform fanqie
  python publisher/__init__.py --project-root <path> upload --platform fanqie --book <id>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# subprocess 运行时 scripts/ 不在 Python path 中，确保绝对导入可用
_scripts_root = Path(__file__).resolve().parent.parent
if str(_scripts_root) not in sys.path:
    sys.path.insert(0, str(_scripts_root))

from publisher.adapters import get_adapter as _get_adapter_impl


def _get_adapter(platform: str):
    try:
        return _get_adapter_impl(platform)
    except ValueError as e:
        from publisher.adapters import list_platforms
        print(f"{e}")
        print(f"可用平台: {', '.join(list_platforms())}")
        sys.exit(1)


async def _cmd_setup_auth(args: argparse.Namespace):
    from publisher.browser import Browser
    adapter = _get_adapter(args.platform)
    browser = Browser(headless=False, platform=args.platform)
    page = await browser.start()
    try:
        ok = await adapter.setup_auth(page)
        if ok:
            print(f"[OK] {adapter.display_name} 登录成功，认证状态已自动保存")
        else:
            print(f"[FAIL] {adapter.display_name} 登录超时")
            sys.exit(1)
    finally:
        await browser.close()


async def _cmd_list_books(args: argparse.Namespace):
    from publisher.browser import Browser
    adapter = _get_adapter(args.platform)
    browser = Browser(platform=args.platform)
    page = await browser.start()
    try:
        books = await adapter.list_books(page)
        if not books:
            print("未找到书籍")
        else:
            for i, book in enumerate(books, 1):
                bid = book.get("book_id", "") or book.get("id", "")
                name = book.get("book_name", book.get("title", "未知"))
                print(f"  {i}. {name}  (book_id: {bid})")
    finally:
        await browser.close()


async def _cmd_create_book(args: argparse.Namespace):
    from publisher.browser import Browser
    from publisher.base import BookMeta
    from publisher.config import save_publish_config, load_publish_config
    adapter = _get_adapter(args.platform)
    project_root = Path(args.project_root).expanduser().resolve()
    meta = _read_book_meta(project_root)

    # 简介：自动生成 or 用户输入 or 跳过
    abstract = _build_abstract_from_project(project_root)
    if args.abstract:
        abstract = args.abstract
    elif not args.yes:
        print(f"\n自动生成简介:\n  {abstract}\n")
        choice = _safe_input("使用自动简介？[Y=使用 / 输入新简介 / N=跳过]: ", default="y")
        if choice.lower() == 'n':
            abstract = ""
        elif choice and choice.lower() != 'y':
            abstract = choice
    print(f"书名: {meta.title}")
    print(f"题材: {meta.genre}")
    print(f"简介: {abstract or '(跳过)'}")
    if not args.yes:
        resp = _safe_input("\n确认创建？(Y/n): ", default="y")
        if resp.lower() in ('n', 'no'):
            print("已取消。")
            return

    browser = Browser(platform=args.platform)
    page = await browser.start()
    try:
        book_id = await adapter.create_book(page, meta)
        if book_id:
            print(f"[OK] 书籍创建成功！book_id: {book_id}")
            # 绑定到项目
            cfg = load_publish_config(project_root)
            cfg.setdefault("bindings", {})[args.platform] = {
                "book_id": book_id, "book_name": meta.title,
            }
            save_publish_config(project_root, cfg)
            print(f"  已绑定到项目: {project_root}")
        else:
            print("[FAIL] 创建失败，请手动检查")
            sys.exit(1)
    finally:
        await browser.close()


def _build_abstract_from_project(project_root: Path) -> str:
    """从项目元数据自动生成简介（50+ 字）。"""
    import json as _json
    state_path = project_root / ".webnovel" / "state.json"
    pi = {}
    if state_path.is_file():
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
            pi = state.get("project_info", {})
        except (_json.JSONDecodeError, OSError):
            pass
    parts = []
    selling = pi.get("core_selling_points", "")
    if selling:
        parts.append(selling)
    world = pi.get("world_scale", "")
    gf = pi.get("golden_finger_name", "")
    if gf and world:
        parts.append(f"{world}背景，{gf}为刃")
    return "。".join(parts) if parts else ""


async def _cmd_upload(args: argparse.Namespace):
    from publisher.browser import Browser
    from publisher.base import Chapter
    from publisher.config import PublishConfig, load_upload_log, save_upload_log, resolve_book_id
    from publisher.formatter import format_for_platform

    project_root = Path(args.project_root).expanduser().resolve()
    book_id = resolve_book_id(project_root, args.platform, getattr(args, 'book', None))
    # 首次上传时自动持久化绑定
    if getattr(args, 'book', None):
        from publisher.config import load_publish_config, save_publish_config
        cfg = load_publish_config(project_root)
        if str(args.platform) not in cfg.get("bindings", {}):
            cfg.setdefault("bindings", {})[args.platform] = {"book_id": book_id}
            save_publish_config(project_root, cfg)

    adapter = _get_adapter(args.platform)
    adapter.set_mode(args.mode)
    cfg = PublishConfig(mode=args.mode)
    project_name = project_root.name
    uploaded = load_upload_log(args.platform, book_id, project_name)

    # 交叉校验：防止 book_id 误用
    from publisher.config import get_log_path
    log_path = get_log_path(args.platform, book_id, project_name)
    if log_path.is_file():
        try:
            log_data = json.loads(log_path.read_text(encoding="utf-8"))
            logged_book_id = log_data.get("book_id", "")
            if logged_book_id and logged_book_id != book_id:
                logged_name = log_data.get("book_name", "未知")
                print(f"⚠️ 警告: 上传日志中的 book_id ({logged_book_id}, {logged_name}) 与当前 book_id ({book_id}) 不一致！")
                print("可能原因: 误用了另一本书的 book_id。")
                if getattr(args, 'yes', False):
                    print("--yes 已指定，跳过确认继续上传。")
                else:
                    resp = _safe_input("确认继续上传？(y/N): ", default="n")
                    if resp.lower() != "y":
                        print("已取消。")
                        return
        except (json.JSONDecodeError, KeyError):
            pass

    book_meta = _read_book_meta(project_root)
    book_name = book_meta.title if book_meta else ""
    chapter_indices = _parse_range(args.range, project_root)
    to_upload = [i for i in chapter_indices if i not in uploaded]
    if not to_upload:
        print("所有章节已上传。")
        return

    # 上传确认摘要
    print(
        f"目标书籍: {book_name or '?'} (book_id: {book_id})\n"
        f"待上传: {len(to_upload)} 章 "
        f"(共 {len(chapter_indices)} 章, {len(uploaded)} 章已传)\n"
        f"模式: {args.mode}"
    )
    if not getattr(args, 'yes', False):
        resp = _safe_input("继续？(Y/n): ", default="y")
        if resp.lower() in ('n', 'no'):
            print("已取消。")
            return

    browser = Browser(headless=cfg.headless, platform=args.platform)
    page = await browser.start()
    success_count = 0
    fail_count = 0

    try:
        for idx in to_upload:
            chapter_file = _find_chapter_file(project_root, idx)
            if not chapter_file:
                print(f"  [WARN] 第{idx}章文件未找到，跳过")
                fail_count += 1
                continue

            raw_md = chapter_file.read_text(encoding="utf-8")
            title = _extract_title(raw_md) or f"第{idx}章"
            # 剔除首行标题（平台 API 单独设标题，正文不需重复）
            raw_md = _strip_heading_line(raw_md)
            content = format_for_platform(raw_md, args.platform)
            chapter = Chapter(index=idx, title=title, content=content)

            try:
                result = await adapter.upload_chapter(page, book_id, chapter)
            except RuntimeError as e:
                fail_count += 1
                print(f"  [FAIL] 第{idx}章 {e}")
                await asyncio.sleep(cfg.chapter_gap)
                continue
            if result.success:
                uploaded.add(idx)
                save_upload_log(args.platform, book_id, uploaded, book_name=book_name, project_name=project_name)
                success_count += 1
                print(f"  [OK] 第{idx}章 {result.message}")
            else:
                fail_count += 1
                print(f"  [FAIL] 第{idx}章 {result.message}")

            await asyncio.sleep(cfg.chapter_gap)
    finally:
        await browser.close()

    print(f"\n上传完成: 成功 {success_count}, 失败 {fail_count}")


def _safe_input(prompt: str, default: str = "y") -> str:
    """Wrap input() with EOFError guard for non-TTY environments."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print(f"\n[非交互环境] 输入不可用，使用默认值: {default}")
        return default


def _read_book_meta(project_root: Path):
    from publisher.base import BookMeta
    import json
    state_file = project_root / ".webnovel" / "state.json"
    meta = BookMeta(title="", genre="", synopsis="", protagonist="")
    if state_file.is_file():
        s = json.loads(state_file.read_text(encoding="utf-8"))
        proj_info = s.get("project_info", {}) if isinstance(s, dict) else {}
        meta.title = proj_info.get("title", "") or project_root.name
        meta.genre = proj_info.get("genre", "")
        protag = s.get("protagonist_state", {}) if isinstance(s, dict) else {}
        meta.protagonist = protag.get("name", "") if isinstance(
            protag, dict) else ""
        meta.synopsis = proj_info.get("synopsis", "")
    return meta


def _parse_range(spec: str, project_root: Path) -> list[int]:
    import re
    if spec.lower() == "all":
        text_dir = project_root / "正文"
        if text_dir.is_dir():
            nums = []
            for f in sorted(text_dir.rglob("第*章*.md")):
                m = re.match(r"第(\d+)章", f.name)
                if m:
                    nums.append(int(m.group(1)))
            return nums
        return []

    result: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                a, b = part.split("-", 1)
                result.update(range(int(a), int(b) + 1))
            else:
                result.add(int(part))
        except ValueError:
            print(f"ERROR: 无效的章节范围 '{part}'，应为数字或范围（如 32-37）", file=sys.stderr)
            raise SystemExit(1)
    return sorted(result)


def _strip_heading_line(md: str) -> str:
    """剔除首行 Markdown 标题（## 第XX章 标题），避免正文重复标题。"""
    import re
    lines = md.splitlines()
    if lines:
        first = lines[0].strip()
        if first.startswith("#") and re.search(r'第\d+章', first):
            return '\n'.join(lines[1:]).lstrip('\n')
    return md


def _extract_title(md: str) -> str:
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def _find_chapter_file(project_root: Path, index: int) -> Path | None:
    """在正文目录中定位章节文件。优先按卷目录查找，避免多卷同名冲突。"""
    import re
    text_dir = project_root / "正文"
    if not text_dir.is_dir():
        return None

    def _match(f):
        return re.match(rf"第0*{index}章", f.name)

    # 优先在当前卷目录查找
    vol = (index - 1) // 20 + 1
    vol_dir = text_dir / f"第{vol}卷"
    if vol_dir.is_dir():
        for f in sorted(vol_dir.iterdir()):
            if f.is_file() and f.suffix == ".md" and _match(f):
                return f

    # 回退到正文根目录
    for f in sorted(text_dir.iterdir()):
        if f.is_file() and f.suffix == ".md" and _match(f):
            return f

    # 最后递归搜索（兼容旧结构）
    for f in sorted(text_dir.rglob("*.md")):
        if _match(f):
            return f
    return None


def main():
    parser = argparse.ArgumentParser(description="小说自动发布")
    parser.add_argument("--project-root", type=Path, default=Path("."),
                        help="书项目根目录")
    sub = parser.add_subparsers(dest="command", required=True)

    p_setup = sub.add_parser("setup-auth", help="引导登录指定平台")
    p_setup.add_argument("--platform", required=True,
                         help="平台名称 (fanqie)")

    p_list = sub.add_parser("list-books", help="列出已有书单")
    p_list.add_argument("--platform", required=True, help="平台名称")

    p_create = sub.add_parser("create-book", help="创建新书")
    p_create.add_argument("--platform", required=True, help="平台名称")
    p_create.add_argument("--abstract", default=None, help="书籍简介（默认自动生成）")
    p_create.add_argument("--yes", action="store_true", help="跳过交互确认")

    p_upload = sub.add_parser("upload", help="上传章节")
    p_upload.add_argument("--platform", required=True, help="平台名称")
    p_upload.add_argument("--book", default=None, help="书籍 ID 或书名（未指定时从项目绑定读取）")
    p_upload.add_argument("--range", default="all", help="章节范围")
    p_upload.add_argument("--mode", default="draft", choices=["draft"],
                          help="发布模式 (目前仅支持草稿)")
    p_upload.add_argument("--yes", action="store_true",
                          help="跳过交叉校验的交互确认")

    args = parser.parse_args()

    cmd_map = {
        "setup-auth": _cmd_setup_auth,
        "list-books": _cmd_list_books,
        "create-book": _cmd_create_book,
        "upload": _cmd_upload,
    }
    handler = cmd_map.get(args.command)
    if handler:
        asyncio.run(handler(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
