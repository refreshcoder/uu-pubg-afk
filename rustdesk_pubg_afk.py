import sys
import os
import argparse
import shlex
import shutil

# 必须在导入任何可能初始化 GUI/X11 的库之前处理 DISPLAY 环境变量
parser = argparse.ArgumentParser(description='RustDesk PUBG Anti-AFK Script (Linux CLI Mode)')
parser.add_argument('--display', type=str, default=':0', help='指定 X11 DISPLAY 环境变量 (默认: :0)')
parser.add_argument('--target-id', type=str, default=os.environ.get('RUSTDESK_TARGET_ID', ''), help='RustDesk 被控端 ID')
parser.add_argument('--target-password', type=str, default=os.environ.get('RUSTDESK_TARGET_PASSWORD', ''), help='RustDesk 被控端密码')
parser.add_argument('--rustdesk-extra-args', type=str, default=os.environ.get('RUSTDESK_EXTRA_ARGS', ''), help='额外透传给 rustdesk 的参数')
args = parser.parse_args()

# 强制将所有 GUI 操作绑定到指定的 Display
os.environ['DISPLAY'] = args.display

XAUTHORITY_PATH = os.environ.get('XAUTHORITY') or os.path.expanduser('~/.Xauthority')
os.environ['XAUTHORITY'] = XAUTHORITY_PATH
try:
    os.makedirs(os.path.dirname(XAUTHORITY_PATH), exist_ok=True)
    with open(XAUTHORITY_PATH, 'a', encoding='utf-8'):
        pass
except Exception:
    pass

import subprocess
import pyautogui
import random
import time

pyautogui.FAILSAFE = False

def is_x11():
    """检查当前是否为 X11 运行环境"""
    return os.environ.get('DISPLAY') is not None

def start_rustdesk_connection(target_id, target_password, extra_args):
    if not target_id or not target_password:
        return True

    if shutil.which('rustdesk') is None:
        print("未检测到 rustdesk 命令，无法自动连接。")
        return False

    env = os.environ.copy()
    base_cmd = ['rustdesk', '--no-sandbox']
    subprocess.Popen(base_cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

    cmd = ['rustdesk', '--no-sandbox', '--connect', target_id, '--password', target_password]
    if extra_args:
        cmd.extend(shlex.split(extra_args))
    subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)
    return True

