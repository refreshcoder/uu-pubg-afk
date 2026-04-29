# WebUI：多设备远控挂机控制台（技术方案）

## 1. 总体架构

采用“单进程 Web 服务 + 设备 Runner 子进程”的架构：
- Web 服务提供 UI（静态资源/服务端渲染皆可）与 API
- 每台设备启动时由 Web 服务启动一个独立的脚本子进程（runner）
- Web 服务负责：
  - 设备配置落盘
  - 子进程生命周期管理（启动/停止/状态/退出码）
  - 截图文件目录管理（最近 10 张）
  - 日志落盘与 UI 展示

## 2. 技术栈选择

**后端：**
- Python 3.10+
- FastAPI（HTTP API）
- Uvicorn（ASGI server）
- PyYAML（读取/合并配置）

**前端：**
- MVP：使用服务端渲染（Jinja2）或纯静态 HTML + 少量原生 JS 调用 API
- 不引入复杂前端构建链，保证部署简单

## 3. 目录结构（建议）

```
/workspace
  webui/
    app.py
    templates/
    static/
  data/
    devices.yaml
    runtime/
      <device_key>/
        effective_config.yaml
        screenshots/
        logs/
```

说明：
- `devices.yaml`：持久化设备配置（名称、id、password、override_config 等）
- `runtime/<device_key>/effective_config.yaml`：每次启动时生成的最终配置
- `screenshots/`：每台设备最近 10 张截图
- `logs/`：每台设备运行日志（stdout/stderr 重定向到文件）

## 4. 数据模型

### 4.1 Device（持久化）
- `key`：设备唯一键（slug/uuid）
- `name`：展示名
- `target_id`：RustDesk 被控端 ID
- `target_password`：RustDesk 被控端密码
- `override_config_yaml`：设备覆盖配置（YAML 文本，覆盖 `config.yaml`）

### 4.2 Runtime（内存态）
- `pid` / `process`
- `started_at`
- `expected_end_at`（由 N 小时 M 分换算）
- `status`：`stopped | running | exited | error`
- `last_exit_code`
- `last_error`

## 5. API 设计（示例）

- `GET /api/devices`：列表
- `POST /api/devices`：新增
- `PUT /api/devices/{key}`：更新
- `DELETE /api/devices/{key}`：删除

- `POST /api/devices/{key}/start`：启动（body: `{hours, minutes}`）
- `POST /api/devices/{key}/stop`：停止
- `GET /api/devices/{key}/status`：状态
- `GET /api/devices/{key}/screenshots`：截图列表（最近 10）

## 6. Runner 启动方式

### 6.1 RustDesk（Linux）默认

Web 服务启动子进程：
- 可执行：`python3 rustdesk_pubg_afk.py`
- 参数：
  - `--target-id`
  - `--target-password`
  - `--display`（由环境/配置决定）
- 环境变量：
  - `PUBG_AFK_CONFIG` 指向生成的 `effective_config.yaml`
  - `PUBG_AFK_DEVICE_KEY`（可选：用于日志前缀/截图目录）
  - `PUBG_AFK_SCREENSHOT_DIR`（可选：截图输出目录）

### 6.2 UU（Windows）扩展点

未来可扩展 runner 类型：
- `python uu_pubg_afk.py`
- Windows 截图方案另行实现

## 7. 截图实现策略

为避免引入重型 OCR 依赖，截图做成“可选能力”：
- Runner 在每次执行 `safety_movement()` 后尝试保存截图
- 若截图工具不可用，则记录日志但不中断主流程

Linux 方案优先级：
1) `scrot <path>`（依赖 `scrot` 包）
2) 备选：`import -window root <path>`（依赖 ImageMagick）

截图留存策略：
- 每次保存后扫描目录，按时间排序，超过 10 张则删除最旧

## 8. 并发与进程管理

- Web 服务内维护 `device_key -> subprocess.Popen` 的映射
- 启动：
  - 若设备已在运行，返回 409 或提示“已运行”
- 停止：
  - 优先发送 `SIGTERM`（Linux）/ `terminate()`（Windows）
  - 超时后 `kill()`
- 进程退出监听：
  - 通过后台线程/async task 轮询 `poll()` 更新状态

## 9. 安全与权限

- 默认仅监听 `127.0.0.1`，如需远程访问由用户自行反代并加鉴权
- `devices.yaml` 与 `runtime/` 目录建议设置为仅当前用户可读写（600/700）
- UI 展示中对 ID 进行部分脱敏（例如仅显示后 4 位）

## 10. 可观测性

- 每台设备 stdout/stderr 重定向到 `runtime/<device>/logs/run.log`
- UI 提供“最近日志片段”查看（MVP 可只展示最后 200 行）

