#!/bin/bash

# ==============================================================================
# RustDesk CLI 连接及状态检测工具
# 可以在无头 Xvfb 等环境下自动发起连接，并通过分析窗口信息和日志验证是否成功。
# ==============================================================================

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

if [ -z "$1" ] || [ -z "$2" ]; then
    echo -e "${RED}用法: $0 <目标ID> <密码> [DISPLAY]${NC}"
    echo -e "示例: $0 123456789 mypassword :99"
    exit 1
fi

RUSTDESK_ID="$(echo "$1" | tr -d ' ')"
RUSTDESK_PWD="$2"
# 如果没有指定参数3，则默认用环境变量，若都没有则使用 :0
DISPLAY_ARG=${3:-${DISPLAY:-":0"}}

export DISPLAY="$DISPLAY_ARG"

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}     RustDesk 独立连接检测工具 (DISPLAY=$DISPLAY_ARG)${NC}"
echo -e "${BLUE}===============================================${NC}"

# 1. 确保基础环境就绪
if ! command -v rustdesk > /dev/null 2>&1; then
    echo -e "${RED}[错误] 未检测到 rustdesk 客户端，请先安装。${NC}"
    exit 1
fi

if ! command -v xdotool > /dev/null 2>&1; then
    echo -e "${RED}[错误] 缺少 xdotool，无法检测窗口状态。请先安装: sudo apt install xdotool${NC}"
    exit 1
fi

LOG_FILE="/tmp/rustdesk_connect.log"
echo -e "${YELLOW}[1/4] 清理旧日志与无用进程...${NC}"
rm -f "$LOG_FILE"
killall rustdesk 2>/dev/null
sleep 2

# 2. 静默拉起主界面/守护进程 (避免第一步带参数失效)
echo -e "${YELLOW}[2/4] 启动 RustDesk 主进程...${NC}"
rustdesk --no-sandbox > /dev/null 2>&1 &
sleep 3

# 3. 发起远程连接请求
echo -e "${YELLOW}[3/4] 正在向目标 $RUSTDESK_ID 发起连接...${NC}"
rustdesk --no-sandbox --connect "$RUSTDESK_ID" --password "$RUSTDESK_PWD" > "$LOG_FILE" 2>&1 &

echo -e "${YELLOW}[4/4] 等待连接建立并分析窗口状态...${NC}"
# 等待最长 15 秒来建立连接
TIMEOUT=15
SUCCESS=0

for ((i=1; i<=TIMEOUT; i++)); do
    sleep 1
    # 通过 xdotool 检索当前存在的 RustDesk 窗口
    # 当连接成功后，通常会弹出一个标题包含远控设备ID/名称，或完全无标题的新的子窗口
    # 如果仅有一个窗口（主界面），说明还没连上
    WINDOW_COUNT=$(xdotool search --name "RustDesk" 2>/dev/null | wc -l)
    
    # 也可以检索当前窗口列表的标题进行更深度的校验
    if [ "$WINDOW_COUNT" -ge 2 ]; then
        SUCCESS=1
        echo -e "${GREEN}[✔] 成功！检测到远控窗口已弹出 (找到 $WINDOW_COUNT 个 RustDesk 相关窗口)。${NC}"
        break
    fi
    
    # 解析日志，尝试匹配一些底层 Flutter/C++ 的报错
    if grep -q -i "error\|failed\|timeout\|invalid password" "$LOG_FILE"; then
        ERROR_MSG=$(grep -i "error\|failed\|timeout\|invalid password" "$LOG_FILE" | tail -n 1)
        echo -e "${RED}[✘] 连接失败！日志捕获到错误: ${ERROR_MSG}${NC}"
        SUCCESS=0
        break
    fi
done

if [ $SUCCESS -eq 0 ]; then
    echo -e "${RED}[✘] 连接超时或未成功建立。可能的原因：${NC}"
    echo "1. 密码错误或 ID 不存在。"
    echo "2. 目标主机不在线 / RustDesk 未启动。"
    echo "3. 网络 P2P 穿透失败 / 中继服务器异常。"
    echo -e "\n最后 10 行启动日志如下:"
    tail -n 10 "$LOG_FILE"
    exit 1
fi

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}远程连接就绪！您现在可以挂载防掉线脚本了。${NC}"
echo -e "${GREEN}===============================================${NC}"
exit 0