#!/bin/bash

# ==============================================================================
# RustDesk PUBG Anti-AFK (Linux CLI) 一键安装与运行脚本
# 适用系统: Ubuntu / Debian 及基于 apt 的发行版
# ==============================================================================

# 颜色输出配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}          RustDesk PUBG Anti-AFK (Linux CLI) 一键安装与运行脚本             ${NC}"
echo -e "${BLUE}==============================================================================${NC}"

# 1. 检查是否为 root 用户（安装系统依赖可能需要）
if [ "$EUID" -ne 0 ]; then
  echo -e "${YELLOW}[提示] 您当前不是 root 用户。如果系统缺少依赖，后续步骤可能会提示您输入 sudo 密码。${NC}"
fi

# 2. 检查并安装系统级依赖
echo -e "\n${GREEN}[1/4] 检查系统依赖...${NC}"

# 精简依赖：去除了重量级的 fluxbox，仅保留 Xvfb 和 x11vnc 提供最基础的无头推流能力
REQUIRED_PKGS="xdotool xvfb x11vnc python3 python3-pip python3-tk python3-dev python3-venv"
MISSING_PKGS=""

for pkg in $REQUIRED_PKGS; do
    if ! dpkg -s $pkg >/dev/null 2>&1; then
        MISSING_PKGS="$MISSING_PKGS $pkg"
    fi
done

if [ -n "$MISSING_PKGS" ]; then
    echo -e "${YELLOW}发现缺失依赖: $MISSING_PKGS${NC}"
    echo "正在使用 apt-get 安装 (由于包含桌面组件，可能需要几分钟)..."
    sudo apt-get update
    sudo apt-get install -y $MISSING_PKGS
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 系统依赖安装失败，请检查您的网络或软件源配置。${NC}"
        exit 1
    fi
else
    echo "系统依赖已全部安装！"
fi

# 3. 检查代码仓库是否完整
echo -e "\n${GREEN}[2/4] 检查 Python 脚本文件...${NC}"
if [ ! -f "rustdesk_pubg_afk.py" ] || [ ! -f "requirements.txt" ]; then
    echo -e "${RED}[错误] 找不到 rustdesk_pubg_afk.py 或 requirements.txt！${NC}"
    echo "请确保您已经 git clone 了本仓库，并在仓库根目录下执行此脚本。"
    exit 1
fi
echo "脚本文件检查通过！"

# 4. 配置 Python 虚拟环境并安装依赖
echo -e "\n${GREEN}[3/4] 配置 Python 虚拟环境与依赖库...${NC}"
VENV_DIR="venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "正在创建虚拟环境 (venv)..."
    python3 -m venv $VENV_DIR
fi

# 激活虚拟环境
source $VENV_DIR/bin/activate

echo "正在安装 Python 依赖 (这可能需要几分钟，特别是下载 OCR 模型)..."
# 使用清华源加速国内下载
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] Python 依赖安装失败！${NC}"
    exit 1
fi
echo "Python 依赖安装完成！"

# 5. 启动配置
echo -e "\n${GREEN}[4/4] 准备启动脚本...${NC}"
echo -e "${YELLOW}请确认您的系统环境：${NC}"
echo "将自动检测是否存在可用的 X11 桌面："
echo "- 若存在 DISPLAY 且对应 X socket 可用：直接使用现有桌面"
echo "- 否则：自动启动 Xvfb 无头虚拟桌面 (:99) 并开启 VNC (5900)"

DISPLAY_SOCKET=""
if [ -n "$DISPLAY" ]; then
    DISPLAY_NUM="$(echo "$DISPLAY" | sed 's/^://; s/\\..*$//')"
    DISPLAY_SOCKET="/tmp/.X11-unix/X${DISPLAY_NUM}"
fi

