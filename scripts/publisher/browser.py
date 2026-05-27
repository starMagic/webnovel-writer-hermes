# .opencode/scripts/publisher/browser.py
"""Playwright 浏览器生命周期管理。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
]


def get_user_data_dir(platform: str) -> Path:
    return Path.home() / ".webnovel-publish" / "browser_data" / platform


class Browser:
    """管理 Playwright 浏览器会话。

    始终使用 launch_persistent_context。番茄小说的认证需要完整的浏览器
    数据目录（cookies + localStorage + IndexedDB 等），Playwright 的
    storage_state 只保存 cookies/origins，不足以维持登录态。
    """

    def __init__(self, headless: bool = True, platform: str = ""):
        self.headless = headless
        self.platform = platform
        self._playwright = None
        self._context = None
        self._page = None

    def _get_launch_args(self) -> list[str]:
        args = [*_STEALTH_ARGS]
        if sys.platform == "linux":
            try:
                if os.geteuid() == 0:
                    args.append("--no-sandbox")
            except AttributeError:
                pass
        return args

    async def start(self):
        """启动持久化浏览器上下文。登录态由 user_data_dir 自动维护。"""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        user_data_dir = get_user_data_dir(self.platform)
        user_data_dir.mkdir(parents=True, exist_ok=True)

        self._context = (
            await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=self.headless,
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
                args=self._get_launch_args(),
            )
        )

        self._page = (
            self._context.pages[0]
            if self._context.pages
            else await self._context.new_page()
        )
        return self._page

    async def close(self):
        try:
            if self._context:
                await self._context.close()
                self._context = None
                self._page = None
        finally:
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
