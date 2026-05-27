# .opencode/scripts/publisher/base.py
"""平台适配器抽象接口。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class BookMeta:
    title: str
    genre: str
    synopsis: str
    protagonist: str
    tags: list[str] = field(default_factory=list)


@dataclass
class Chapter:
    index: int
    title: str
    content: str
    volume_title: str = ""


@dataclass
class UploadResult:
    success: bool
    chapter_index: int
    message: str = ""
    url: str = ""


class BasePlatform(ABC):
    name: str = ""
    display_name: str = ""
    login_url: str = ""

    @abstractmethod
    async def setup_auth(self, page) -> bool:
        ...

    @abstractmethod
    async def list_books(self, page) -> list[dict]:
        ...

    @abstractmethod
    async def create_book(self, page, meta: BookMeta) -> str:
        ...

    @abstractmethod
    async def upload_chapter(self, page, book_id: str, chapter: Chapter) -> UploadResult:
        ...
