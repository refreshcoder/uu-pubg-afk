import ctypes
from ctypes import wintypes
import pygetwindow as gw
import pydirectinput
import easyocr
import numpy as np
from PIL import ImageGrab
import random
import time


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
SW_RESTORE = 9


# 初始化 OCR 引擎 (首次运行会自动下载模型，请耐心等待)
print("正在加载 OCR 模型...")
reader = easyocr.Reader(["ch_sim", "en"])
print("OCR 模型加载完成！")


def get_remote_window():
    """
    智能查找实际的远程桌面窗口，排除控制面板。
    根据网易UU远程的进程特性，实际的远程控制窗口标题叫 "HOME"。
    """
    possible_windows = gw.getWindowsWithTitle("HOME")

    for win in possible_windows:
        if win.width > 800 and win.height > 600 and win.visible:
            return win
    return None


def get_window_hwnd(win):
    hwnd = getattr(win, "_hWnd", None)
    if hwnd is None:
        hwnd = getattr(win, "hWnd", None)
    return int(hwnd) if hwnd else 0


def get_foreground_hwnd():
    return int(user32.GetForegroundWindow() or 0)


def activate_hwnd(hwnd):
    """尽量可靠地将指定窗口切到前台。"""
    if not hwnd or not user32.IsWindow(hwnd):
        return False

    current_foreground = user32.GetForegroundWindow()
    current_thread = kernel32.GetCurrentThreadId()
    foreground_thread = user32.GetWindowThreadProcessId(current_foreground, None)
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)

    try:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)

        if foreground_thread:
            user32.AttachThreadInput(foreground_thread, current_thread, True)
        if target_thread:
            user32.AttachThreadInput(target_thread, current_thread, True)

        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
        user32.SetActiveWindow(hwnd)
        time.sleep(0.12)
        return user32.GetForegroundWindow() == hwnd
    finally:
        if foreground_thread:
            user32.AttachThreadInput(foreground_thread, current_thread, False)
        if target_thread:
            user32.AttachThreadInput(target_thread, current_thread, False)


def focus_window_temporarily(win):
    """短暂激活 UU 窗口，并返回原前台窗口句柄。"""
    hwnd = get_window_hwnd(win)
    previous_hwnd = get_foreground_hwnd()
    if not hwnd:
        return previous_hwnd, False

    try:
        if win.isMinimized:
            win.restore()
    except Exception:
        pass

    if activate_hwnd(hwnd):
        return previous_hwnd, True

    try:
        if not win.isActive:
            win.activate()
            time.sleep(0.2)
        return previous_hwnd, True
    except Exception as e:
        print(f"激活窗口失败: {e}")
        return previous_hwnd, False


def restore_previous_window(previous_hwnd):
    """将焦点恢复到输入前的前台窗口。"""
    if not previous_hwnd or not user32.IsWindow(previous_hwnd):
        return

    activate_hwnd(previous_hwnd)


def run_with_temporary_focus(win, action):
    """执行真实输入前短暂切到 UU 窗口，执行后立刻恢复原前台窗口。"""
    previous_hwnd, focused = focus_window_temporarily(win)
    if not focused:
        return False

    try:
        action()
        return True
    finally:
        time.sleep(0.05)
        restore_previous_window(previous_hwnd)


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

    keywords = ["错误"]

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

                    def do_click():
                        pydirectinput.click(abs_click_x, abs_click_y)

                    run_with_temporary_focus(win, do_click)

                return True
    return False


def safety_movement(win):
    """执行极短防掉线动作 (原地踏步 + 立即恢复原前台窗口)。"""
    keys = ["w", "s", "a", "d"]
    key = random.choice(keys)
    hold_time = random.uniform(0.05, 0.1)

    dx = random.randint(-30, 30)
    dy = random.randint(-10, 10)
    center_x = win.left + win.width // 2
    center_y = win.top + win.height // 2

    def do_input():
        pydirectinput.keyDown(key)
        time.sleep(hold_time)
        pydirectinput.keyUp(key)

        opp_map = {"w": "s", "s": "w", "a": "d", "d": "a"}
        time.sleep(0.05)

        pydirectinput.keyDown(opp_map[key])
        time.sleep(hold_time)
        pydirectinput.keyUp(opp_map[key])
        pydirectinput.moveTo(center_x + dx, center_y + dy, duration=0.2)

    if not run_with_temporary_focus(win, do_input):
        print("未能完成短暂切焦输入，跳过本轮防掉线动作。")


def main():
    print("=== UU远程 PUBG 后台防掉线助手已启动 ===")
    print("提示：脚本会短暂切到 UU 窗口发送真实输入，然后立即恢复原前台窗口。按 Ctrl+C 停止。")

    try:
        while True:
            win = get_remote_window()
            if not win:
                print(f"[{time.strftime('%H:%M:%S')}] 未找到符合条件的远程桌面窗口，请检查 UU 远程是否已连接...")
                time.sleep(10)
                continue

            if check_kicked_with_ocr(win):
                print(f"[{time.strftime('%H:%M:%S')}] 状态：画面异常，暂停防掉线动作，等待人工处理或自动重连...")
                time.sleep(30)
            else:
                safety_movement(win)
                print(f"[{time.strftime('%H:%M:%S')}] 状态：已执行极微量位置抵消动作。")

            wait_time = random.randint(45, 90)
            print(f"[{time.strftime('%H:%M:%S')}] 等待 {wait_time} 秒后进行下一次扫描...")
            time.sleep(wait_time)

    except KeyboardInterrupt:
        print("\n=== 脚本已手动停止 ===")


if __name__ == "__main__":
    main()
