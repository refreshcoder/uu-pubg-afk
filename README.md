# UU / RustDesk PUBG Anti-AFK (绝地求生 远程防掉线助手)

这是一个专为“UU远程”和“RustDesk”等远程控制软件设计的 PUBG (绝地求生) 防掉线/防踢出自动化脚本。

由于脚本运行在**主控机**（您正在使用的电脑）而非游戏运行的被控机上，它通过物理级别的图像识别和系统级键鼠模拟来工作，最大限度保证了账号的安全（无游戏内存修改，不触碰反作弊系统）。

该项目目前包含两套脚本：
- `uu_pubg_afk.py`：针对 **Windows** 环境下使用 **UU远程** 的场景。
- `rustdesk_pubg_afk.py`：针对 **Linux** 环境下使用 **RustDesk** 的场景。

## ✨ 核心特性

- 🎯 **智能窗口锁定**：精准锁定实际的远程桌面推流窗口。
- 🚶 **极微量位移抵消**：采用“0.1秒按键+反向补偿”的镜像抵消算法，确保角色在游戏中原地踏步，不乱跑。
- 🖱️ **防失焦鼠标微动**：计算窗口几何中心进行相对微调，防止鼠标随时间推移甩出远程窗口导致失焦。
- ⚡ **主控机资源优化机制**：
  - **Windows (零打扰)**：在每一轮操作前，强行唤醒并置顶 UU 远程窗口执行极短的键鼠动作，完成后立刻将焦点和鼠标位置还给用户，并将远程窗口最小化，不影响您平时看网页或工作。
  - **Linux (随用随连)**：采用“按需连接”生命周期管理机制，每次循环先唤醒 RustDesk 建立连接，动作执行完毕后自动断开并销毁窗口，极大节省服务器带宽和性能。
- ☁️ **全自动无头服务器支持**：对于没有物理显示器的云服务器（如 Ubuntu/Debian Server），一键脚本会自动搭建 Xvfb 虚拟显示器和 x11vnc 环境，支持无缝挂机。

## 🛠️ 安装说明

### Windows (UU 远程版)
我们为您提供了一个一键安装与运行 PowerShell 脚本，它会自动检测/安装 Python，创建虚拟环境并启动防掉线功能。

1. 克隆本仓库或下载源码到本地：
   ```bash
   git clone https://github.com/yourusername/uu-pubg-afk.git
   cd uu-pubg-afk
   ```