def stop_rustdesk_connection():
    subprocess.run(['pkill', '-x', 'rustdesk'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_rustdesk_window():
    """
    通过 xdotool 查找 RustDesk 远程控制窗口
    """
    if os.environ.get('DISPLAY') == ':99':
        if subprocess.run(['pgrep', '-x', 'rustdesk'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
            return None
        return {
            'id': None,
            'left': 0,
            'top': 0,
            'width': 1920,
            'height': 1080,
        }

    try:
        queries = [
            ['xdotool', 'search', '--name', 'RustDesk'],
            ['xdotool', 'search', '--name', 'rustdesk'],
            ['xdotool', 'search', '--class', 'RustDesk'],
            ['xdotool', 'search', '--class', 'rustdesk'],
        ]

        win_ids = []
        for query in queries:
            try:
                output = subprocess.check_output(query, text=True)
                win_ids.extend([w for w in output.strip().split('\n') if w])
            except subprocess.CalledProcessError:
                continue

        if not win_ids:
            return None
        
        for win_id in win_ids:
            # 获取窗口几何信息
            geom_output = subprocess.check_output(['xdotool', 'getwindowgeometry', win_id], text=True)
            # 解析几何信息
            # Example output:
            # Window 10485764
            #   Position: 10, 50 (screen: 0)
            #   Geometry: 1280x720
            lines = geom_output.split('\n')
            pos_line = next(l for l in lines if 'Position:' in l)
            geom_line = next(l for l in lines if 'Geometry:' in l)
            
            # 提取坐标和大小
            pos_parts = pos_line.split(':')[1].split('(')[0].strip().split(',')
            left, top = int(pos_parts[0].strip()), int(pos_parts[1].strip())
            
            size_parts = geom_line.split(':')[1].strip().split('x')
            width, height = int(size_parts[0]), int(size_parts[1])
            
            # 过滤掉太小的窗口（例如主面板），保留远控大窗口
            if width > 800 and height > 600:
                return {
                    'id': win_id,
                    'left': left,
                    'top': top,
                    'width': width,
                    'height': height
                }
    except subprocess.CalledProcessError:
        pass
    except Exception as e:
        print(f"获取窗口信息时出错: {e}")
        
    return None

def focus_window(win_info):
    """通过 xdotool 激活窗口"""
    # 如果是纯无头 Xvfb 模式，通常全屏且只有一个应用在运行，不需要激活窗口，直接返回 True 提升性能
    if os.environ.get('DISPLAY') == ':99':
        return True

    if not win_info or not win_info.get('id'):
        return False
        
    try:
        subprocess.check_call(['xdotool', 'windowactivate', '--sync', win_info['id']])
        time.sleep(0.1)
        return True
    except subprocess.CalledProcessError:
        print("激活窗口失败，请确保安装了 xdotool")
        return False

def safety_movement(win_info):
    """执行极短防掉线动作 (原地踏步)"""
    # 每次操作前确保窗口激活 (Xvfb 无头模式会自动跳过)
    if not focus_window(win_info):
        return
        
    # 如果是在无头环境 (:99)，RustDesk 通常会自动全屏，不需要考虑边界偏移，直接在中心操作
    if os.environ.get('DISPLAY') == ':99':
        center_x = 1920 // 2
        center_y = 1080 // 2
    else:
        center_x = win_info['left'] + win_info['width'] // 2
        center_y = win_info['top'] + win_info['height'] // 2
        
    dx = random.randint(-60, 60)
    dy = random.randint(-20, 20)
    
    # 使用 pyautogui 移动鼠标
    pyautogui.moveTo(center_x + dx, center_y + dy, duration=0.1)
    
    keys = ['w', 's', 'a', 'd']
    k = random.choice(keys)
    hold_time = random.uniform(0.1, 0.18)
    
    pyautogui.keyDown(k)
    time.sleep(hold_time)
    pyautogui.keyUp(k)
    
    opp_map = {'w': 's', 's': 'w', 'a': 'd', 'd': 'a'}
    time.sleep(0.05)
    
    pyautogui.keyDown(opp_map[k])
    time.sleep(hold_time)
    pyautogui.keyUp(opp_map[k])

    extra_times = random.randint(2, 5)
    for _ in range(extra_times):
        key = random.choice(['q', 'e'])
        press_time = random.uniform(0.03, 0.07)
        pyautogui.keyDown(key)
        time.sleep(press_time)
        pyautogui.keyUp(key)
        time.sleep(random.uniform(0.05, 0.15))

def main():
    print(f"=== RustDesk PUBG 防掉线助手 (Linux CLI 模式) 已启动 ===")
    print(f"当前绑定的 X11 Display: {os.environ.get('DISPLAY')}")
    
    if not is_x11():
        print("错误: 未检测到 DISPLAY 环境变量。")
        print("如果您通过 SSH 连接，请确保设置了正确的 DISPLAY (例如 export DISPLAY=:0) ")
        print("或者通过参数传递: python3 rustdesk_pubg_afk.py --display :0")
        sys.exit(1)
        
    print("提示：请按 Ctrl+C 停止脚本。建议让角色在游戏中面壁站立。")
    print("依赖检查: 请确保系统中已安装 xdotool (用于窗口焦点控制)。")
    print("运行策略：每轮开始前连接 RustDesk，执行动作后立刻断开连接。")
    
    try:
        while True:
            start_rustdesk_connection(args.target_id, args.target_password, args.rustdesk_extra_args)

            try:
                win_info = get_rustdesk_window()
                if not win_info:
                    print(f"[{time.strftime('%H:%M:%S')}] 未找到符合条件的 RustDesk 窗口或 rustdesk 进程未启动。")
                    time.sleep(10)
                    continue

                safety_movement(win_info)
                print(f"[{time.strftime('%H:%M:%S')}] 状态：已执行极微量位置抵消动作。")
            finally:
                stop_rustdesk_connection()

            wait_time = random.randint(580, 640)
            print(f"[{time.strftime('%H:%M:%S')}] 等待 {wait_time} 秒后进行下一次扫描...")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\n=== 脚本已手动停止 ===")

if __name__ == "__main__":
    main()
