import pygetwindow as gw
import pydirectinput
import easyocr
import numpy as np
from PIL import ImageGrab
import ctypes
from ctypes import wintypes
import random
import time

# 初始化 OCR 引擎 (首次运行会自动下载模型，请耐心等待)
print("正在加载 OCR 模型...")
reader = easyocr.Reader(['ch_sim', 'en'])
print("OCR 模型加载完成！")

user32 = ctypes.windll.user32

OCR_INTERVAL_SECONDS = 10 * 60

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

def get_remote_window():
    """
    智能查找实际的远程桌面窗口，排除控制面板。
    根据网易UU远程的进程特性，实际的远程控制窗口标题叫 "HOME"。
    """
    possible_windows = gw.getWindowsWithTitle('HOME')

    minimized_candidate = None
    for win in possible_windows:
        if getattr(win, "isMinimized", False):
            minimized_candidate = minimized_candidate or win
            continue
        if win.width > 800 and win.height > 600:
            return win
    return minimized_candidate

def focus_window(win):
    """安全地将窗口恢复、置顶并激活。"""
    try:
        if win.isMinimized:
            win.restore()
            time.sleep(0.5)
        if not win.isActive:
            win.activate()
        time.sleep(0.5)
        return win.isActive
    except Exception as e:
        print(f"激活窗口失败: {e}")
        return False

def minimize_window(win):
    """在本轮结束后将目标窗口重新最小化。"""
    if not win:
        return
    try:
        if not win.isMinimized:
            win.minimize()
            time.sleep(0.3)
    except Exception as e:
        print(f"最小化窗口失败: {e}")

def get_cursor_position():
    """获取当前鼠标坐标，支持 Windows 虚拟桌面坐标系。"""
    point = POINT()
    if user32.GetCursorPos(ctypes.byref(point)):
        return (point.x, point.y)
    return None

def set_cursor_position(x, y):
    """恢复鼠标到指定屏幕坐标，兼容多显示器负坐标。"""
    user32.SetCursorPos(int(x), int(y))

def capture_desktop_state():
    """记录当前焦点窗口和鼠标位置。"""
    try:
        active_window = gw.getActiveWindow()
    except Exception:
        active_window = None

    cursor_pos = get_cursor_position()
    return {
        "active_window": active_window,
        "cursor_pos": cursor_pos,
    }

def describe_window(win):
    """生成用于日志输出的窗口描述。"""
    if not win:
        return "无"

    title = (win.title or "").strip() or "无标题窗口"
    left = getattr(win, "left", "?")
    top = getattr(win, "top", "?")
    width = getattr(win, "width", "?")
    height = getattr(win, "height", "?")
    return f"{title} @ ({left}, {top}, {width}x{height})"

def restore_desktop_state(state):
    """恢复本轮执行前的焦点窗口和鼠标位置。"""
    cursor_pos = state.get("cursor_pos")
    active_window = state.get("active_window")

    if active_window:
        try:
            if active_window.isMinimized:
                active_window.restore()
            if not active_window.isActive:
                active_window.activate()
            time.sleep(0.5)
        except Exception as e:
            print(f"恢复原焦点窗口失败: {e}")

    if cursor_pos is not None:
        try:
            set_cursor_position(*cursor_pos)
        except Exception as e:
            print(f"恢复鼠标位置失败: {e}")

def check_kicked_with_ocr(win):
    """
    使用 OCR 检测窗口中心区域的异常文字
    """
    x1 = win.left + (win.width * 0.25)
    y1 = win.top + (win.height * 0.25)
    x2 = win.left + (win.width * 0.75)
    y2 = win.top + (win.height * 0.75)

    bbox = (int(x1), int(y1), int(x2), int(y2))
    screen = ImageGrab.grab(bbox=bbox)
    img_np = np.array(screen)
    results = reader.readtext(img_np, detail=1)

    keywords = ["错误", "錯誤", "Error", "error"]

    for bbox_coords, text, prob in results:
        for key in keywords:
            if key in text:
                print(f"[{time.strftime('%H:%M:%S')}] 警告！检测到异常文字: '{text}' (置信度: {prob:.2f})")

                if "确定" in text or "确认" in text:
                    center_x = (bbox_coords[0][0] + bbox_coords[1][0]) / 2
                    center_y = (bbox_coords[0][1] + bbox_coords[2][1]) / 2
                    abs_click_x = int(x1 + center_x)
                    abs_click_y = int(y1 + center_y)
                    print(f"尝试自动点击 '确定' 按钮，坐标: ({abs_click_x}, {abs_click_y})")
                    pydirectinput.click(abs_click_x, abs_click_y)

                return True
    return False

