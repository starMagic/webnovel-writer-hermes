# 批量写作协议

## 概述

批量写作（Batch Write）是网文写作系统的扩展功能，允许用户一次执行多个章节的连续写作，同时保持断点安全和灵活的质量控制。

## batch_state.json Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["task_id", "range", "status", "created_at"],
  "properties": {
    "task_id": {
      "type": "string",
      "description": "批量任务唯一标识，格式：batch_YYYYMMDD_HHMMSS",
      "pattern": "^batch_\\d{8}_\\d{6}$"
    },
    "range": {
      "type": "object",
      "required": ["start", "end"],
      "properties": {
        "start": {
          "type": "integer",
          "description": "起始章节号"
        },
        "end": {
          "type": "integer",
          "description": "结束章节号"
        }
      }
    },
    "mode": {
      "type": "string",
      "enum": ["minimal", "standard", "full"],
      "description": "审查级别"
    },
    "status": {
      "type": "string",
      "enum": ["running", "completed", "failed", "stopped", "paused"],
      "description": "任务状态"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "任务创建时间（ISO 8601）"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "最后更新时间（ISO 8601）"
    },
    "current_chapter": {
      "type": "integer",
      "description": "当前正在执行的章节号"
    },
    "completed_chapters": {
      "type": "array",
      "items": {"type": "integer"},
      "description": "已完成章节列表"
    },
    "failed_chapters": {
      "type": "array",
      "items": {"type": "integer"},
      "description": "失败章节列表"
    },
    "chapter_results": {
      "type": "object",
      "description": "各章节结果详情",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "status": {
            "type": "string",
            "enum": ["success", "failed", "skipped"]
          },
          "score": {
            "type": "number",
            "description": "审查分数"
          },
          "words": {
            "type": "integer",
            "description": "字数"
          },
          "duration_seconds": {
            "type": "integer",
            "description": "耗时（秒）"
          },
          "completed_at": {
            "type": "string",
            "format": "date-time"
          },
          "error": {
            "type": "string",
            "description": "错误信息（如果失败）"
          }
        }
      }
    },
    "stop_reason": {
      "type": ["string", "null"],
      "description": "停止原因"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "review_level": {
          "type": "string"
        },
        "stop_on_fail": {
          "type": "boolean"
        },
        "force": {
          "type": "boolean"
        },
        "user_id": {
          "type": "string",
          "description": "用户标识"
        }
      }
    }
  }
}
```

## 任务状态机

```
                    ┌─────────────┐
                    │   created   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
              ┌─────│   running   │─────┐
              │     └─────────────┘     │
              │                         │
              ▼                         ▼
      ┌───────────────┐         ┌───────────────┐
      │   completed  │         │   stopped    │
      └───────────────┘         └───────┬───────┘
                                        │
                                        ▼
                                  ┌───────────────┐
                                  │    paused     │
                                  └───────┬───────┘
                                          │
                                          ▼
                                    (resume)
```

### 状态转换规则

| 当前状态 | 事件 | 目标状态 | 说明 |
|---------|------|---------|------|
| created | 开始执行 | running | 任务启动 |
| running | 所有章节完成 | completed | 成功完成 |
| running | 单章失败 + stop_on_fail | stopped | 被迫停止 |
| running | 用户中断 | paused | 暂停 |
| stopped | 用户恢复 | running | 继续执行 |
| paused | 用户恢复 | running | 继续执行 |
| completed | - | - | 终态 |

## 恢复策略

### 检测中断

```bash
# 检查 batch_state.json 是否存在且 status != completed
if [ -f "$BATCH_STATE_FILE" ]; then
    STATUS=$(python -c "import json; d=json.load(open('${BATCH_STATE_FILE}')); print(d.get('status'))")
    if [ "$STATUS" != "completed" ]; then
        echo "检测到中断任务: $STATUS"
    fi
