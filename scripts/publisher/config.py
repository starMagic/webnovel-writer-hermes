# .opencode/scripts/publisher/config.py
"""发布配置与上传进度追踪。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class PublishConfig:
    mode: str = "draft"          # draft | publish
    headless: bool = True
    retry_count: int = 2
    retry_delay: float = 3.0     # 秒
    chapter_gap: float = 5.0     # 章间间隔，避免触发反爬
    timeout: float = 30.0        # 单次操作超时


def get_upload_log_dir(project_name: str = "") -> Path:
    base = Path.home() / ".webnovel-publish" / "upload_log"
    if project_name:
        base = base / project_name
    return base


def _log_path(platform: str, book_id: str, project_name: str = "") -> Path:
    d = get_upload_log_dir(project_name)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{platform}_{book_id}.json"


def get_log_path(platform: str, book_id: str, project_name: str = "") -> Path:
    """公开接口：获取上传日志文件路径。"""
    return _log_path(platform, book_id, project_name)


def load_upload_log(platform: str, book_id: str, project_name: str = "") -> set[int]:
    p = _log_path(platform, book_id, project_name)
    if not p.is_file():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return set(data.get("uploaded", []))
    except (json.JSONDecodeError, KeyError):
        return set()


def save_upload_log(platform: str, book_id: str, uploaded: set[int], book_name: str = "", project_name: str = ""):
    p = _log_path(platform, book_id, project_name)
    # 先读出已有数据，合并 upload 列表（防止多进程竞态覆盖）
    existing = set()
    try:
        if p.is_file():
            existing = set(json.loads(p.read_text(encoding="utf-8")).get("uploaded", []))
    except (json.JSONDecodeError, KeyError):
        pass
    merged = sorted(existing | uploaded)
    payload = {
        "book_id": book_id,
        "book_name": book_name,
        "uploaded": merged,
        "last_upload": datetime.now(timezone.utc).isoformat(),
    }
    # 原子写入：先写临时文件，再 rename（跨平台原子操作）
    import os
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def get_publish_config_path(project_root: str | Path) -> Path:
    """项目级发布配置：绑定的 book_id、平台等。"""
    return Path(project_root) / ".webnovel" / "publish_config.json"


def load_publish_config(project_root: str | Path) -> dict:
    p = get_publish_config_path(project_root)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_publish_config(project_root: str | Path, data: dict):
    p = get_publish_config_path(project_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_book_id(project_root: str | Path, platform: str, book_spec: str | None) -> str:
    """将 book_spec（ID 或书名）解析为 book_id。
    优先顺序：显式传入 → publish_config.json 绑定 → 报错。"""
    if book_spec and book_spec.strip():
        spec = book_spec.strip()
        # 纯数字 → book_id
        if spec.isdigit():
            return spec
        # 书名 → 从上传日志查找
        log_dir = get_upload_log_dir()
        if log_dir.is_dir():
            for f in log_dir.glob(f"{platform}_*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    name = (data.get("book_name") or "").strip()
                    if name and spec.lower() in name.lower():
                        return data.get("book_id", "")
                except (json.JSONDecodeError, OSError):
                    pass
        raise ValueError(f"未找到匹配 '{spec}' 的书籍。请先 list-books 确认书名，或使用 book_id。")

    # 从项目配置读取
    cfg = load_publish_config(project_root)
    bound = cfg.get("bindings", {}).get(platform, {})
    bid = bound.get("book_id", "")
    if bid:
        return bid
    raise ValueError(f"未指定 --book 且项目未绑定书籍。请先 create-book 或传入 --book <id/书名>。")
