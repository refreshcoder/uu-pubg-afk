# UU / RustDesk PUBG Anti-AFK (绝地求生 远程防掉线助手)

这是一个专为“UU远程”和“RustDesk”等远程控制软件设计的 PUBG (绝地求生) 防掉线/防踢出自动化脚本。

由于脚本运行在**主控机**（您正在使用的电脑）而非游戏运行的被控机上，它通过物理级别的图像识别和系统级键鼠模拟来工作，最大限度保证了账号的安全（无游戏内存修改，不触碰反作弊系统）。

该项目目前包含两套脚本：
- `uu_pubg_afk.py`：针对 **Windows** 环境下使用 **UU远程** 的场景。
- `rustdesk_pubg_afk.py`：针对 **Linux** 环境下使用 **RustDesk** 的场景。

## ✨ 核心特性

- 🎯 **智能窗口锁定**：精准锁定实际的远程桌面推流窗口。
- 👁️ **OCR 异常检测**：定期扫描屏幕中心区域，通过 `EasyOCR` 识别“错误”, “錯誤”(繁), “Error”, “error”等掉线提示词，支持自动点击重连。
- 🚶 **极微量位移抵消**：采用“0.1秒按键+反向补偿”的镜像抵消算法，确保角色在游戏中原地踏步，不乱跑。
- 🖱️ **防失焦鼠标微动**：计算窗口几何中心进行相对微调，防止鼠标随时间推移甩出远程窗口导致失焦。
- ⚡ **性能优化**：通过限制 OCR 的识别坐标区域（仅识别中心 50% 的画面），大幅降低 CPU 占用。

## 🛠️ 安装说明

### Windows (UU 远程版)
1. 确保您的电脑（主控机）已安装 [Python 3.8+](https://www.python.org/downloads/)。
2. 克隆本仓库或下载源码到本地：
   ```bash
   git clone https://github.com/yourusername/uu-pubg-afk.git
   cd uu-pubg-afk
   ```
3. 创建并激活虚拟环境：
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
4. 安装相关依赖包：
   ```bash
   pip install -r requirements.txt
   ```

### Linux (RustDesk 远控版 - 纯 CLI 模式兼容)
1. 确保您的系统为 X11 / Xorg 环境。若您在 SSH 或纯终端下运行，脚本已自动适配环境变量。
2. 安装系统依赖（如 `xdotool` 用于窗口焦点控制）：
   ```bash
   sudo apt-get install xdotool python3-tk python3-dev
   ```
3. 克隆并进入目录：
   ```bash
   git clone https://github.com/yourusername/uu-pubg-afk.git
   cd uu-pubg-afk
   ```
4. 安装 Python 依赖：
   ```bash
   pip3 install -r requirements.txt
   ```

## 🚀 使用指南

1. **准备工作**：在被控机（游戏机）打开 PUBG，建议让角色在安全区域**面壁站立**（这样可以利用游戏内的物理碰撞体积进一步防止位移误差）。
2. **连接远程**：在主控机打开远程软件（UU远程 或 RustDesk）并连接到被控机，确保能看到游戏画面。
3. **运行脚本**：
   - **Windows (UU远程)**：以管理员身份打开终端运行：
     ```bash
     python uu_pubg_afk.py
     ```
   - **Linux (RustDesk)**：通过终端或 SSH 运行：
     ```bash
     python3 rustdesk_pubg_afk.py
     ```
     *(如果您是通过 SSH 运行，且桌面的 DISPLAY 并非默认的 `:0`，您可以使用参数指定：`python3 rustdesk_pubg_afk.py --display :1`)*
4. **停止运行**：在终端中按下 `Ctrl + C` 即可安全停止脚本。

## ⚠️ 注意事项

- **遮挡问题**：脚本运行时，主控机的 UU 远程画面不能被其他窗口完全遮挡，否则 OCR 无法截取到游戏画面。
- **分辨率与比例**：如果您中途缩放了 UU 远程窗口，脚本会自动重新计算中心区域，具备一定的自适应能力。
- **权限问题**：如果发现鼠标和键盘在游戏中没有反应，请务必以**管理员权限**运行终端/Python 环境。
- **封号风险**：虽然本脚本完全属于外部物理模拟，但过于机械化的长时间挂机行为（如连续数小时在同一坐标点进行规律动作）仍有可能触发游戏服务端的行为特征分析。**建议每隔几小时进行一次人工接管操作。**

## 📝 许可证

[MIT License](LICENSE)