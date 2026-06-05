# Webnovel Writer for Hermes

[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Hermes Agent](https://img.shields.io/badge/Hermes%20Agent-Compatible-purple.svg)](https://github.com/NousResearch/hermes-agent)

基于 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的长篇中文网文 AI 创作系统。通过分层 RAG、故事合同（Story Contracts）和结构化质量审查，解决 AI 在连载创作中的"遗忘"和"幻觉"问题。

> 移植自 [webnovel-writer](https://github.com/lingfengQAQ/webnovel-writer) (Claude Code 版) 和 [webnovel-writer-opencode](https://github.com/lujih/webnovel-writer-opencode) (OpenCode 版)。

---

## 为什么选择 Hermes 版？

相比 Claude Code 版和 OpenCode 版，Hermes 版在架构上做了根本性的重新设计：

| 维度 | Claude Code / OpenCode 版 | Hermes 版 |
|------|--------------------------|-----------|
| **Agent 框架** | 绑定特定工具（Claude Code CLI / OpenCode Agent） | 基于 Hermes 原生 `skill_view` + `delegate_task`，与框架解耦 |
| **跨会话记忆** | 依赖项目文件，会话间容易丢失上下文 | Hermes 持久记忆系统，自动跨会话记住创作偏好和设定决策 |
| **多端创作** | 仅 CLI | WebUI / Telegram / Discord / CLI 全端可用，同一本书任何设备都能写 |
| **模型自由** | Claude Code 版锁定 Claude，OpenCode 版绑定其 Provider | 支持任意 LLM（DeepSeek / GPT / Claude / 国产模型），按需切换 |
| **技能模块化** | 单体指令集 | 12 个独立技能，可单独加载、修补、升级，互不干扰 |
| **定时任务** | 无 | 支持 cron 定时写作、自动备份、定期审查 |
| **上下文预算** | 固定窗口 | 伏笔债务感知的动态预算分配，超 2 条未回收伏笔自动激活 15% token 预留 |
| **子 Agent 隔离** | 子 Agent 泄漏上下文 | `delegate_task` 干净上下文隔离，每个子 Agent 只拿到所需的上下文 |

**一句话：Hermes 版不是"移植"，是在 Hermes 原生能力上做的架构升级。** 你把 Hermes 当日常助手用（写代码、查资料、管日程），同时它也是你的写作搭档——同一个人格、同一套记忆、同一个对话流。

---

## 小白零门槛起步

**没写过网文？不知道写什么题材？完全没关系。**

Hermes 版针对零基础用户设计了一条"选择式起步"路径，不需要你提前有任何创意：

```
你: "我想写网文但不知道写什么"
    ↓
📊 市场扫描：三大平台对比，热门品类展示
    "番茄男频快节奏，七猫女频甜宠向，起点深度阅读……
     目前番茄最火的是都市异能和系统流，选一个感兴趣的方向？"
    ↓
📖 对标拆解：搜 3-5 本该方向热书，拆给你看
    "这 5 本书的共同规律：穿越/重生开头占 100%，
     1-2 章一个爽点，主角都是'废柴外表+隐藏实力'……
     给你 3 个缝合方案，选哪个？"
    ↓
✍️ 搭骨架：基于你选的缝合方案，细化书名、主角、金手指
    "好，你的故事核：重生+签到系统+都市异能。
     主角叫 XXX，第一章就面临前世导致他死亡的危机……"
    ↓
🚀 开始写第一章
```

**你不用回答"你的题材是什么？"——你只需要在选项之间做选择。**

| 小白专属技能 | 做什么 |
|-------------|------|
| `webnovel-market` | 三大平台市场扫描：热门品类、读者偏好、爆款公式、小白选平台决策树 |
| `webnovel-learn` | 对标书拆解：输入平台+品类 → 输出钩子/节奏/人设/爽点/结构五类可选项卡片 + 缝合方案 |
| `webnovel-init`（小白路径） | 识别小白 → 自动走市场扫描→对标分析→缝合方案流程，选完才进入细化 |

有经验的作者可以跳过小白路径，直接走深度交互式创作信息收集。

---

## 核心特性

- **13 个技能覆盖全流程** — 从市场扫描、对标拆解、项目初始化、卷/章规划、单章/批量写作、审查润色、重写删除，到导出发布
- **6 层数据流架构** — 知识库 → 推理路由 → 故事合同 → 上下文组装 → 事实提交 → 投影写入，层层递进防遗忘
- **故事合同引擎** — MASTER_SETTING 作为全书真源，卷/章级合同约束写作边界，事件溯源记录所有变更
- **三级记忆系统** — 工作记忆（短）→ 情节记忆（中）→ 语义记忆（长），自动压缩与预算管理
- **6 维并行审查** — 一致性 / 连续性 / OOC / 爽点 / 节奏 / 追读力，子 Agent 并行评估
- **伏笔追踪（DebtTracker）** — 超 2 条未回收伏笔时自动激活 15% token 预算分配
- **知识图谱 RAG** — 实体关系图谱 + SQLite 持久化，支持时序查询"某角色在第 N 章时的状态"
- **可视化面板** — FastAPI + React 19 + ECharts，只读查看创作进度、实体图谱、章节内容
- **多格式导出** — MD / TXT / EPUB / HTML / DOCX / PDF，中文排版优化

---

## 两种运行模式

Hermes 版支持两种写章模式，启动时自动检测并选择最优方案：

### 模式一：Hermes + DeerFlow（推荐）

利用 [DeerFlow](https://github.com/bytedance/deer-flow)（字节跳动 Super Agent Harness）将 OpenCode 版的 sub-agent 管道完整移植到 Hermes：

```
┌─────────────────────────────────────────────────┐
│                  Hermes Agent                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ 自检模块  │  │ 正文起草  │  │  润色+备份   │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
│       │              │               │          │
│       ▼              ▼               ▼          │
│  ┌──────────────────────────────────────────┐   │
│  │           DeerFlow Gateway :8001          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │context-  │ │reviewer  │ │data-agent│  │   │
│  │  │agent     │ │(评分+    │ │(事实提取) │  │   │
│  │  │(任务书)  │ │ 审查)    │ │          │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘  │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

| 步骤 | 执行者 | 模式 | 耗时 |
|------|--------|------|------|
| Step 0: 自检 | Bridge health check | — | ~2s |
| Step 1: context-agent | DeerFlow | think | ~13s |
| Step 2: 正文起草 | **Hermes 直写** | — | 人工 |
| Step 3: reviewer | DeerFlow | flash | ~15s |
| Step 4: 润色 | Hermes | — | 人工 |
| Step 5: data-agent | DeerFlow | flash | ~10s |
| Step 6: 备份 | Git | — | ~1s |

**核心设计**：正文起草由 Hermes 主模型完成（需要创作能力），context-agent / reviewer / data-agent 三个结构化子任务交由 DeerFlow 并行执行。使用 Python wrapper 脚本（`scripts/context_agent.py`、`scripts/review_chapter.py`）彻底避免 shell JSON 转义问题。

### 模式二：仅 Hermes（降级）

当 DeerFlow Gateway 不可用时，自动降级为 Hermes 直写模式，跳过子 Agent 管道。经 300+ 章实战验证，产出质量可用。

### 自检逻辑

每次写章前自动运行：

```bash
# 1. 检查 bridge 脚本是否存在
# 2. 检查 DeerFlow Gateway 是否可达 (curl :8001/health)
# 3. 检查 bridge 健康状态
# 全部通过 → hermes+deerflow
# 任何失败 → hermes-only（安静降级，不中断流程）
```

> **前置依赖（仅模式一需要）**：安装并运行 [DeerFlow](https://github.com/bytedance/deer-flow)，Gateway 监听 `127.0.0.1:8001`。

---

## 快速开始

### 环境要求

- Python 3.10+
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)（已安装并运行）

### 安装

```bash
git clone https://github.com/starMagic/webnovel-writer-hermes.git
cd webnovel-writer-hermes
python install.py
```

安装后，12 个技能会注册到 `~/.hermes/skills/webnovel-writer-hermes/`，在 Hermes 中自动可用。

### 在 Hermes 中使用

直接对话即可触发，Hermes 会自动加载对应技能：

```
"帮我初始化一个玄幻小说"          → 自动加载 webnovel-init
"规划第3卷大纲"                   → 自动加载 webnovel-plan
"写第5章"                        → 自动加载 webnovel-write
"连写第10到15章"                  → 自动加载 webnovel-write-batch
"审查前10章"                     → 自动加载 webnovel-review
"导出为 EPUB"                    → 自动加载 webnovel-export
```

也可以手动加载技能：

```python
skill_view(name='webnovel-writer-hermes/webnovel-init')
```

### 可视化面板

```bash
cd webnovel-writer-hermes
python -m dashboard
```

访问 `http://127.0.0.1:8888` 查看项目状态、实体图谱和章节内容。

---

## 技能列表

| 技能 | 用途 | 典型触发 |
|------|------|---------|
| `webnovel-market` | 三大平台市场扫描，热门品类+读者偏好+爆款公式+小白决策树 | "分析番茄最近什么题材火" |
| `webnovel-init` | 深度初始化项目，结构化收集创作信息，生成设定集/大纲/合同树 | "初始化一个玄幻小说" |
| `webnovel-plan` | 基于总纲生成卷纲、时间线、章纲（精确到 CBN/CPNs/CEN 节点） | "规划第3卷大纲" |
| `webnovel-write` | 单章 6 步闭环：上下文→起草→审查→润色→提交→备份 | "写第5章" |
| `webnovel-write-batch` | 批量写作，逐章完整流程，支持断点续传 | "连写第10到15章" |
| `webnovel-review` | 事后 6 维审查，生成结构化评分报告 | "审查前10章" |
| `webnovel-rewrite` | 安全删除旧版 → 清理投影 → 用当前设定重写 | "重写第5章" |
| `webnovel-delete` | 安全删除章节及关联投影数据，支持 dry-run 预览 | "删除第3章" |
| `webnovel-export` | 导出 MD / TXT / EPUB / HTML / DOCX / PDF | "导出为 EPUB" |
| `webnovel-publish` | 自动发布到小说平台（番茄等） | "发布到番茄小说" |
| `webnovel-query` | 查询设定、角色状态、伏笔紧急度、金手指状态 | "主角现在什么境界" |
| `webnovel-learn` | 拆解参考书，提取节奏/桥段/人设模式，写入灵感库 | "拆解《诡秘之主》的节奏" |
| `webnovel-dashboard` | 启动只读可视化面板 | "打开写作面板" |

---

## 架构概览

### 6 层数据流

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Knowledge │ →  │ Reasoning│ →  │ Contract │ →  │ Context  │ →  │  Commit  │ →  │Projection│
│  知识库   │    │ 推理路由 │    │ 故事合同 │    │ 上下文   │    │ 事实提交 │    │ 投影写入 │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
   CSV+MD        题材匹配+        MASTER_SETTING   JSON组装        事件溯源+       state/index/
   +BM25         反套路排序      +卷/章合同        给写作者        事实提取       summary/
                                                                               memory/vector
```

### 子系统

| 子系统 | 说明 | 核心模块 |
|--------|------|---------|
| 故事合同引擎 | MASTER_SETTING 真源，卷/章合同派生，事件溯源 | `story_system_engine.py`, `story_contracts.py` |
| 记忆系统 | 三层记忆：工作/情节/语义，自动压缩预算管理 | `memory/orchestrator.py`, `memory/compactor.py` |
| 审查流水线 | 确定性代码检查 → 6 维 LLM 并行审查 | `review_pipeline.py`, `review_schema.py` |
| 伏笔追踪 | 伏笔债务 + 硬约束阻断 + 上下文预算自适应 | `index_debt_mixin.py` |
| 图 RAG | 实体关系图谱 + SQLite + 时序状态查询 | entity linking + index 模块 |
| 可视化面板 | FastAPI 后端 + React 19 前端 + ECharts | `dashboard/` |

### 5 个子 Agent

| Agent | 职责 |
|-------|------|
| `context-agent` | 收集写作上下文，生成写作任务书 |
| `chapter-writer-agent` | 起草 + 润色（干净上下文中的完整创作闭环） |
| `reviewer` | 6 维并行审查（一致性/连续性/OOC/爽点/节奏/追读力） |
| `data-agent` | 从正文提取事实，生成 fulfillment/disambiguation/extraction |
| `deconstruction-agent` | 拆解参考书，提取可复用模式 |

---

## CLI 命令

统一入口 `scripts/webnovel.py`，共 28 个子命令：

```bash
python scripts/webnovel.py preflight       # 验证运行环境
python scripts/webnovel.py status          # 项目健康报告
python scripts/webnovel.py story-system    # 故事合同管理
python scripts/webnovel.py review-pipeline # 审查流水线
python scripts/webnovel.py chapter-commit  # 章节提交
python scripts/webnovel.py export          # 导出
python scripts/webnovel.py publish         # 发布
python scripts/webnovel.py memory-contract # 记忆管理
python scripts/webnovel.py knowledge       # 知识查询
# ... 共 28 个命令
```

### 运行测试

```bash
# 全部测试（60 个测试文件）
python -m pytest scripts/data_modules/tests -q --no-cov

# 单个测试
python -m pytest scripts/data_modules/tests/test_config.py -q --no-cov
```

---

## 创作流程示例

### 小白起步（零基础）

```
用户: "我想写网文但完全不知道写什么"
  ↓
Hermes 加载 webnovel-init → 识别为小白 → 进入小白路径
  ↓
📊 Step 0.2: webnovel-market 市场扫描
  "你是番茄读者还是七猫读者？番茄最近最火的是都市异能和系统流，
   七猫女频豪门总裁和古言宫斗持续霸榜。起点门槛高，不建议新手直接上。
   你平时看哪个App？"
  用户: "番茄，比较喜欢看那种主角有系统的"
  ↓
📖 Step 0.4: webnovel-learn 对标拆解
  "好，搜了番茄系统流 5 本热书——"
  
  钩子卡片: 5本书100%用「系统激活+立刻任务」开头，第1章就有危机
  人设卡片: 80%是「废柴外表+隐藏天赋」，读者最爱反差感
  节奏卡片: 1-2章一个爽点，对话占比40%以上，节奏不能慢
  
  🔧 缝合方案:
    A（保守）: 穿越+签到系统+都市 → 稳定但模板化
    B（差异）: 重生+任务系统+轻度规则怪谈元素 → 有点新意
    C（特色）: 普通人+神秘传承+隐藏世界 → 慢热但后劲足
  用户: "B 方案有点意思"
  ↓
✍️ 细化故事核
  → 书名：《重生之规则入侵》（工作名）
  → 故事核：主角重生回规则怪谈降临前三天，绑定"违规检测系统"
  → 核心冲突：在规则怪谈中存活 + 揭露幕后组织
  → 生成：设定集/、大纲/总纲.md、.story-system/MASTER_SETTING.json
  ↓
用户: "规划第一卷"
  ↓
Hermes 加载 webnovel-plan → 生成节拍表、时间线、详细章纲
  → 每章精确到 CBN/CPNs/CEN 节点 + 必须覆盖节点 + 本章禁区
  ↓
用户: "写前3章"
  ↓
Hermes 加载 webnovel-write-batch → 逐章完整闭环：
  第1章: context-agent → chapter-writer-agent → reviewer(6维) → 修复 → 提交
  第2章: （加载第1章事实上下文）
  第3章: （同上）
  → 每章汇报：审查得分 + 字数 + 伏笔状态
  ↓
用户: "导出为 EPUB"
  ↓
Hermes 加载 webnovel-export → 生成带目录 + CSS 排版的 EPUB
```

### 有想法直接写（有经验作者）

```
用户: "我想写一本都市修真的，主角是被宗门抛弃的废柴"
  ↓
Hermes 加载 webnovel-init → 7 步结构化追问
  → 生成：设定集/世界观.md、力量体系.md、主角卡.md、总纲.md
  → 生成：.story-system/MASTER_SETTING.json（全书调性合同）
  ↓
用户: "规划第一卷"
  ↓
Hermes 加载 webnovel-plan → 生成节拍表、时间线、详细章纲
  → 每章精确到 CBN（章节起点）/ CPNs（推进节点）/ CEN（章节终点）
  → 包含本章禁区、必须覆盖节点
  ↓
用户: "写前3章"
  ↓
Hermes 加载 webnovel-write-batch → 逐章完整闭环：
  第1章: context-agent → chapter-writer-agent → reviewer(6维) → 修复 → 提交 → 备份
  第2章: （同上，加载第1章事实上下文）
  第3章: （同上）
  → 每章汇报：审查得分 + 字数 + 伏笔状态
  ↓
用户: "第2章节奏太慢，重写"
  ↓
Hermes 加载 webnovel-rewrite → 安全删除 → 清理投影 → 重写 → 验证连续性
  ↓
用户: "导出为 EPUB"
  ↓
Hermes 加载 webnovel-export → 生成带目录 + CSS 排版的 EPUB
```

---

## 项目结构

```
webnovel-writer-hermes/
├── .hermes-skills/          # 13 个 Hermes 技能定义
├── agents/                  # 5 个子 Agent 定义
├── scripts/                 # CLI 入口 + 核心数据模块
│   ├── webnovel.py          # 统一 CLI 入口（28 个命令）
│   └── data_modules/        # 核心引擎（故事合同/记忆/审查/投影/索引）
│       └── tests/           # 60 个测试文件
├── dashboard/               # FastAPI + React 19 可视化面板
├── references/              # CSV 知识表 + MD 创作参考（命名规则/桥段/爽点/场景写法）
├── genres/                  # 题材路由 + 反套路库
├── templates/               # 输出模板（节拍表/时间线/大纲格式）
├── install.py               # 一键安装脚本
├── manifest.json            # 项目元数据
└── AGENTS.md                # Hermes Agent 开发指南
```

---

## 开源协议

本项目基于 [GPL v3](LICENSE) 协议开源。

移植自：
- [lingfengQAQ/webnovel-writer](https://github.com/lingfengQAQ/webnovel-writer) (Claude Code 版)
- [lujih/webnovel-writer-opencode](https://github.com/lujih/webnovel-writer-opencode) (OpenCode 版)
