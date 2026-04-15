import sys
import os
import argparse

# 必须在导入任何可能初始化 GUI/X11 的库之前处理 DISPLAY 环境变量
parser = argparse.ArgumentParser(description='RustDesk PUBG Anti-AFK Script (Linux CLI Mode)')
parser.add_argument('--display', type=str, default=':0', help='指定 X11 DISPLAY 环境变量 (默认: :0)')
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
import easyocr
import numpy as np
import mss
import random
import time

# 初始化 OCR 引擎
print("正在加载 OCR 模型（默认使用 CPU）...")
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
print("OCR 模型加载完成！当前模式：CPU OCR")

OCR_INTERVAL_SECONDS = 10 * 60

def is_x11():
    """检查当前是否为 X11 运行环境"""
    return os.environ.get('DISPLAY') is not None

def get_rustdesk_window():
    """
    通过 xdotool 查找 RustDesk 远程控制窗口
    """
    if os.environ.get('DISPLAY') == ':99':
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

def check_kicked_with_ocr(win_info):
    """
    使用 OCR 检测窗口中心区域的异常文字
    """
    x1 = win_info['left'] + (win_info['width'] * 0.25)
    y1 = win_info['top'] + (win_info['height'] * 0.25)
    x2 = win_info['left'] + (win_info['width'] * 0.75)
    y2 = win_info['top'] + (win_info['height'] * 0.75)
    
    # mss 使用 top/left/width/height 的格式
    monitor = {
        "top": int(y1),
        "left": int(x1),
        "width": int(x2 - x1),
        "height": int(y2 - y1)
    }
    
    try:
        with mss.mss() as sct:
            sct_img = sct.grab(monitor)
            # mss 输出 BGRA 格式，需要转换以供 easyocr 使用
            img_np = np.array(sct_img)
    except Exception as e:
        print(f"截图失败 (可能无权限访问 X Display 或 X11 环境未启动): {e}")
        return False
        
    results = reader.readtext(img_np, detail=1)
    
    keywords = ["错误", "錯誤", "Error", "error", "异常", "断开"]
    
    for bbox_coords, text, prob in results:
        for key in keywords:
            if key in text:
                print(f"[{time.strftime('%H:%M:%S')}] 警告！检测到异常文字: '{text}' (置信度: {prob:.2f})")
                
                if "确定" in text or "确认" in text or "OK" in text:
                    center_x = (bbox_coords[0][0] + bbox_coords[1][0]) / 2
                    center_y = (bbox_coords[0][1] + bbox_coords[2][1]) / 2
                    abs_click_x = int(x1 + center_x)
                    abs_click_y = int(y1 + center_y)
                    print(f"尝试自动点击 '确定' 按钮，坐标: ({abs_click_x}, {abs_click_y})")
                    pyautogui.click(abs_click_x, abs_click_y)
                    
                return True
    return False

def should_run_ocr(last_ocr_time):
    """控制 OCR 的执行频率"""
    if last_ocr_time is None:
        return True
    return (time.time() - last_ocr_time) >= OCR_INTERVAL_SECONDS

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
    print("OCR 检测频率：每 10 分钟最多执行一次。")
    
    last_ocr_time = None
    
    try:
        while True:
            win_info = get_rustdesk_window()
            if not win_info:
                print(f"[{time.strftime('%H:%M:%S')}] 未找到符合条件的 RustDesk 窗口...")
                print(" -> 请确保您的 RustDesk 在当前 DISPLAY 运行并已连接到被控端。")
                print(" -> (如果您使用的是无头服务器的 Xvfb 模式，请使用其他客户端连接到此虚拟桌面打开远控)。")
                time.sleep(10)
                continue
                
            # 执行动作
            safety_movement(win_info)
            print(f"[{time.strftime('%H:%M:%S')}] 状态：已执行极微量位置抵消动作。")
            
            # 决定是否进行 OCR 检测
            if should_run_ocr(last_ocr_time):
                print(f"[{time.strftime('%H:%M:%S')}] 正在执行定期画面状态 OCR 检测...")
                if check_kicked_with_ocr(win_info):
                    print(f"[{time.strftime('%H:%M:%S')}] 状态：画面异常，暂停防掉线动作，等待人工处理...")
                    time.sleep(30)
                last_ocr_time = time.time()
                
            wait_time = random.randint(45, 90)
            print(f"[{time.strftime('%H:%M:%S')}] 等待 {wait_time} 秒后进行下一次扫描...")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\n=== 脚本已手动停止 ===")

if __name__ == "__main__":
    main()