def should_run_ocr(last_ocr_time):
    """控制 OCR 的执行频率，默认每 10 分钟最多执行一次。"""
    if last_ocr_time is None:
        return True
    return (time.time() - last_ocr_time) >= OCR_INTERVAL_SECONDS

def safety_movement(win):
    """执行极短防掉线动作 (原地踏步)"""
    dx = random.randint(-60, 60)
    dy = random.randint(-20, 20)
    center_x = win.left + win.width // 2
    center_y = win.top + win.height // 2
    pydirectinput.moveTo(center_x + dx, center_y + dy, duration=0.2)

    keys = ['w', 's', 'a', 'd']
    k = random.choice(keys)
    hold_time = random.uniform(0.1, 0.18)

    pydirectinput.keyDown(k)
    time.sleep(hold_time)
    pydirectinput.keyUp(k)

    opp_map = {'w': 's', 's': 'w', 'a': 'd', 'd': 'a'}
    time.sleep(0.05)

    pydirectinput.keyDown(opp_map[k])
    time.sleep(hold_time)
    pydirectinput.keyUp(opp_map[k])

def main():
    print("=== UU远程 PUBG 防掉线助手已启动 ===")
    print("提示：请按 Ctrl+C 停止脚本。建议让角色在游戏中面壁站立。")
    print("OCR 检测频率：每 10 分钟最多执行一次。")
    print("运行模式：每轮开始恢复并激活 HOME 窗口，结束后重新最小化。")

    last_ocr_time = None

    try:
        while True:
            win = get_remote_window()
            if not win:
                print(f"[{time.strftime('%H:%M:%S')}] 未找到符合条件的 HOME 窗口，请检查 UU 远程是否已连接...")
                time.sleep(10)
                continue

            desktop_state = capture_desktop_state()
            if not focus_window(win):
                restore_desktop_state(desktop_state)
                minimize_window(win)
                print(f"[{time.strftime('%H:%M:%S')}] 无法将 HOME 窗口恢复并切到前台，10 秒后重试...")
                time.sleep(10)
                continue

            print(
                f"[{time.strftime('%H:%M:%S')}] 已将 HOME 窗口恢复并切到前台。"
                f"本轮开始前焦点窗口: {describe_window(desktop_state['active_window'])}，"
                f"鼠标位置: {desktop_state['cursor_pos']}"
            )

            try:
                kicked = False
                if should_run_ocr(last_ocr_time):
                    print(f"[{time.strftime('%H:%M:%S')}] 开始执行 OCR 检测。")
                    kicked = check_kicked_with_ocr(win)
                    last_ocr_time = time.time()

                    if kicked:
                        print(f"[{time.strftime('%H:%M:%S')}] 状态：画面异常，暂停防掉线动作，等待人工处理或自动重连...")
                        time.sleep(30)
                    else:
                        safety_movement(win)
                        print(f"[{time.strftime('%H:%M:%S')}] 状态：已执行极微量位置抵消动作。")
                else:
                    next_ocr_in = int(max(0, OCR_INTERVAL_SECONDS - (time.time() - last_ocr_time)))
                    print(f"[{time.strftime('%H:%M:%S')}] 跳过 OCR 检测，距离下次 OCR 约还有 {next_ocr_in} 秒。")
                    safety_movement(win)
                    print(f"[{time.strftime('%H:%M:%S')}] 状态：已执行极微量位置抵消动作。")
            finally:
                restore_desktop_state(desktop_state)
                minimize_window(win)
                print(
                    f"[{time.strftime('%H:%M:%S')}] 本轮结束后已恢复焦点窗口，并重新最小化 HOME 窗口: "
                    f"{describe_window(desktop_state['active_window'])}，"
                    f"鼠标位置: {desktop_state['cursor_pos']}"
                )

            wait_time = random.randint(45, 90)
            print(f"[{time.strftime('%H:%M:%S')}] 等待 {wait_time} 秒后进行下一次扫描...")
            time.sleep(wait_time)

    except KeyboardInterrupt:
        print("\n=== 脚本已手动停止 ===")

if __name__ == "__main__":
    main()
