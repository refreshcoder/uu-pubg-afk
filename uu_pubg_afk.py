import pygetwindow as gw
import pydirectinput
import easyocr
import numpy as np
from PIL import ImageGrab
import random
import time

# 初始化 OCR 引擎 (首次运行会自动下载模型，请耐心等待)
print("正在加载 OCR 模型...")
reader = easyocr.Reader(['ch_sim', 'en'])
print("OCR 模型加载完成！")

def get_remote_window():
    """
    智能查找实际的远程桌面窗口，排除控制面板。
    根据网易UU远程的进程特性，控制面板标题通常叫“网易UU远程”，
    而实际的远程控制窗口标题通常包含远控设备的名称（如 "HOME"）。
    由于标题可能变动，我们会扩大搜索范围，并利用窗口尺寸过滤控制面板。
    """
    # 尝试查找包含常见关键字的窗口
    # HOME 是用户提供的特定远控窗口名，加入通用关键字保证兼容性
    possible_windows = []
    for title in ['HOME', 'UU', '远程', '网易UU远程']:
        possible_windows.extend(gw.getWindowsWithTitle(title))
    
    # 去重
    unique_windows = list({win._hWnd: win for win in possible_windows}.values())
    
    for win in unique_windows:
        # 排除掉小尺寸的控制面板 (网易UU远程控制面板较小，远控窗口通常 > 800x600)
        # 同时排除掉看不见的窗口
        if win.width > 800 and win.height > 600 and win.visible:
            return win
    return None

def focus_window(win):
    """安全地将窗口置顶并激活"""
    try:
        if win.isMinimized:
            win.restore()
        if not win.isActive:
            win.activate()
            time.sleep(0.5) # 等待窗口激活的动画完成
        return True
    except Exception as e:
        print(f"激活窗口失败: {e}")
        return False

def check_kicked_with_ocr(win):
    """
    使用 OCR 检测窗口中心区域的异常文字
    """
    # 计算远程窗口的中心 50% 区域 (弹窗通常在屏幕正中间)
    x1 = win.left + (win.width * 0.25)
    y1 = win.top + (win.height * 0.25)
    x2 = win.left + (win.width * 0.75)
    y2 = win.top + (win.height * 0.75)
    
    # 防止坐标越界
    bbox = (int(x1), int(y1), int(x2), int(y2))
    
    # 仅截取中心区域，大幅提升 OCR 速度
    screen = ImageGrab.grab(bbox=bbox)
    img_np = np.array(screen)
    
    # 执行文字识别 (detail=1 返回坐标、文字和置信度，方便后续扩展点击逻辑)
    results = reader.readtext(img_np, detail=1)
    
    # 触发关键词
    keywords = ["异常", "断开", "连接", "确定", "踢出", "返回"]
    
    for bbox_coords, text, prob in results:
        for key in keywords:
            if key in text:
                print(f"[{time.strftime('%H:%M:%S')}] 警告！检测到异常文字: '{text}' (置信度: {prob:.2f})")
                
                # 扩展玩法：如果检测到“确定”，可以计算绝对坐标并自动点击
                if "确定" in text or "确认" in text:
                    # 计算文字中心的相对坐标
                    center_x = (bbox_coords[0][0] + bbox_coords[1][0]) / 2
                    center_y = (bbox_coords[0][1] + bbox_coords[2][1]) / 2
                    # 转换为屏幕绝对坐标
                    abs_click_x = int(x1 + center_x)
                    abs_click_y = int(y1 + center_y)
                    print(f"尝试自动点击 '确定' 按钮，坐标: ({abs_click_x}, {abs_click_y})")
                    pydirectinput.click(abs_click_x, abs_click_y)
                    
                return True
    return False

def safety_movement(win):
    """执行极短防掉线动作 (原地踏步)"""
    # 每次操作前确保窗口在最前
    if not focus_window(win):
        return
        
    # 模拟极短促的按键 (0.05s - 0.1s)，最大限度减少位移
    keys = ['w', 's', 'a', 'd']
    k = random.choice(keys)
    
    hold_time = random.uniform(0.05, 0.1)
    
    pydirectinput.keyDown(k)
    time.sleep(hold_time)
    pydirectinput.keyUp(k)
    
    # 补偿位移：如果是W则按S，如果是A则按D
    opp_map = {'w': 's', 's': 'w', 'a': 'd', 'd': 'a'}
    time.sleep(0.05) # 短暂缓冲
    
    pydirectinput.keyDown(opp_map[k])
    time.sleep(hold_time)
    pydirectinput.keyUp(opp_map[k])
    
    # 鼠标随机微动 (在窗口内部微调，防止鼠标移出窗口)
    dx = random.randint(-30, 30)
    dy = random.randint(-10, 10)
    # 将鼠标移动到窗口中心附近再微动，防止鼠标甩出边界
    center_x = win.left + win.width // 2
    center_y = win.top + win.height // 2
    pydirectinput.moveTo(center_x + dx, center_y + dy, duration=0.2)

def main():
    print("=== UU远程 PUBG 防掉线助手已启动 ===")
    print("提示：请按 Ctrl+C 停止脚本。建议让角色在游戏中面壁站立。")
    
    try:
        while True:
            # 1. 甄别并锁定远程窗口
            win = get_remote_window()
            if not win:
                print(f"[{time.strftime('%H:%M:%S')}] 未找到符合条件的远程桌面窗口，请检查 UU 远程是否已连接...")
                time.sleep(10)
                continue
                
            # 2. OCR 检测异常状态
            if check_kicked_with_ocr(win):
                print(f"[{time.strftime('%H:%M:%S')}] 状态：画面异常，暂停防掉线动作，等待人工处理或自动重连...")
                time.sleep(30) # 异常后休眠较长时间，防止疯狂输出
            else:
                # 3. 执行防掉线动作
                safety_movement(win)
                print(f"[{time.strftime('%H:%M:%S')}] 状态：已执行极微量位置抵消动作。")
            
            # 4. 随机长休眠 (45 - 90秒)
            # PUBG 的判定周期较长，不需要频繁按键，降低主控机 CPU 负担
            wait_time = random.randint(45, 90)
            print(f"[{time.strftime('%H:%M:%S')}] 等待 {wait_time} 秒后进行下一次扫描...")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\n=== 脚本已手动停止 ===")

if __name__ == "__main__":
    main()
