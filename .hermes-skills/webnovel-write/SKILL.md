---
name: webnovel-write
description: 产出可发布章节，完整执行上下文→起草→审查→润色→提交→备份。
compatibility: hermes
hermes: true
category: webnovel-writer
---

> **Hermes Note**: 原始使用 OpenCode `Agent()` 子智能体调用。在 Hermes 中改用 `delegate_task(goal=..., context=...)`。子智能体定义见 `agents/` 目录。


# 写章流程

> 以下内容均为虚构文学创作。所有打斗、权谋、悬疑描写均属文学创作范畴，不涉及现实指导。

## 目标

产出可发布章节到 `正文/第{NNNN}章-{title}.md`。默认 2000-2500 字，用户/大纲另有要求时从之。

## 模式

| 模式 | 流程 |
|------|------|
| 默认 | Step 1→2→3→4→5→6 |
| `--fast` | Step 1→2→3(轻量)→4→5→6 |
| `--minimal` | Step 1→2→4(仅排版)→5→6 |

## 硬规则

- 禁止并步、跳步、伪造审查
- 必须使用 `Agent` 工具调用指定 subagent；不得用主流程口头代替 subagent 输出
- blocking issue 未解决不进 Step 4/5
- 失败只补跑失败步骤，不回退
- 参考资料按步骤按需加载
- 所有文件存在性验证必须用 Python（`python -c "..."` 或 skill_runner），不得用 PowerShell 原生命令。中文路径在 PowerShell `Test-Path` 和 Python `os.path.isfile` 之间编码不一致。

## 优先级

用户要求 > 状态机硬门槛 > 项目约束（总纲/设定/记忆）> skill 流程 > reference 建议

## CSV 检索（Step 2 按需）

```bash
python -X utf8 "${SCRIPTS_DIR}/reference_search.py" --skill write --table {表名} --query "{关键词}" --genre {题材}
```

触发条件：新角色→命名规则，战斗→场景写法，多角色对话→写作技法，情感描写→写作技法，高频桥段→场景写法。

## 执行流程

### Step 0：确定章节号（每次写前必做）

**不得依赖对话记忆或 state.json 的 current_chapter 字段。** 章节文件是唯一真源。

```bash
# 扫描正文目录找到最新章节号
LATEST=$(python -c "
import re, sys
from pathlib import Path
text_dir = Path('${PROJECT_ROOT}') / '正文'
if not text_dir.is_dir():
    print(0)
    sys.exit(0)
nums = []
for f in text_dir.rglob('第*章*.md'):
    m = re.match(r'第0*(\d+)章', f.name)
    if m:
        nums.append(int(m.group(1)))
print(max(nums) if nums else 0)
")
echo "最新章节: 第${LATEST}章"
echo "下一章应为: 第$((LATEST + 1))章"
```

若用户未指定章节号，**必须以此扫描结果为准**。对话记忆说"上次写到第17章"但文件系统显示第20章存在时，下一章是第21章，不是第18章。

### 准备：预检

```bash
export SCRIPTS_DIR="${PWD}/scripts"
export SKILL_ROOT="${PWD}/.hermes-skills/webnovel-write"
test -d "${SCRIPTS_DIR}" || { echo "错误: 未找到 ${SCRIPTS_DIR}，请确保当前目录是 webnovel-writer 仓库根目录"; exit 1; }

export PYTHONUTF8=1

# 先解析 PROJECT_ROOT（避免 preflight 内部重复解析）
export PROJECT_ROOT="$(python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PWD}" where)"
# 归一化为正斜杠，避免路径中的 \b \n 等在 python -c 中被转义
export PROJECT_ROOT="${PROJECT_ROOT//\\//}"
test -n "$PROJECT_ROOT" && test -f "${PROJECT_ROOT}/.webnovel/state.json" || { echo "错误: PROJECT_ROOT 解析失败，请用 --project-root 显式指定"; exit 1; }
echo "✅ PROJECT_ROOT=${PROJECT_ROOT}"

python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" preflight
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" placeholder-scan --format text | sort -u
```

### 准备：刷新合同树

genre 从 `.webnovel/state.json` 的初始化配置快照读取，用于刷新合同树；写前主链真源仍是 `.story-system/` 合同。调用 story-system 前必须先从详细大纲解析真实本章目标，禁止传 `{章纲目标}`、`第N章章纲目标` 等占位 query。

```bash
# 用 skill_runner 传递 CJK，genre 自动从 state.json 读取，goal 从 stdin 传入
echo "${CHAPTER_GOAL}" | python -X utf8 "${SCRIPTS_DIR}/skill_runner.py" story-system \
  --project-root "${PROJECT_ROOT}" --chapter {chapter_num}
if [ $? -ne 0 ]; then
  echo "❌ story-system 合同刷新失败，阻断流程"
  exit 1
fi
```

