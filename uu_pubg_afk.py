import pygetwindow as gw
import pydirectinput
import ctypes
from ctypes import wintypes
import random
import time
from config_loader import load_config

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
config, config_error = load_config()
if config_error:
    print(f"[config] {config_error}, using built-in defaults")

SW_RESTORE = 9
SW_SHOW = 5
SW_MINIMIZE = 6
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = ctypes.c_void_p(-1)
HWND_NOTOPMOST = ctypes.c_void_p(-2)
FOREGROUND_RETRY_DELAY_SECONDS = 0.2
FOREGROUND_RETRY_COUNT = 3

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

def get_window_handle(win):
    """从 pygetwindow 窗口对象中提取底层 HWND。"""
    hwnd = getattr(win, "_hWnd", None)
    if hwnd is None:
        hwnd = getattr(win, "hWnd", None)
    return int(hwnd) if hwnd else None

def is_window_foreground(hwnd):
    """用原生 Win32 前台窗口句柄校验是否真正切到前台。"""
    if not hwnd:
        return False
    return user32.GetForegroundWindow() == hwnd

def wait_for_foreground(hwnd, retries=FOREGROUND_RETRY_COUNT, delay=FOREGROUND_RETRY_DELAY_SECONDS):
    """给窗口切前台留一个极短的异步生效时间。"""
    for _ in range(max(1, retries)):
        if is_window_foreground(hwnd):
            return True
        time.sleep(delay)
    return is_window_foreground(hwnd)

def force_window_foreground(hwnd):
    """
    通过 Win32 API 强制把窗口切到前台。
    pygetwindow.activate() 偶尔会抛出错误码 0 的假失败，这里做回退。
    """
    if not hwnd or not user32.IsWindow(hwnd):
        return False

    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.2)
    else:
        user32.ShowWindow(hwnd, SW_SHOW)

    current_foreground = user32.GetForegroundWindow()
    current_thread_id = kernel32.GetCurrentThreadId()
    foreground_thread_id = user32.GetWindowThreadProcessId(current_foreground, None) if current_foreground else 0
    target_thread_id = user32.GetWindowThreadProcessId(hwnd, None)
    attached_thread_ids = []

    try:
        for thread_id in (foreground_thread_id, target_thread_id):
            if thread_id and thread_id != current_thread_id and thread_id not in attached_thread_ids:
                if user32.AttachThreadInput(current_thread_id, thread_id, True):
                    attached_thread_ids.append(thread_id)

        user32.BringWindowToTop(hwnd)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
        user32.SetActiveWindow(hwnd)
    finally:
        for thread_id in reversed(attached_thread_ids):
            user32.AttachThreadInput(current_thread_id, thread_id, False)

    return wait_for_foreground(hwnd)

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
        if win.width > 100 and win.height > 100:
            return win
    return minimized_candidate

def focus_window(win):
    """安全地将窗口恢复、置顶并激活。"""
    hwnd = get_window_handle(win)
    if not hwnd:
        print("激活窗口失败: 未能获取目标窗口句柄。")
        return False

    try:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.5)

        if wait_for_foreground(hwnd, retries=1, delay=0):
            return True

        try:
            win.activate()
        except Exception as e:
            # pygetwindow 在 Windows 上偶发抛出“Error code 0”，但窗口可能已恢复。
            print(f"pygetwindow 激活报错，尝试 Win32 回退激活: {e}")

        if wait_for_foreground(hwnd):
            return True

        return force_window_foreground(hwnd)
    except Exception as e:
        if is_window_foreground(hwnd):
            return True
        print(f"激活窗口失败: {e}")
        return force_window_foreground(hwnd)

def minimize_window(win):
    """在本轮结束后将目标窗口重新最小化。"""
    if not win:
        return
    try:
        hwnd = get_window_handle(win)
        if hwnd and user32.IsWindow(hwnd) and not user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_MINIMIZE)
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
            if not focus_window(active_window):
                print("恢复原焦点窗口失败: 未能将原窗口重新切到前台。")
        except Exception as e:
            print(f"恢复原焦点窗口失败: {e}")

    if cursor_pos is not None:
        try:
            set_cursor_position(*cursor_pos)
        except Exception as e:
            print(f"恢复鼠标位置失败: {e}")

