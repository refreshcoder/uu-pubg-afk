# 共享 YAML 配置（Rust Linux + UU Windows）设计

## 目标

- 将 `rustdesk_pubg_afk.py` 与 `uu_pubg_afk.py` 中的默认循环间隔、连接延迟、键鼠动作参数、随机数范围等统一抽取到公共 YAML 配置文件中
- 两端脚本默认使用同一份配置（完全通用一份），并允许通过环境变量指定自定义配置路径
- 新增定时退出能力：脚本在运行 6 小时 5 分钟后自动退出

## 非目标

- 不引入平台覆盖配置（不做 `common + platform override` 结构）
- 不改动 RustDesk 连接方式、窗口识别算法、进程守护策略
- 不新增 OCR 相关逻辑与依赖

## 现状与差异（需要统一）

- 循环间隔
  - Rust：`280-320s`
  - UU：`120-180s`
- 窗口初始化等待
  - Rust：检测到远控窗口后固定等待 `15s`
  - UU：无显式等待
- 鼠标/右键操作
  - Rust：包含右键长按 + 双击右键（2-4s 间隔）
  - UU：当前无右键操作

统一策略：以 Rust 默认值为准，UU 同步执行 Rust 的右键动作序列。

## 配置文件

### 文件名与位置

- 默认：仓库根目录 `config.yaml`
- 可覆盖：环境变量 `PUBG_AFK_CONFIG` 指向任意 YAML 路径

### YAML 结构（建议）

```yaml
run:
  auto_exit_after_seconds: 21900

loop:
  interval_seconds:
    min: 280
    max: 320
  window_init_wait_seconds: 15

movement:
  mouse:
    offset_x:
      min: -60
      max: 60
    offset_y:
      min: -20
      max: 20
    move_duration_seconds: 0.1
    right_click:
      hold_seconds: 0.1
      double_click_interval_seconds:
        min: 2
        max: 4

  keyboard:
    wasd_keys: ["w", "s", "a", "d"]
    hold_seconds:
      min: 0.1
      max: 0.18
    opp_sleep_seconds: 0.05

    qe_keys: ["q", "e"]
    qe_times:
      min: 2
      max: 5
    qe_hold_seconds:
      min: 0.03
      max: 0.07
    qe_interval_seconds:
      min: 0.05
      max: 0.15

rustdesk:
  connection:
    connect_timeout_seconds: 30
    connect_retries: 3
```

说明：
- `rustdesk.*` 字段对 UU 端无意义，允许 UU 忽略，但保留在同一份 YAML 中以保证“单文件统一管理”。
- 所有区间字段遵循闭区间随机（`randint` 或 `uniform`）语义。

## 代码结构

### 新增模块

- `config_loader.py`
  - `load_config() -> dict`：读取 YAML、合并默认值、做最小类型校验
  - 在读取失败/缺字段时，回退到代码内置默认值，确保脚本可用性

### 两脚本改动点

- `rustdesk_pubg_afk.py`
  - `CONNECT_TIMEOUT_SECONDS / CONNECT_RETRIES` 替换为 `config['rustdesk']['connection']`
  - 检测到远控窗口后的等待 `time.sleep(15)` 替换为 `config['loop']['window_init_wait_seconds']`
  - 循环间隔 `random.randint(280, 320)` 替换为 `config['loop']['interval_seconds']`
  - `safety_movement()` 内所有随机范围与动作时长全部从 `movement.*` 读取
  - 定时退出
    - 记录启动时间 `start_ts`
    - 每轮开始时判断 `(time.time() - start_ts) >= auto_exit_after_seconds`
    - 若触发：执行断开连接清理逻辑后退出

- `uu_pubg_afk.py`
  - 循环间隔统一改为 `280-320s`，从 `config['loop']['interval_seconds']` 读取
  - 新增与 Rust 一致的鼠标右键序列（长按右键 + 双击右键）
  - `safety_movement()` 内所有随机范围与动作时长全部从 `movement.*` 读取
  - 定时退出
    - 记录启动时间 `start_ts`
    - 每轮开始时判断 `(time.time() - start_ts) >= auto_exit_after_seconds`
    - 若触发：自然走本轮 `finally` 恢复桌面状态后退出

## 依赖与脚本安装

- 引入 YAML 解析依赖：`PyYAML`
  - Windows：加入 `requirements.txt`
  - Linux：加入 `requirements_rustdesk.txt`（`install_and_run.sh` 安装该文件）

## 错误处理策略

- 配置文件不存在/解析失败：打印提示并使用内置默认值继续运行
- 配置字段类型不合法：针对该字段回退默认值，不影响其他字段
- 定时退出：确保退出前执行必要的断开/窗口清理（RustDesk 断开连接窗口、UU 恢复窗口/鼠标）

## 验收标准

- 两脚本默认读取 `config.yaml`，且无需命令行参数即可生效
- 将 Rust/UU 中涉及到的默认区间与固定等待全部迁移到 YAML（代码中不再散落硬编码常量）
- UU 与 Rust 行为在“动作序列/随机范围/间隔”层面保持一致（平台差异仅体现在底层注入实现）
- 两脚本均在运行达到 21900 秒后自动退出

