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

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

# 1. 检查是否为 root 用户（安装系统依赖可能需要）
if [ "$EUID" -ne 0 ]; then
  echo -e "${YELLOW}[提示] 您当前不是 root 用户。如果系统缺少依赖，后续步骤可能会提示您输入 sudo 密码。${NC}"
fi

# 2. 检查并安装系统级依赖
echo -e "\n${GREEN}[1/5] 检查系统依赖...${NC}"

# 精简依赖：去除了重量级的 fluxbox，保留 Xvfb, x11vnc 提供无头推流能力
# 新增 libegl1 和 libgl1 解决 RustDesk 在无头环境启动时缺失 OpenGL 硬件渲染库报错的问题
REQUIRED_PKGS="xdotool xvfb x11vnc libegl1 libgl1 python3 python3-pip python3-tk python3-dev python3-venv"
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

# 2.5 检查并安装 RustDesk 客户端
echo -e "\n${GREEN}[2/5] 检查 RustDesk 客户端...${NC}"
if ! command -v rustdesk >/dev/null 2>&1; then
    echo -e "${YELLOW}未检测到 RustDesk 客户端，正在为您自动下载并安装...${NC}"
    # 获取最新的 RustDesk deb 下载链接 (这里使用 GitHub API 或固定版本)
    # 为了稳定，这里使用 1.2.3 稳定版作为 fallback
    RUSTDESK_DEB_URL="https://github.com/rustdesk/rustdesk/releases/download/1.2.3/rustdesk-1.2.3-x86_64.deb"
    
    echo "正在下载 RustDesk: $RUSTDESK_DEB_URL"
    wget -qO /tmp/rustdesk.deb "$RUSTDESK_DEB_URL"
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] RustDesk 下载失败，请检查网络或稍后手动安装。${NC}"
        exit 1
    fi
    
    echo "正在安装 RustDesk..."
    sudo apt-get install -y /tmp/rustdesk.deb
    if [ $? -ne 0 ]; then
         echo -e "${RED}[错误] RustDesk 安装失败。${NC}"
         exit 1
    fi
    rm /tmp/rustdesk.deb
    echo "RustDesk 安装完成！"
else
    echo "RustDesk 已安装！"
fi

# 3. 检查代码仓库是否完整
echo -e "\n${GREEN}[3/5] 检查 Python 脚本文件...${NC}"
if [ ! -f "rustdesk_pubg_afk.py" ] || [ ! -f "requirements_rustdesk.txt" ]; then
    echo -e "${RED}[错误] 找不到 rustdesk_pubg_afk.py 或 requirements_rustdesk.txt！${NC}"
    echo "请确保您已经 git clone 了本仓库，并在仓库根目录下执行此脚本。"
    exit 1
fi
echo "脚本文件检查通过！"

# 4. 配置 Python 虚拟环境并安装依赖
echo -e "\n${GREEN}[4/5] 配置 Python 虚拟环境与依赖库...${NC}"
VENV_DIR="venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "正在创建虚拟环境 (venv)..."
    python3 -m venv $VENV_DIR
fi

# 激活虚拟环境
source $VENV_DIR/bin/activate

echo "正在安装 Python 依赖..."
# 使用清华源加速国内下载
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements_rustdesk.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] Python 依赖安装失败！${NC}"
    exit 1
fi
echo "Python 依赖安装完成！"

# 5. 交互式启动配置
echo -e "\n${GREEN}[5/5] 准备启动脚本...${NC}"
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
    
    RUSTDESK_ID="${RUSTDESK_ID:-${RUSTDESK_TARGET_ID:-}}"
    RUSTDESK_PWD="${RUSTDESK_PWD:-${RUSTDESK_TARGET_PASSWORD:-}}"
    RUSTDESK_EXTRA_ARGS="${RUSTDESK_EXTRA_ARGS:-${RUSTDESK_RUSTDESK_EXTRA_ARGS:-}}"

    if [ -z "$RUSTDESK_ID" ] || [ -z "$RUSTDESK_PWD" ]; then
        echo -e "\n${YELLOW}请输入被控端 (游戏主机) 的 RustDesk 信息（也可写入 .env 自动读取）：${NC}"
        read -r -p "被控端 ID (如 123456789): " RUSTDESK_ID
        RUSTDESK_ID="$(echo "$RUSTDESK_ID" | tr -d ' ')"
        read -r -s -p "被控端 密码: " RUSTDESK_PWD
        echo
    fi

    read -r -p "额外 rustdesk 参数(可选，直接回车跳过): " RUSTDESK_EXTRA_ARGS
    
    # 获取本机IP以供提示
    SERVER_IP=$(hostname -I | awk '{print $1}')
    
    echo -e "\n${GREEN}★★★ 无头虚拟桌面环境已就绪！★★★${NC}"
    echo -e "1. 请在您的本地电脑上使用 VNC Viewer 连接到: ${YELLOW}${SERVER_IP}:5900${NC}"
    echo -e "2. 首次连接如遇到安全验证页面，请在 VNC 内完成一次验证。"
    echo -e "3. 完成后回到 SSH 终端按回车启动防掉线脚本。"
    echo -e "${BLUE}=======================================================${NC}\n"
    
    read -p "如果您已经配置好 RustDesk 画面，请按回车键开始防掉线挂机..." DUMMY
else
    DISPLAY_ARG="${DISPLAY:-:0}"
fi

echo -e "\n${BLUE}正在启动防掉线脚本 (使用 DISPLAY=$DISPLAY_ARG)...${NC}"
echo -e "提示：按 ${RED}Ctrl+C${NC} 可以随时停止脚本。\n"

# 启动 Python 脚本
if [ -n "$RUSTDESK_ID" ] && [ -n "$RUSTDESK_PWD" ]; then
    python rustdesk_pubg_afk.py --display "$DISPLAY_ARG" --target-id "$RUSTDESK_ID" --target-password "$RUSTDESK_PWD" --rustdesk-extra-args "$RUSTDESK_EXTRA_ARGS"
else
    python rustdesk_pubg_afk.py --display "$DISPLAY_ARG"
fi

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
