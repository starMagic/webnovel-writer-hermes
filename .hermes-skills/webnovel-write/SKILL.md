---
name: webnovel-write
description: 产出可发布章节。支持两种模式——Hermes直写（默认）和 Hermes+DeerFlow 管道（context-agent→起草→reviewer→润色→data-agent→备份）。
compatibility: hermes
hermes: true
category: webnovel-writer
version: 2.0.0
---

# 写章流程

> 产出可发布章节到 `正文/第{NNNN}章-{title}.md`。

---

## 模式自检（必读）

**每次写章前，先跑自检决定用哪个模式：**

```bash
BRIDGE="$HOME/Workspace/Git/deer-flow/backend/.venv/bin/python3 $HOME/HermesWorkspace/deerflow_bridge.py"
HEALTH=$($BRIDGE health 2>&1)
if echo "$HEALTH" | grep -q '"healthy": true'; then
  echo "MODE: hermes+deerflow"
else
  echo "MODE: hermes-only"
fi
```

| 条件 | 模式 | 流程 |
|------|------|------|
| DeerFlow Gateway 健康 | **hermes+deerflow**（优先） | 自检→context-agent(DF)→起草→reviewer(DF)→润色→data-agent(DF)→备份 |
| DeerFlow 不可用 | **hermes-only**（降级） | 直写→批量备份 |

---

## 模式一：hermes+deerflow（推荐）

### 执行纪律

- 写前自检，不通则降级
- 每批写完后跑备份，不要每章打断
- DeerFlow 子任务超时=降级到 hermes-only

### Step 0：确定章节号

```bash
LATEST=$(python3 -c "
import re; from pathlib import Path
td = Path('${PROJECT_ROOT}') / '正文'
if not td.is_dir(): print(0)
else:
    nums = [int(m.group(1)) for f in td.rglob('第*章*.md') if (m := re.match(r'第0*(\d+)章', f.name))]
    print(max(nums) if nums else 0)
")
CHAPTER=$((LATEST + 1))
echo \"下一章: 第${CHAPTER}章\"
```

### Step 1：context-agent

> 调用封装脚本，自动读取章纲+前章摘要，生成写作任务书。

```bash
python3 scripts/context_agent.py --chapter ${CHAPTER} \
  --project-root "${PROJECT_ROOT}"
```
```

### Step 2：起草正文（Hermes）

根据任务书起草。**这是 Hermes 自己做，不走 DeerFlow。** 中文思维。每章 2000-2500 字，开头标注分比进度条。核心约束：迪恩斯吐槽风格、对话占比 40%+、章末具体钩子。

```bash
# 写后校验
CHAPTER_PATH="${PROJECT_ROOT}/正文/第$(printf '%04d' ${CHAPTER})章-${TITLE}.md"
test -s \"${CHAPTER_PATH}\" || { echo \"❌ 章节文件为空\"; exit 1; }
```

### Step 3：reviewer

> 调用封装脚本，自动读取章节文件并审查。

```bash
python3 scripts/review_chapter.py --chapter ${CHAPTER} \
  --project-root "${PROJECT_ROOT}"
```

返回 JSON：`{"passed": bool, "blocking": [...], "warnings": [...], "score": int, "summary": "..."}`。blocking=true → 修复后重审。
blocking=true → 修复后重审。warning → 记录，下次注意。

### Step 4：润色（Hermes）

修复 reviewer 的非 blocking issue。风格适配。排版。只改表达不改事实。

### Step 5：data-agent（DeerFlow）

> 提取章节事实。模式：flash。超时 60s。

```bash
$BRIDGE task "{
  \"action\":\"chat\",
  \"message\":\"你是《你好！迪恩》的数据提取员（data-agent）。从以下章节提取事实，输出 JSON：{\\\"entities\\\":[{\\\"name\\\":\\\"\\\",\\\"type\\\":\\\"\\\",\\\"changes\\\":\\\"\\\"}],\\\"score_changes\\\":{\\\"waker\\\":0,\\\"admin\\\":0},\\\"bifurcation\\\":\\\"\\\",\\\"new_locations\\\":[],\\\"foreshadowing\\\":[]}\\n\\n=== 正文 ===\\n${CHAPTER_TEXT:0:5000}\",
  \"thread_id\":\"data-ch${CHAPTER}\",
  \"options\":{\"mode\":\"flash\"}
}" 2>&1
```

提取后更新 state.json + index.db。

### Step 6：备份

```bash
cd $HOME/Workspace/Git/webnovel-writer-hermes && \
python3 -X utf8 scripts/webnovel.py --project-root \"${PROJECT_ROOT}\" backup \
  --chapter ${CHAPTER} --chapter-title \"${TITLE}\"