def safety_movement(win):
    """执行极短防掉线动作 (原地踏步)"""
    dx = random.randint(int(config["movement"]["mouse"]["offset_x"]["min"]), int(config["movement"]["mouse"]["offset_x"]["max"]))
    dy = random.randint(int(config["movement"]["mouse"]["offset_y"]["min"]), int(config["movement"]["mouse"]["offset_y"]["max"]))
    center_x = win.left + win.width // 2
    center_y = win.top + win.height // 2
    pydirectinput.moveTo(
        center_x + dx,
        center_y + dy,
        duration=float(config["movement"]["mouse"]["move_duration_seconds"]),
    )

    pydirectinput.mouseDown(button="right")
    time.sleep(float(config["movement"]["mouse"]["right_click"]["hold_seconds"]))
    pydirectinput.mouseUp(button="right")

    pydirectinput.click(button="right")
    time.sleep(
        random.uniform(
            float(config["movement"]["mouse"]["right_click"]["double_click_interval_seconds"]["min"]),
            float(config["movement"]["mouse"]["right_click"]["double_click_interval_seconds"]["max"]),
        )
    )
    pydirectinput.click(button="right")

    keys = list(config["movement"]["keyboard"]["wasd_keys"])
    k = random.choice(keys)
    hold_time = random.uniform(
        float(config["movement"]["keyboard"]["hold_seconds"]["min"]),
        float(config["movement"]["keyboard"]["hold_seconds"]["max"]),
    )

    pydirectinput.keyDown(k)
    time.sleep(hold_time)
    pydirectinput.keyUp(k)

    opp_map = {'w': 's', 's': 'w', 'a': 'd', 'd': 'a'}
    time.sleep(float(config["movement"]["keyboard"]["opp_sleep_seconds"]))

    pydirectinput.keyDown(opp_map[k])
    time.sleep(hold_time)
    pydirectinput.keyUp(opp_map[k])

    extra_times = random.randint(
        int(config["movement"]["keyboard"]["qe_times"]["min"]),
        int(config["movement"]["keyboard"]["qe_times"]["max"]),
    )
    for _ in range(extra_times):
        key = random.choice(list(config["movement"]["keyboard"]["qe_keys"]))
        press_time = random.uniform(
            float(config["movement"]["keyboard"]["qe_hold_seconds"]["min"]),
            float(config["movement"]["keyboard"]["qe_hold_seconds"]["max"]),
        )
        pydirectinput.keyDown(key)
        time.sleep(press_time)
        pydirectinput.keyUp(key)
        time.sleep(
            random.uniform(
                float(config["movement"]["keyboard"]["qe_interval_seconds"]["min"]),
                float(config["movement"]["keyboard"]["qe_interval_seconds"]["max"]),
            )
        )

def main():
    print("=== UU远程 PUBG 防掉线助手已启动 ===")
    print("提示：请按 Ctrl+C 停止脚本。建议让角色在游戏中面壁站立。")
    print("运行模式：每轮开始恢复并激活 HOME 窗口，结束后重新最小化。")
    start_ts = time.time()
    auto_exit_after = float(config["run"]["auto_exit_after_seconds"])

    try:
        while True:
            if auto_exit_after > 0 and (time.time() - start_ts) >= auto_exit_after:
                print(f"[{time.strftime('%H:%M:%S')}] Auto exit after {int(auto_exit_after)} seconds.")
                break

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
            time.sleep(float(config["loop"]["window_init_wait_seconds"]))

            try:
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

            wait_time = random.randint(
                int(config["loop"]["interval_seconds"]["min"]),
                int(config["loop"]["interval_seconds"]["max"]),
            )
            remaining = (start_ts + auto_exit_after) - time.time() if auto_exit_after > 0 else None
            if remaining is not None and remaining <= 0:
                print(f"[{time.strftime('%H:%M:%S')}] Auto exit after {int(auto_exit_after)} seconds.")
                break
            sleep_time = min(wait_time, remaining) if remaining is not None else wait_time
            print(f"[{time.strftime('%H:%M:%S')}] 等待 {int(sleep_time)} 秒后进行下一次扫描...")
            time.sleep(max(0, sleep_time))
            if remaining is not None and sleep_time < wait_time:
                print(f"[{time.strftime('%H:%M:%S')}] Auto exit after {int(auto_exit_after)} seconds.")
                break

    except KeyboardInterrupt:
        print("\n=== 脚本已手动停止 ===")

if __name__ == "__main__":
    main()
