#!/bin/bash

# ==============================================================================
# RustDesk PUBG Anti-AFK (Linux CLI) 一键安装与运行脚本
# 适用系统: Ubuntu / Debian 及基于 apt 的发行版
# ==============================================================================

# 颜色输出配置
RED='\03.3[0;31m'
GREEN='\03.3[0;32m'
YELLOW='\03.3[0;33m'
BLUE='\03.3[0;34m'
NC='\03.3[0m' # No Color

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}          RustDesk PUBG Anti-AFK (Linux CLI) 一键安装与运行脚本             ${NC}"
echo -e "${BLUE}==============================================================================${NC}"

# 1. 检查是否为 root 用户（安装系统依赖可能需要）
if [ "$EUID" -ne 0 ]; then
  echo -e "${YELLOW}[提示] 您当前不是 root 用户。如果系统缺少依赖，后续步骤可能会提示您输入 sudo 密码。${NC}"
fi

# 2. 检查并安装系统级依赖 (xdotool, python3, pip, python3-tk)
echo -e "\n${GREEN}[1/4] 检查系统依赖...${NC}"

REQUIRED_PKGS="xdotool python3 python3-pip python3-tk python3-dev python3-venv"
MISSING_PKGS=""

for pkg in $REQUIRED_PKGS; do
    if ! dpkg -s $pkg >/dev/null 2>&1; then
        MISSING_PKGS="$MISSING_PKGS $pkg"
    fi
done

if [ -n "$MISSING_PKGS" ]; then
    echo -e "${YELLOW}发现缺失依赖: $MISSING_PKGS${NC}"
    echo "正在使用 apt-get 安装..."
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

# 5. 交互式启动配置
echo -e "\n${GREEN}[4/4] 准备启动脚本...${NC}"
echo -e "${YELLOW}请确认您的系统环境：${NC}"
echo "如果您在桌面环境的终端中运行，或者您通过 SSH 连接但桌面编号为默认的 :0"
echo "您可以直接按回车键启动。"
echo -e "如果您的显示器编号不同（例如虚拟显示器 :1），请手动输入编号。\n"

read -p "请输入 DISPLAY 环境变量 (直接回车默认 :0): " USER_DISPLAY
DISPLAY_ARG=${USER_DISPLAY:-":0"}

echo -e "\n${BLUE}正在启动防掉线脚本 (使用 DISPLAY=$DISPLAY_ARG)...${NC}"
echo -e "提示：按 ${RED}Ctrl+C${NC} 可以随时停止脚本。\n"

# 启动 Python 脚本
python rustdesk_pubg_afk.py --display $DISPLAY_ARG

# 脚本退出后，退出虚拟环境
deactivate