2. **小白一键启动 (推荐)**：
   以**管理员身份**打开 PowerShell（按 Win 键搜索 PowerShell，右键“以管理员身份运行”），然后执行以下命令：
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_uu_pubg_afk.ps1
   ```

*(如果您希望手动控制依赖和环境，请参考下方的详细手动启动步骤：)*
3. **详细手动启动**：
   确保已安装 [Python 3.10+](https://www.python.org/downloads/)。
   在终端中运行以下命令创建虚拟环境并安装依赖：
   ```bash
   python -m venv venv_win
   venv_win\Scripts\activate
   pip install -r requirements.txt
   python uu_pubg_afk.py
   ```

### Linux (RustDesk 远控版 - 纯 CLI/云主机无头兼容)

我们为您提供了一个一键安装与运行脚本，该脚本会自动处理所有系统级依赖（xdotool, xvfb 等）、创建 Python 虚拟环境、配置加速源安装库并交互式启动：

1. 克隆并进入目录：
   ```bash
   git clone https://github.com/yourusername/uu-pubg-afk.git
   cd uu-pubg-afk
   ```
2. 赋予脚本执行权限并运行：
   ```bash
   chmod +x install_and_run.sh
   ./install_and_run.sh
   ```
   
可选：把被控端 ID/密码写入 `.env`，避免每次运行脚本都手输（不要提交真实 `.env` 到仓库）：
```bash
cp .env.example .env
```
如果你使用自建 RustDesk Server OSS，需要在 `.env` 中额外填写 `RUSTDESK_ID_SERVER`、`RUSTDESK_RELAY_SERVER`、`RUSTDESK_KEY`，脚本会自动写入 RustDesk 的配置文件并应用。相关字段含义可参考 RustDesk 的自建服务器客户端配置说明。 [rustdesk.com docs](https://rustdesk.com/docs/en/self-host/client-configuration/)。
3. **对于拥有桌面环境的 Linux**：按下回车键（默认 `:0` 号显示器）即可。
4. **对于纯命令行/无桌面的服务器（如云主机/Debian Server）**：脚本将全自动为您在后台完成以下操作：
   - 自动检测并下载安装 `rustdesk` 客户端 (如果系统尚未安装)
   - 创建 `:99` 虚拟显示器 (Xvfb)
   - 开启无密码的 VNC 远程桌面服务 (x11vnc)
   - 提示您输入目标电脑的 RustDesk ID 和密码
   - **自动启动 RustDesk 客户端并传入参数连接到您的游戏机**
   - *随后您只需用本地电脑上的 VNC Viewer 连入服务器 IP 的 `5900` 端口确认画面，然后在 SSH 终端回车让脚本接管即可。真正的一键无头挂机！*

### 独立连接检测工具 (可选)
为了方便排查 RustDesk 在无头环境的连接问题，项目中提供了一个独立的检测工具 `rustdesk_connect_check.sh`。它能拉起 RustDesk 并分析窗口状态和底层报错，给出友好的失败原因（如密码错误、P2P穿透失败等）：
```bash
./rustdesk_connect_check.sh <您的远控ID> <您的密码> :99
```

## 🚀 使用指南

1. **准备工作**：在被控机（游戏机）打开 PUBG，建议让角色在安全区域**面壁站立**（这样可以利用游戏内的物理碰撞体积进一步防止位移误差）。
2. **连接远程**：在主控机打开远程软件（UU远程 或 RustDesk）并连接到被控机，确保能看到游戏画面。
3. **运行脚本**：
   - **Windows (UU远程)**：请参考上方 [安装说明 - 小白一键启动] 的指令，在 PowerShell 以管理员权限执行 `run_uu_pubg_afk.ps1`。
   - **Linux (RustDesk)**：通过一键脚本运行：
     ```bash
     ./install_and_run.sh
     ```
     *(如果您是通过 SSH 运行，且桌面的 DISPLAY 并非默认的 `:0`，请在运行后的提示中输入：`:1`)*
4. **停止运行**：在终端中按下 `Ctrl + C` 即可安全停止脚本。

## ⚙️ 公共配置 (config.yaml)

仓库根目录提供一份公共配置文件 `config.yaml`，用于同时控制 Windows(UU) 与 Linux(RustDesk) 两套脚本的默认行为（循环间隔、窗口初始化等待、键鼠动作随机范围等）。

如需在不改动仓库文件的情况下切换配置，可通过环境变量指定自定义路径：

- Windows (PowerShell)
  ```powershell
  $env:PUBG_AFK_CONFIG = "D:\path\to\config.yaml"
  ```
- Linux (bash)
  ```bash
  export PUBG_AFK_CONFIG=/path/to/config.yaml
  ```

### 自动退出

`config.yaml` 中的 `run.auto_exit_after_seconds` 控制脚本自动退出时间。

- 默认：`21900` 秒（6 小时 5 分钟）
- 设置为 `0`：表示不自动退出

## 🖥️ WebUI（多设备控制）

如果你需要在一台 Linux 主控机上同时管理多台 RustDesk 设备（配置 ID/密码、每台设备独立参数、可视化启动/停止、截图留存），可以使用本仓库内置的 WebUI。

### 小白版（推荐）

1. 安装 WebUI 依赖：
   ```bash
   python3 -m pip install -r requirements_webui.txt
   ```
2. 启动 WebUI（默认仅本机可访问）：
   ```bash
   python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8000
   ```
3. 浏览器打开：
   - `http://127.0.0.1:8000/`
4. 在页面中新增设备，填写设备名称、RustDesk ID、密码，然后点击“开始”，输入运行时长（小时/分钟）。

### 详细版（可配置项说明）

- 数据落盘目录：
  - 默认：`./data/`（设备配置保存在 `data/devices.yaml`，运行日志/截图保存在 `data/runtime/<device>/`）
  - 可通过环境变量覆盖：`PUBG_AFK_DATA_DIR=/path/to/data`
- 每台设备的独立配置：
  - 在设备编辑页填写“覆盖配置（YAML）”，该 YAML 会与仓库根目录的 `config.yaml` 深度合并
  - 每次点击“开始”时，WebUI 会将本次运行时长写入 `run.auto_exit_after_seconds`
- 截图机制：
  - WebUI 启动脚本时会自动设置 `PUBG_AFK_SCREENSHOT_DIR`
  - 脚本会在每次防掉线动作后尝试保存一张 PNG，并仅保留最近 10 张
  - Linux 推荐安装 `scrot`（`install_and_run.sh` 已包含）

当前版本 WebUI 的 runner 默认对接 **Linux + RustDesk** 场景；Windows(UU) 可作为后续扩展。

## ⚠️ 注意事项

- **分辨率与比例**：如果您中途缩放了 UU 远程窗口，脚本会自动重新计算中心区域，具备一定的自适应能力。
- **权限问题**：如果发现鼠标和键盘在游戏中没有反应，请务必以**管理员权限**运行终端/Python 环境。
- **封号风险**：虽然本脚本完全属于外部物理模拟，但过于机械化的长时间挂机行为（如连续数小时在同一坐标点进行规律动作）仍有可能触发游戏服务端的行为特征分析。**建议每隔几小时进行一次人工接管操作。**

## 📝 许可证

[MIT License](LICENSE)
