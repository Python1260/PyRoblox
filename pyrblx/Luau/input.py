import ctypes
import threading
import time
import win32gui
import win32process

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_ESCAPE = 0x1B
MAPVK_VK_TO_VSC = 0

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ULONG_PTR)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_uint),
        ("dwFlags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ULONG_PTR)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_uint),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort)
    ]

class _INPUTunion(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint),
        ("union", _INPUTunion)
    ]

def get_hwnd_from_pid(pid):
    hwnds = []
    def cb(hwnd, lParam):
        tid, window_pid = win32process.GetWindowThreadProcessId(hwnd)
        if window_pid == pid and win32gui.IsWindowVisible(hwnd):
            hwnds.append(hwnd)
        return True
    win32gui.EnumWindows(cb, None)
    return hwnds[0] if hwnds else None

def focus_until(pid, func):
    hwnd = get_hwnd_from_pid(pid)

    stop_flag = {"stop": False}

    def focus_loop():
        while not stop_flag["stop"]:
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.0001)
    def focus_stop():
        func()
        stop_flag["stop"] = True

    threading.Thread(target=focus_loop, daemon=True).start()
    threading.Thread(target=focus_stop, daemon=True).start()

def send_keys(*keys):
    for key in keys:
        time.sleep(0.1)

        scan = user32.MapVirtualKeyW(key, MAPVK_VK_TO_VSC)

        inp_down = INPUT()
        inp_down.type = INPUT_KEYBOARD
        inp_down.union.ki.wVk = key
        inp_down.union.ki.wScan = scan
        inp_down.union.ki.dwFlags = 0
        inp_down.union.ki.time = 0
        inp_down.union.ki.dwExtraInfo = 0

        inp_up = INPUT()
        inp_up.type = INPUT_KEYBOARD
        inp_up.union.ki.wVk = key
        inp_up.union.ki.wScan = scan
        inp_up.union.ki.dwFlags = KEYEVENTF_KEYUP
        inp_up.union.ki.time = 0
        inp_up.union.ki.dwExtraInfo = 0

        arr = (INPUT * 2)(inp_down, inp_up)
        sent = user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(INPUT))