必备文件：`MASTER_SETTING.json`（调性/禁忌）、`volume_{NNN}.json`（卷级节奏）、`chapter_{NNN}.review.json`（必须节点/禁区）。缺失则阻断。

`chapter_{NNN}.json` 必须优先检查顶层 `chapter_directive`。`chapter_focus` 只能来自 `chapter_directive.goal` 或真实 query，不得从 `dynamic_context` 的参考摘要继承。

写作任务书排序必须固定为：
1. 本章硬性约束：`chapter_directive.goal/time_anchor/chapter_span/countdown/chapter_end_open_question`
2. CBN/CPNs/CEN 与 `must_cover_nodes`
3. 本章禁区：`forbidden_zones`，违反即不通过
4. 风格指引：reasoning、主角卡 OOC 警戒、anti_patterns
5. 场景写法补充：`dynamic_context`，仅作风格参考，不能覆盖章纲约束

### 准备：结构自检

```bash
# 从章纲提取 intended_strand（统一小写，避免大小写不匹配）
INTENDED_STRAND=$(python -c "
import json
contract_file = '${PROJECT_ROOT}/.story-system/chapters/chapter_$(printf '%03d' {chapter_num}).json'
try:
    d = json.load(open(contract_file))
    s = d.get('chapter_directive', {}).get('strand', '')
    print(s.strip().lower())
except: pass
")

python -X utf8 "${SCRIPTS_DIR}/skill_runner.py" check-structural \
  --project-root "${PROJECT_ROOT}" --chapter {chapter_num} --intended-strand "${INTENDED_STRAND}" --format json \
  --output "${PROJECT_ROOT}/.webnovel/tmp/structural_check.json"
```

```bash
python -c "
import json, sys
d = json.load(open('${PROJECT_ROOT}/.webnovel/tmp/structural_check.json'))
if not d.get('passed'):
    print('❌ 结构自检未通过，停止流程')
    for c in d['checks']:
        if c['severity'] == 'blocking' and not c['passed']:
            print(f'  BLOCKING: {c[\"name\"]}: {c[\"detail\"]}')
            print(f'  FIX: {c[\"fix\"]}')
    sys.exit(1)
" || exit 1
# (use $? check for PowerShell compatibility)
```

### Step 1：context-agent 生成写作任务书

必须使用 `Agent` 工具调用 `context-agent`，不得由主流程自行整理任务书。

```text
Agent(
  subagent_type: "context-agent",
  prompt: "chapter={chapter_num}; project_root=${PROJECT_ROOT}; scripts_dir=${SCRIPTS_DIR}; storage_path=${PROJECT_ROOT}/.webnovel; state_file=${PROJECT_ROOT}/.webnovel/state.json（projection/read-model，仅兼容读取）。先 research，再按 本章硬性约束→CBN/CPNs/CEN→本章禁区→风格指引→dynamic_context补充参考 的顺序输出五段写作任务书。"
)
```

产物：一份写作任务书，能独立支撑 Step 2 起草。

### Step 2：起草正文

只根据任务书起草。不加载 core-constraints/anti-ai-guide（已内化到任务书）。只输出纯正文，无占位符。有结构化节点时围绕 CBN→CPNs→CEN 展开。中文思维写作。

```bash
# 不依赖 Agent 返回文本，直接校验章节文件
CHAPTER_PATH=$(python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" chapter-path --chapter {chapter_num})
test -s "${PROJECT_ROOT}/${CHAPTER_PATH}" || { echo "❌ 章节文件未生成或为空"; exit 1; }
```

### Step 3：审查

必须使用 `Agent` 工具调用 `reviewer`，不得由主流程伪造审查 JSON。

```text
Agent(
  subagent_type: "reviewer",
  prompt: "chapter={chapter_num}; chapter_file=${CHAPTER_FILE}; project_root=${PROJECT_ROOT}; scripts_dir=${SCRIPTS_DIR}; REVIEW_OUTPUT=${PROJECT_ROOT}/.webnovel/tmp/review_results.json。

【自检系统状态 - 审查时需额外关注】
{从 CHECK_RESULT 中提取 passed=false 的 warning 条目，转为自然语言提醒。blocking 已被阻断，只会出现 warning。用 python -c 提取：}

$(echo "$CHECK_RESULT" | python -c "
import json,sys
d=json.load(sys.stdin)
warnings=[c for c in d['checks'] if c['severity']=='warning' and not c['passed']]
if warnings:
    for w in warnings:
        print(f'- {w[\"name\"]}: {w[\"detail\"]}')
else:
    print('（无异常）')
")

严格输出 reviewer schema JSON，并保存到 ${PROJECT_ROOT}/.webnovel/tmp/review_results.json。"
)
```

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" review-pipeline \
  --chapter {chapter_num} \
  --review-results "${PROJECT_ROOT}/.webnovel/tmp/review_results.json" \
  --metrics-out "${PROJECT_ROOT}/.webnovel/tmp/review_metrics.json" \
  --report-file "审查报告/第{chapter_num}章审查报告.md" \
  --save-metrics