```

---

## 模式二：hermes-only（降级）

### 执行纪律（P0）

- **禁止中途暂停汇报进度。** 写完一章立刻写下一章。不要问「要不要继续？」、不要列 todo、不要发字数统计、不要求确认。用户原话：「你这是还要喘口气，中途求夸奖，求抱抱吗？后续的事情都交给你了，知道完成本书。」
- **写完再复盘，写完再扩章。** 第一遍跑骨架，章均 500-800 字是正常的番茄体节奏。不要边写边纠结字数——先跑完全书骨架再回头扩写。
- **每批 10 章集中 backup。** 不要每章单独 backup 打断写作流。
- **DeerFlow 子任务超时=降级到 hermes-only。** 不要卡 pipeline。

### 流程

1. 读对应章的详细大纲（CBN/CPNs/CEN/章末钩子/禁区）
2. 中文思维起草，每章开头标注分比进度条
3. 迪恩斯系统吐槽保持诙谐+硬核量化
4. 写后批量 backup（每批 10 章）

```bash
cd $HOME/Workspace/Git/webnovel-writer-hermes && \
for ch in $(seq N M); do
  python3 -X utf8 scripts/webnovel.py --project-root \"${PROJECT_ROOT}\" backup \
    --chapter $ch --chapter-title \"ch$ch\"
done
```

---

## Pitfalls

1. **DeerFlow reviewer shell 转义**：reviewer 任务中 `CHAPTER_TEXT` 含引号/换行符时，shell JSON 转义会断裂。**不要用 shell 变量内插大段文本。** 解决方案：将章节文本写入临时文件 → 用 Python 读文件内容构建 JSON payload → 直接调用 bridge。
2. **First call slow** — DeerFlowClient 懒加载 agent（system prompt + tool loading），首次调用可能延迟 10s+。
3. **Bridge health 必须先跑** — 不跑自检直接调 task 会在 Gateway 不可用时卡死。
4. **Thread continuity** — 必须传 thread_id 才能多轮对话。
5. **降级策略** — 任何 DeerFlow 步骤超时或失败 → 自动降级为 hermes-only 直写，不要卡 pipeline。

| 角色 | mode | timeout | 功能 |
|------|------|---------|------|
| context-agent | think | 120s | 章纲→写作任务书 |
| reviewer | pro | 300s | 章节→审查 JSON |
| data-agent | flash | 60s | 章节→事实提取 |

## 自检脚本（嵌入 skill，启动时运行）

```bash
# deerflow_selfcheck.sh
BRIDGE="$HOME/Workspace/Git/deer-flow/backend/.venv/bin/python3 $HOME/HermesWorkspace/deerflow_bridge.py"
if [ ! -f "$HOME/HermesWorkspace/deerflow_bridge.py" ]; then
  echo "MODE: hermes-only（bridge 脚本不存在）"
  exit 0
fi
if ! curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/health | grep -q 200; then
  echo "MODE: hermes-only（Gateway 不可达）"
  exit 0
fi
if ! $BRIDGE health 2>&1 | grep -q '"healthy": true'; then
  echo "MODE: hermes-only（Bridge 健康检查失败）"
  exit 0
fi
echo "MODE: hermes+deerflow"
```
