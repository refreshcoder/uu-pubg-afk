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
import random
import time

RUSTDESK_DAEMON_LOG = '/tmp/rustdesk_daemon.log'
RUSTDESK_CONNECT_LOG = '/tmp/rustdesk_connect.log'
CONNECT_TIMEOUT_SECONDS = 30
CONNECT_RETRIES = 3

def is_x11():
    """检查当前是否为 X11 运行环境"""
    return os.environ.get('DISPLAY') is not None

def xdotool(*args):
    return subprocess.run(['xdotool', *map(str, args)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def xdotool_key_down(key):
    xdotool('keydown', key)

def xdotool_key_up(key):
    xdotool('keyup', key)

def xdotool_mouse_move(x, y):
    xdotool('mousemove', x, y)

def xdotool_mouse_down(button):
    xdotool('mousedown', button)

def xdotool_mouse_up(button):
    xdotool('mouseup', button)

def xdotool_mouse_click(button):
    xdotool('click', button)

def is_rustdesk_running():
    return subprocess.run(['pgrep', '-x', 'rustdesk'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

def ensure_rustdesk_running():
    if shutil.which('rustdesk') is None:
        print("未检测到 rustdesk 命令，无法自动连接。")
        return False

    if is_rustdesk_running():
        return True

    env = os.environ.copy()
    with open(RUSTDESK_DAEMON_LOG, 'ab') as fp:
        subprocess.Popen(['rustdesk', '--no-sandbox'], env=env, stdout=fp, stderr=fp)

    for _ in range(8):
        if is_rustdesk_running():
            return True
        time.sleep(1)
    return True

def list_rustdesk_windows():
    queries = [
        ['xdotool', 'search', '--name', 'RustDesk'],
        ['xdotool', 'search', '--name', 'rustdesk'],
        ['xdotool', 'search', '--class', 'RustDesk'],
        ['xdotool', 'search', '--class', 'rustdesk'],
    ]

    win_ids = set()
    for query in queries:
        try:
            output = subprocess.check_output(query, text=True)
            for wid in output.strip().split('\n'):
                wid = wid.strip()
                if wid:
                    win_ids.add(wid)
        except subprocess.CalledProcessError:
            continue
    return win_ids

def get_window_name(win_id):
    try:
        return subprocess.check_output(['xdotool', 'getwindowname', win_id], text=True).strip()
    except Exception:
        return ''

def get_window_geometry(win_id):
    try:
        geom_output = subprocess.check_output(['xdotool', 'getwindowgeometry', win_id], text=True)
        lines = geom_output.split('\n')
        pos_line = next(l for l in lines if 'Position:' in l)
        geom_line = next(l for l in lines if 'Geometry:' in l)

        pos_parts = pos_line.split(':')[1].split('(')[0].strip().split(',')
        left, top = int(pos_parts[0].strip()), int(pos_parts[1].strip())

        size_parts = geom_line.split(':')[1].strip().split('x')
        width, height = int(size_parts[0]), int(size_parts[1])

        return {
            'id': win_id,
            'left': left,
            'top': top,
            'width': width,
            'height': height,
        }
    except Exception:
        return None

def get_display_geometry():
    try:
        out = subprocess.check_output(['xdotool', 'getdisplaygeometry'], text=True).strip()
        parts = out.split()
        if len(parts) >= 2:
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return 1920, 1080

def fullscreen_window(win_id):
    if not win_id:
        return False

    width, height = get_display_geometry()
    subprocess.run(['xdotool', 'windowmove', win_id, '0', '0'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    subprocess.run(['xdotool', 'windowsize', win_id, str(width), str(height)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return True

def select_remote_window(target_id, preferred_ids=None):
    width, height = get_display_geometry()
    display_area = width * height

    target_id = (target_id or '').replace(' ', '').strip()
    ids = set(preferred_ids or set())
    ids |= list_rustdesk_windows()
    if not ids:
        return None

    best = None
    best_score = -1
    for wid in ids:
        geom = get_window_geometry(wid)
        if not geom:
            continue

        area = geom['width'] * geom['height']
        if area < 300 * 300:
            continue

        name = get_window_name(wid)
        score = 0
        if target_id and target_id in name.replace(' ', ''):
            score += 1_000_000
        if area >= int(display_area * 0.70):
            score += area
        elif score == 0:
            continue

        if score > best_score:
            best_score = score
            best = geom

    if best and best.get('id'):
        fullscreen_window(best['id'])
    return best

def restart_rustdesk():
    subprocess.run(['pkill', '-x', 'rustdesk'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    return ensure_rustdesk_running()

def read_log_tail(path, max_bytes=8000):
    try:
        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max_bytes), os.SEEK_SET)
            return f.read().decode('utf-8', errors='ignore')
    except Exception:
        return ''

def is_connect_failed_from_log(text):
    lowered = text.lower()
    if 'security-v4.rustdesk.com/verify' in lowered:
        return True
    patterns = [
        'invalid password',
        'timeout',
        'failed',
        'error',
        'cannot connect',
    ]
    return any(p in lowered for p in patterns)

def connect_rustdesk(target_id, target_password, extra_args):
    target_id = (target_id or '').replace(' ', '').strip()
    target_password = (target_password or '').strip()

    if not target_id or not target_password:
        return set()

    if not ensure_rustdesk_running():
        return set()

    before = list_rustdesk_windows()

    env = os.environ.copy()
    cmd = ['rustdesk', '--no-sandbox', '--connect', target_id, '--password', target_password]
    if extra_args:
        cmd.extend(shlex.split(extra_args))
    try:
        with open(RUSTDESK_CONNECT_LOG, 'wb'):
            pass
    except Exception:
        pass
    with open(RUSTDESK_CONNECT_LOG, 'ab') as fp:
        subprocess.Popen(cmd, env=env, stdout=fp, stderr=fp)

    for _ in range(CONNECT_TIMEOUT_SECONDS):
        after = list_rustdesk_windows()
        delta = after - before
        if delta:
            return delta
        if is_connect_failed_from_log(read_log_tail(RUSTDESK_CONNECT_LOG)):
            return set()
        time.sleep(1)

    after = list_rustdesk_windows()
    return after - before

def disconnect_rustdesk(win_ids):
    if not win_ids:
        return False

    ok = False
    for wid in win_ids:
        try:
            subprocess.run(['xdotool', 'windowkill', wid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            ok = True
        except Exception:
            continue
    time.sleep(1)
    return ok

def get_rustdesk_window():
    """
    通过 xdotool 查找 RustDesk 远程控制窗口
    """
    try:
        win_ids = list(list_rustdesk_windows())
        if not win_ids:
            return None

        best = None
        best_area = 0
        for win_id in win_ids:
            geom = get_window_geometry(win_id)
            if not geom:
                continue
            area = geom['width'] * geom['height']
            if area > best_area:
                best_area = area
                best = geom

        if best and best['width'] > 300 and best['height'] > 300:
            return best
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
        fullscreen_window(win_info['id'])
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
    
    move_duration = 0.1
    xdotool_mouse_move(center_x + dx, center_y + dy)

    xdotool_mouse_down(3)
    time.sleep(move_duration)
    xdotool_mouse_up(3)

    xdotool_mouse_click(3)
    time.sleep(random.uniform(2, 4))
    xdotool_mouse_click(3)
    
    keys = ['w', 's', 'a', 'd']
    k = random.choice(keys)
    hold_time = random.uniform(0.1, 0.18)
    
    xdotool_key_down(k)
    time.sleep(hold_time)
    xdotool_key_up(k)
    
    opp_map = {'w': 's', 's': 'w', 'a': 'd', 'd': 'a'}
    time.sleep(0.05)
    
    xdotool_key_down(opp_map[k])
    time.sleep(hold_time)
    xdotool_key_up(opp_map[k])

    extra_times = random.randint(2, 5)
    for _ in range(extra_times):
        key = random.choice(['q', 'e'])
        press_time = random.uniform(0.03, 0.07)
        xdotool_key_down(key)
        time.sleep(press_time)
        xdotool_key_up(key)
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
    print("运行策略：RustDesk 常驻运行，每轮操作前建立连接，操作结束后断开连接。")

    if not args.target_id or not args.target_password:
        print("错误：缺少 RustDesk 被控端信息。请使用参数 --target-id 和 --target-password。")
        sys.exit(2)

    ensure_rustdesk_running()
    
    try:
        while True:
            connected_win_ids = set()
            for _ in range(CONNECT_RETRIES):
                connected_win_ids = connect_rustdesk(args.target_id, args.target_password, args.rustdesk_extra_args)
                if connected_win_ids:
                    break
                restart_rustdesk()

            try:
                win_info = None
                for _ in range(CONNECT_TIMEOUT_SECONDS):
                    win_info = select_remote_window(args.target_id, preferred_ids=connected_win_ids)
                    if win_info:
                        break
                    time.sleep(1)

                if not win_info:
                    print(f"[{time.strftime('%H:%M:%S')}] 未找到可操作的 RustDesk 窗口。")
                    time.sleep(10)
                    continue

                time.sleep(15)

                safety_movement(win_info)
                print(f"[{time.strftime('%H:%M:%S')}] 状态：已执行极微量位置抵消动作。")
            finally:
                if win_info and win_info.get('id'):
                    connected_win_ids.add(win_info['id'])
                disconnect_rustdesk(connected_win_ids)

            wait_time = random.randint(280, 320)
            print(f"[{time.strftime('%H:%M:%S')}] 等待 {wait_time} 秒后进行下一次扫描...")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\n=== 脚本已手动停止 ===")

if __name__ == "__main__":
    main()