if [ -z "$DISPLAY" ] || [ -n "$DISPLAY_SOCKET" ] && [ ! -S "$DISPLAY_SOCKET" ]; then
    echo -e "\n${BLUE}================ 无头服务器保姆级模式 =================${NC}"
    echo -e "${GREEN}正在为您在后台启动 Xvfb 虚拟显示器 (:99)...${NC}"
    
    # 启动 Xvfb
    if pgrep -x "Xvfb" > /dev/null; then
        echo -e "${YELLOW}[提示] Xvfb 已经在运行。${NC}"
    else
        Xvfb :99 -screen 0 1920x1080x24 -ac -nolisten tcp > /dev/null 2>&1 &
        XVFB_PID=$!
        sleep 2
    fi
    DISPLAY_ARG=":99"
    export DISPLAY=":99"

    XAUTHORITY_PATH="${XAUTHORITY:-$HOME/.Xauthority}"
    export XAUTHORITY="$XAUTHORITY_PATH"
    touch "$XAUTHORITY" 2>/dev/null || true
    
    # 启动 x11vnc 提供远程连接
    if pgrep -x "x11vnc" > /dev/null; then
         echo -e "${YELLOW}[提示] x11vnc 已经在运行。${NC}"
    else
         echo "启动 x11vnc 远程桌面服务 (无密码，端口 5900)..."
         x11vnc -display :99 -forever -shared -bg -nopw -quiet &
    fi
    
    # 交互获取 RustDesk 连接参数
    if ! command -v rustdesk > /dev/null 2>&1; then
        echo -e "\n${YELLOW}[警告] 未检测到 rustdesk 命令。请先在该服务器安装 RustDesk 客户端后再继续。${NC}"
        echo -e "${YELLOW}当前仍会启动挂机脚本，但需要您自行确保 RustDesk 画面已存在于 :99。${NC}"
    else
        echo -e "\n${YELLOW}为方便一键挂机，请输入被控端 (游戏主机) 的 RustDesk 信息：${NC}"
        if [ -z "$RUSTDESK_ID" ]; then
            read -r -p "被控端 ID (如 123456789): " RUSTDESK_ID
        fi
        RUSTDESK_ID="$(echo "$RUSTDESK_ID" | tr -d ' ')"
        if [ -z "$RUSTDESK_PWD" ]; then
            read -r -s -p "被控端 密码: " RUSTDESK_PWD
            echo
        fi
    
        if [ -n "$RUSTDESK_ID" ] && [ -n "$RUSTDESK_PWD" ]; then
            echo -e "${BLUE}正在后台拉起 RustDesk 并自动连接到 $RUSTDESK_ID...${NC}"
            DISPLAY=:99 rustdesk --connect "$RUSTDESK_ID" --password "$RUSTDESK_PWD" > /dev/null 2>&1 &
            sleep 5
            if ! pgrep -f "rustdesk" > /dev/null 2>&1; then
                echo -e "${YELLOW}[警告] rustdesk 进程未检测到。可能是参数不兼容或程序启动失败。${NC}"
            fi
        else
            echo -e "${YELLOW}[警告] 您未输入完整的 ID 或密码，稍后请手动在终端中输入 DISPLAY=:99 rustdesk 启动。${NC}"
        fi
    fi
    
    # 获取本机IP以供提示
    SERVER_IP=$(hostname -I | awk '{print $1}')
    
    echo -e "\n${GREEN}★★★ 无头虚拟桌面环境已就绪！★★★${NC}"
    echo -e "1. 请在您的本地电脑上使用 VNC Viewer 连接到: ${YELLOW}${SERVER_IP}:5900${NC}"
    if [ -n "$RUSTDESK_ID" ]; then
        echo -e "2. 如果您填写的连接参数无误，VNC 画面中应已显示游戏主机的全屏远控画面！"
    else
        echo -e "2. 连接成功后，您将看到一个黑屏环境。"
        echo -e "3. 请在这个终端中（不要断开 SSH），后台启动 RustDesk: ${YELLOW}DISPLAY=:99 rustdesk &${NC}"
        echo -e "4. 此时您的 VNC 画面会显示出 RustDesk 全屏窗口，请进行连接操作。"
    fi
    echo -e "5. 确认画面后，请回到这个 SSH 终端按下回车键，脚本会接管自动操作！"
    echo -e "${BLUE}=======================================================${NC}\n"
    
    read -p "如果您已经配置好 RustDesk 画面，请按回车键开始防掉线挂机..." DUMMY
else
    DISPLAY_ARG="${DISPLAY:-:0}"
fi

echo -e "\n${BLUE}正在启动防掉线脚本 (使用 DISPLAY=$DISPLAY_ARG)...${NC}"
echo -e "提示：按 ${RED}Ctrl+C${NC} 可以随时停止脚本。\n"

# 启动 Python 脚本
python rustdesk_pubg_afk.py --display $DISPLAY_ARG

# 如果是我们启动的 Xvfb 组件，在脚本退出后提示是否清理
if [ -n "$XVFB_PID" ]; then
    echo -e "\n${YELLOW}脚本已停止。是否需要清理刚才创建的虚拟桌面(Xvfb/VNC)？(y/n)${NC}"
    read -p "" CLEANUP_ANS
    if [ "$CLEANUP_ANS" == "y" ] || [ "$CLEANUP_ANS" == "Y" ]; then
        echo -e "${BLUE}正在清理虚拟桌面进程...${NC}"
        kill $XVFB_PID 2>/dev/null
        killall x11vnc 2>/dev/null
    else
        echo -e "${GREEN}虚拟桌面将继续在后台运行，您可以稍后再次执行脚本。${NC}"
    fi
fi

# 脚本退出后，退出虚拟环境
deactivate