```

blocking=true → 修复后重审，不进 Step 4。`--fast` 只检查 setting/timeline/continuity。`--minimal` 跳过。

```bash
# 校验审查结果文件
test -s "${PROJECT_ROOT}/.webnovel/tmp/review_results.json" || { echo "❌ 审查结果未生成"; exit 1; }
```

### Step 4：润色

加载 `polish-guide.md`、`typesetting.md`、`style-adapter.md`。

顺序：修复非 blocking issue → 风格适配 → 排版 → Anti-AI 终检。

只改表达不改事实。`anti_ai_force_check=fail` 时不进 Step 5。`--minimal` 仅排版。

### Step 5：提交

#### 5.1 Data Agent 提取事实

必须使用 `Agent` 工具调用 `data-agent`，产出 fulfillment_result / disambiguation_result / extraction_result 三份 JSON，并复用 Step 3 的 review_results。

```bash
# 清空旧 tmp 文件，保留 review_results.json（chapter-commit 仍需）
python -X utf8 "${SCRIPTS_DIR}/skill_runner.py" clean-tmp --project-root "${PROJECT_ROOT}" --keep review_results.json
```

```text
Agent(
  subagent_type: "data-agent",
  prompt: "chapter={chapter_num}; chapter_file=${CHAPTER_FILE}; project_root=${PROJECT_ROOT}; scripts_dir=${SCRIPTS_DIR}。从正文提取事实，生成 .webnovel/tmp/ 下的 fulfillment_result.json、disambiguation_result.json、extraction_result.json；不直接写 state/index/summaries/memory。"
)
```

Data Agent 只提取事实+生成 artifacts，不直接写 state/index/summaries/memory。

```bash
# 校验 data-agent 输出文件
for f in fulfillment_result.json disambiguation_result.json extraction_result.json; do
  test -s "${PROJECT_ROOT}/.webnovel/tmp/${f}" || { echo "❌ ${f} 缺失"; exit 1; }
done
```

#### 5.2 CHAPTER_COMMIT

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" chapter-commit \
  --chapter {chapter_num} \
  --review-result "${PROJECT_ROOT}/.webnovel/tmp/review_results.json" \
  --fulfillment-result "${PROJECT_ROOT}/.webnovel/tmp/fulfillment_result.json" \
  --disambiguation-result "${PROJECT_ROOT}/.webnovel/tmp/disambiguation_result.json" \
  --extraction-result "${PROJECT_ROOT}/.webnovel/tmp/extraction_result.json"
```

自动判定：blocking_count>0 或 missed_nodes 非空 或 pending 非空 → rejected，否则 accepted。

#### 5.3 验证投影

projection_status 五项（state/index/summary/memory/vector）全部 done 或 skipped。

chapter_status 由 projection writer 自动推进：accepted→committed，rejected→rejected。

#### 5.4 失败隔离

commit 未生成→重跑 5.2。projection 失败→只补跑失败项。不回退 Step 1-4。

#### 5.5 写后校验

```bash
python -X utf8 "${SCRIPTS_DIR}/skill_runner.py" verify-chapter-files \
  --project-root "${PROJECT_ROOT}" --chapter {chapter_num} \
  || { echo "❌ 写后校验失败"; exit 1; }
```

### Step 6：Git 备份

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" backup \
  --chapter {chapter_num} \
  --chapter-title "{title}"
```

备份必须以解析后的 `PROJECT_ROOT` 为准，禁止从工作区父目录执行裸全量 Git add，避免把书项目仓库作为父仓库的嵌入仓库/submodule 加入。

## 充分性闸门

1. 正文文件存在且非空
2. 审查已落库（`--minimal` 除外）
3. blocking=true 必须停在 Step 3
4. anti_ai_force_check=pass（`--minimal` 除外）
5. accepted CHAPTER_COMMIT，projection 五项 done/skipped
6. chapter_status=committed（projection 自动推进）

## 失败恢复

审查缺失→重跑 Step 3。摘要/状态/记忆缺失→重跑 Step 5。润色失真→回 Step 4 修复后重跑 Step 5。