fi
```

### 恢复选项

| 选项 | 适用状态 | 说明 |
|------|---------|------|
| **继续当前章节** | running, stopped | 从当前章节重新开始 |
| **跳过已完成章节** | running, stopped | 从下一章开始 |
| **重新开始** | any | 清空状态，重新执行 |
| **仅查看报告** | any | 显示 batch_state 内容 |

### 恢复决策树

```
                    检测到 batch_state
                           │
                           ▼
                    ┌──────────────┐
                    │ status ==    │
                    │ completed?   │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
             Yes                        No
              │                         │
              ▼                         ▼
      ┌──────────────┐         ┌──────────────┐
      │ 显示报告     │         │ status ==    │
      │ 询问退出    │         │ failed?      │
      └──────────────┘         └──────┬───────┘
                                       │
                              ┌────────┴────────┐
                              │                 │
                             Yes               No
                              │                 │
                              ▼                 ▼
                      ┌────────────┐   ┌──────────────┐
                      │ 显示失败   │   │ 显示恢复选项 │
                      │ 询问重试   │   │ 继续/跳过/   │
                      └────────────┘   │ 重新开始    │
                                       └────────────┘
```

## 与 workflow_state.json 的交互

批量任务与单章任务共享 `.webnovel/workflow_state.json`：

### 注册批量任务

```python
# workflow_manager.py
def start_batch_task(task_id: str, range_start: int, range_end: int, mode: str):
    state = load_state()
    state.setdefault("batch_tasks", {})
    state["batch_tasks"][task_id] = {
        "range": {"start": range_start, "end": range_end},
        "mode": mode,
        "status": "running",
        "started_at": now_iso(),
        "current_chapter": range_start,
        "completed_chapters": [],
        "failed_chapters": []
    }
    save_state(state)
```

### 更新批量进度

```python
def update_batch_progress(task_id: str, chapter: int, result: Dict):
    state = load_state()
    batch = state.get("batch_tasks", {}).get(task_id)
    if not batch:
        return
    
    batch["current_chapter"] = chapter + 1
    
    if result.get("status") == "success":
        batch["completed_chapters"].append(chapter)
    else:
        batch["failed_chapters"].append(chapter)
        if result.get("stop_on_fail"):
            batch["status"] = "stopped"
    
    save_state(state)
```

## 命令行接口

### 参数规范

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--range` | 是 | - | 章节范围，格式：start-end |
| `--review-level` | 否 | standard | 审查级别 |
| `--stop-on-fail` | 否 | true | 失败时停止 |
| `--resume` | 否 | false | 恢复模式 |
| `--force` | 否 | false | 绕过上限 |

### 示例

```bash
# 基本批量写作
/webnovel-write-batch --range 53-60

# 快速模式
/webnovel-write-batch --range 53-60 --review-level minimal

# 完整审查
/webnovel-write-batch --range 53-60 --review-level full

# 失败继续执行
/webnovel-write-batch --range 53-60 --no-stop-on-fail

# 恢复中断任务
/webnovel-write-batch --resume

# 强制执行 30 章
/webnovel-write-batch --range 53-82 --force
```

## 错误处理

### 错误级别

| 级别 | 处理方式 | 示例 |
|------|---------|------|
| **critical** | 停止批量任务 | 章节文件为空、state.json 损坏 |
| **high** | 记录但继续 | 审查分数低于 60 |
| **medium** | 警告但继续 | 缺少章节大纲 |
| **low** | 仅记录 | Git 提交警告 |

### 错误恢复

```python
ERROR_RECOVERY = {
    "chapter_file_missing": "重新执行当前章节的 Step 2A",
    "review_metrics_failed": "重新执行当前章节的 Step 3",
    "state_write_failed": "重试 3 次后停止",
    "git_commit_failed": "记录但继续，不阻断"
}
```

## 性能指标

### 基准值

| 指标 | 目标值 | 警告阈值 |
|------|--------|---------|
| 单章平均耗时 | 60-120 秒 | > 300 秒 |
| 批量成功率 | 100% | < 95% |
| 审查分数均值 | >= 80 | < 70 |

### 日志记录

```json
{
  "timestamp": "2026-04-10T10:30:00Z",
  "event": "batch_chapter_completed",
  "task_id": "batch_20260410_103000",
  "chapter": 53,
  "duration_seconds": 85,
  "score": 87,
  "words": 2340
}
```

## 安全约束

1. **并发限制**：同一时间只能有一个活跃的批量任务
2. **上限保护**：默认 20 章上限，防止资源耗尽
3. **状态持久化**：每章完成后立即保存状态
4. **原子性**：Git 提交保证章节级别的可回滚性
