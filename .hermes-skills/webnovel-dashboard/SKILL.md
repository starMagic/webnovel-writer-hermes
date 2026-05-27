---
name: webnovel-dashboard
description: 启动只读小说管理面板，查看项目状态、实体图谱与章节内容。
compatibility: hermes
hermes: true
category: webnovel-writer
---


# Webnovel Dashboard

## 目标

在本地启动只读 Web 面板，查看创作进度、设定词典、关系图谱、章节内容与追读力数据。

## 环境设置

```bash
# 以下命令假设当前目录为 webnovel-writer 仓库根目录
export SCRIPTS_DIR="${PWD}/scripts"
export DASHBOARD_DIR="${PWD}/.opencode/dashboard"
test -d "${DASHBOARD_DIR}" || { echo "错误: 未找到 ${DASHBOARD_DIR}，请确保当前目录是 webnovel-writer 仓库根目录"; exit 1; }
```

## 执行流程

### Step 1：安装依赖

```bash
python -m pip install -r "${DASHBOARD_DIR}/requirements.txt" --quiet
```

### Step 2：解析项目路径 + 校验前端

```bash
export PROJECT_ROOT="$(python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PWD}" where)"
test -n "$PROJECT_ROOT" && test -f "${PROJECT_ROOT}/.webnovel/state.json" || { echo "错误: PROJECT_ROOT 解析失败，请用 --project-root 显式指定"; exit 1; }
echo "项目路径: ${PROJECT_ROOT}"

test -f "${DASHBOARD_DIR}/frontend/dist/index.html" || { echo "错误: 缺少前端构建产物 ${DASHBOARD_DIR}/frontend/dist/index.html"; exit 1; }
```

### Step 3：启动 Dashboard（后台运行）

> Dashboard 是长运行服务（uvicorn），必须用后台模式启动。命令中设置 `run_in_background: true`。

```bash
PYTHONPATH="${PWD}/.opencode" python -X utf8 -m dashboard.server --project-root "${PROJECT_ROOT}"
```

默认端口 8765，访问 `http://127.0.0.1:8765`。

自定义端口：
```bash
PYTHONPATH="${PWD}/.opencode" python -X utf8 -m dashboard.server --project-root "${PROJECT_ROOT}" --port 9000 --no-browser
```

### Step 4：验证服务

```bash
curl -s http://127.0.0.1:8765/api/preflight || echo "服务未启动，请检查端口是否被占用"
```

## 注意事项

- Dashboard 为纯只读面板，不提供修改任何项目数据的接口
- uvicorn 默认监听 `127.0.0.1:8765`
- 首次启动可能需安装依赖（`pip install -r requirements.txt`）
- Windows 中文输出乱码：运行 `chcp 65001` 后重试

## 失败恢复

| 故障 | 恢复方式 |
|------|---------|
| 依赖安装失败 | 检查 Python 版本，手动 `pip install -r requirements.txt` |
| 前端 `dist/` 缺失 | 确认插件完整安装 |
| PROJECT_ROOT 解析失败 | 显式传 `--project-root` 或检查 `.opencode/.webnovel-current-project` 指针 |
| 端口占用 | 使用 `--port <其他端口>` |
| 服务被 timeout 终止 | 确保使用后台模式（`run_in_background: true`）启动 |
| 页面空白/数据缺失 | 确认 `.webnovel/` 下有 state.json、index.db 等数据文件 |
