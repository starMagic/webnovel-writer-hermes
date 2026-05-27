# AGENTS.md

This file provides guidance to Hermes Agent when working with code in this repository.

## Project

Webnovel Writer for Hermes — a long-form Chinese web novel AI writing system built on the Hermes Agent framework. Combats AI "forgetting" and "hallucination" in serialized fiction through layered RAG, story contracts, and structured quality review.

Migrated from [webnovel-writer (Claude Code)](https://github.com/lingfengQAQ/webnovel-writer) and [webnovel-writer-opencode](https://github.com/lujih/webnovel-writer-opencode).

## Hermes Integration

### Skills (12 skills in `.hermes-skills/`)

Load with `skill_view(name='webnovel-xxx')`. **Auto-load rule**: scan user message for trigger keywords; if matched, load the skill before responding.

| Skill | 中文触发词 | Auto-load when user says... | What it does |
|-------|----------|---------------------------|-------------|
| `webnovel-init` | 初始化, 创建小说, 新建项目, 开始写新书 | "帮我初始化一个玄幻小说" | Deep project init: genre picker, MASTER_SETTING seed, outline scaffold |
| `webnovel-plan` | 规划, 大纲, 卷纲, 章纲 | "规划第3卷大纲" | Volume/chapter planning with genre pacing templates |
| `webnovel-write` | 写, 写章, 继续写, 写第, 撰写 | "帮我写第5章" | 6-step pipeline: context→draft→review→polish→commit→backup |
| `webnovel-write-batch` | 批量, 连写, 连更 | "连写第10到15章" | Batch writing with context isolation per chapter |
| `webnovel-review` | 审查, review, 审阅 | "审查前10章的一致性" | Post-hoc 6-dimension review (consistency/continuity/OOC/high-point/pacing/reader-pull) |
| `webnovel-rewrite` | 重写, 改, 修改 | "重写第5章的高潮部分" | Targeted chapter rewrite, preserving commit history |
| `webnovel-delete` | 删除, 删章 | "删除第3章" | Safe deletion with index/index cleanup |
| `webnovel-export` | 导出 | "导出为EPUB" | Export to MD/EPUB/HTML/DOCX |
| `webnovel-publish` | 发布 | "发布到番茄小说" | Platform publishing with format adaptation |
| `webnovel-query` | 查询, 状态, 进度 | "查询当前写作进度" | Project health: chapter count, debt status, word count trends |
| `webnovel-learn` | 拆书, 学习, 分析 | "拆解《诡秘之主》的节奏" | Reference novel deconstruction → idea bank |
| `webnovel-dashboard` | 面板, dashboard | "打开写作面板" | Launch FastAPI+React visualization dashboard on port 8888 |

### Agents (5 agents in `agents/`)

Original OpenCode used `Agent()` subagent calls. In Hermes, use `delegate_task`:

| Agent | Hermes usage |
|-------|-------------|
| `context-agent` | `delegate_task(goal="Generate writing brief for chapter N", context="...")` |
| `data-agent` | `delegate_task(goal="Extract facts from chapter N", context="...")` |
| `reviewer` | `delegate_task(goal="Review chapter N", context="...")` × 6 parallel |
| `chapter-writer-agent` | `delegate_task(goal="Draft chapter N", context="...")` |
| `deconstruction-agent` | `delegate_task(goal="Deconstruct reference novel", context="...")` |

### Skill Loading Pattern

When the user says "写第5章":
1. Load the skill: `skill_view(name='webnovel-write')`
2. Follow the skill's 6-step pipeline
3. Call agents via `delegate_task` where the skill says to use Agent()

## Commands

### Testing

```bash
# Full test suite (from repo root)
python -m pytest scripts/data_modules/tests -q --no-cov

# Single test file
python -m pytest scripts/data_modules/tests/test_config.py -q --no-cov

# Single test function
python -m pytest scripts/data_modules/tests/test_config.py::test_load_env -q --no-cov
```

Tests live in `scripts/data_modules/tests/` (60 test files).

### CLI

```bash
# Unified entry point for all commands
python scripts/webnovel.py <command> [args]

# Common subcommands
python scripts/webnovel.py preflight       # validate runtime environment
python scripts/webnovel.py status          # project health report
python scripts/webnovel.py story-system    # story contract management
python scripts/webnovel.py review-pipeline # review pipeline management
python scripts/webnovel.py export          # export novel
python scripts/webnovel.py publish         # publish to platform
python scripts/webnovel.py memory          # memory system management
```

Full command list (28 commands): `where`, `preflight`, `use`, `index`, `state`, `rag`, `style`, `entity`, `context`, `memory`, `migrate`, `status`, `update-state`, `backup`, `archive`, `init`, `extract-context`, `story-system`, `story-events`, `chapter-commit`, `memory-contract`, `project-memory`, `review-pipeline`, `placeholder-scan`, `master-outline-sync`, `export`, `publish`, `knowledge`.

Most subcommands forward to `data_modules/<module>.py` via argparse dispatch. The entry point auto-resolves the book project root (directory containing `.webnovel/state.json`).

### Dashboard

```bash
# Backend (FastAPI on port 8888)
python -m dashboard

# Frontend dev server (React + Vite, separate terminal)
cd dashboard/frontend && npm run dev
```

## Architecture

### Six-Layer Data Flow

Code is organized as a pipeline — each layer feeds the next:

| Layer | What | Where |
|-------|------|-------|
| Knowledge | CSV tables + MD references + BM25 retrieval | `references/` |
| Reasoning | Genre routing + anti-pattern ranking | `genres/` |
| Contract | MASTER_SETTING + volume/chapter briefs + review contracts | `.story-system/` (per-project) |
| Context | JSON assembly of what the writer needs | `scripts/data_modules/context_manager.py` |
| Commit | Fact extraction + event sourcing + projection routing | `scripts/data_modules/chapter_commit_service.py`, `scripts/data_modules/event_log_store.py` |
| Projection | 5 writers: state, index, summary, memory, vector | `scripts/data_modules/` various `*_writer.py` |

### Key Subsystems

**Story Contract Engine** — MASTER_SETTING.json is the source of truth. Runtime contracts derive from it per chapter. Event sourcing records all mutations; projections materialize state/index/summary/memory/vector views. Core files: `scripts/data_modules/story_system_engine.py`, `scripts/data_modules/story_contracts.py`, `scripts/data_modules/event_log_store.py`, `scripts/data_modules/event_projection_router.py`, `scripts/data_modules/chapter_commit_service.py`.

**Memory System** — Three tiers: working (short-term), plot (mid-term), semantic (long-term). Modules in `scripts/data_modules/memory/`: orchestrator, compactor, store, writer, schema, bootstrap, budget.

**DebtTracker** — Foreshadowing tracking with hard constraint blocking. Active debts > 2 triggers debt-aware context budget (auto-allocate 15% tokens to foreshadowing list). Implemented in `scripts/data_modules/index_debt_mixin.py` (mixed into `scripts/data_modules/index_manager.py`).

**Review Pipeline** — Two layers: Code Checkers (deterministic, run before LLM, block critical issues) → 6 parallel LLM reviewers (consistency, continuity, OOC, high-point, pacing, reader-pull). Reviewer output processed via `scripts/review_pipeline.py`, schema defined in `scripts/data_modules/review_schema.py`.

**Graph-RAG** — Entity relationship graph with SQLite persistence. Located in `scripts/data_modules/` entity linking and index modules.

**Dashboard** — FastAPI backend (read-only GET endpoints serving project state) + React 19 frontend with ECharts visualization. Backend: `dashboard/app.py`. Frontend: `dashboard/frontend/`.

### Key Convention: Unified CLI

All Python functionality routes through a single entry point: `scripts/webnovel.py` → `scripts/data_modules/webnovel.py`. Subcommands are dispatched via argparse. New subcommands should be added to the argparse subparser chain in `scripts/webnovel.py`.

## Commit Convention & Versioning

All commits **MUST** follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <简短描述>
```

### Types

| Type | 用途 | 版本影响 |
|------|------|---------|
| `feat:` | 新功能 | **bump MINOR** |
| `fix:` | Bug 修复 | **bump PATCH** |
| `feat!:` / `fix!:` / `BREAKING CHANGE:` | 破坏性变更 | **bump MAJOR** |
| `docs:` | 文档 | 不触发版本变更 |
| `refactor:` | 重构 | **bump PATCH** |
| `perf:` | 性能优化 | **bump PATCH** |
| `ci:` | CI/CD | 不触发版本变更 |
| `chore:` | 杂项 | 不触发版本变更 |
| `simplify:` | 代码审查清理 | 不触发版本变更 |
| `test:` | 测试 | 不触发版本变更 |

> 不要在提交里手动改 `manifest.json` 版本号——CI 自动处理。

## Phase 2: Hermes 特有增强（待实现）

利用 Hermes 相对 Claude Code/OpenCode 的差异化能力，以下增强项不阻塞 Phase 1 MVP，但可显著提升用户体验：

| 增强项 | Hermes 能力 | 实现思路 | 优先级 |
|-------|-----------|---------|-------|
| **自然语言多平台触发** | Gateway (15+平台) | 用户在微信/飞书说"写第3章"即可触发，不局限于终端 | P2 |
| **持久化用户文风偏好** | Memory | 用户偏爱的节奏/视角/字数偏好跨会话记忆，无需每次重申 | P1 |
| **定时自动审查** | Cron | 每日8点自动审查昨日章节，结果推送 | P1 |
| **自进化写作技能** | Skills auto-gen | 审查中发现的常见问题自动沉淀为新 Skill（如"玄幻打斗场面写法"） | P2 |
| **后台静默任务** | Background processes | 长任务（批量写作/全本审查）后台运行，完成后通知 | P1 |
| **多书并行管理** | Profiles | 不同小说用不同 profile 隔离状态和记忆 | P3 |

## 迁移决策记录

| 决策 | TeleClaw建议 | 最终选择 | 理由 |
|------|:----------:|:------:|------|
| Skill 文件结构 | 单文件 `.md` | 子目录 `SKILL.md` | Hermes 使用子目录结构，保留 references/evals |
| Agent 处理 | 合并进 Skill 步骤 | 保留独立 + `delegate_task` | 保留并行审查能力（6 reviewer 并行） |
| 目录组织 | 全塞 `.hermes/` | 顶层平铺 | `.hermes/` 是用户配置目录，不放项目代码 |
| 上下文注入 | 无 | `AGENTS.md` | Hermes 核心机制，等价 CLAUDE.md |
| 触发方式 | YAML triggers 字段 | 技能表 + 中文触发词 | Hermes 无原生 triggers 字段，用描述+表格替代 |

## Guidelines

### 1. Think Before Coding

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them.
- If a simpler approach exists, say so.

### 2. Simplicity First

- No features beyond what was asked.
- No abstractions for single-use code.
- No error handling for impossible scenarios.

### 3. Surgical Changes

- Don't "improve" adjacent code, comments, or formatting.
- Match existing style.
- Remove only imports/variables/functions YOUR changes made unused.

### 4. Goal-Driven Execution

For multi-step tasks, state a brief plan with verification per step.
