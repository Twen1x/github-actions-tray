from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

try:
    import win32gui
except Exception:
    win32gui = None

ABM_GETTASKBARPOS = 0x00000005

ABE_LEFT = 0
ABE_TOP = 1
ABE_RIGHT = 2
ABE_BOTTOM = 3

_EDGE_MAP = {
    ABE_LEFT: "left",
    ABE_TOP: "top",
    ABE_RIGHT: "right",
    ABE_BOTTOM: "bottom",
}

_DEFAULT_EDGE = "bottom"

class APPBARDATA(ctypes.Structure):

    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.UINT),
        ("uEdge", wintypes.UINT),
        ("rc", wintypes.RECT),
        ("lParam", wintypes.LPARAM),
    ]

def _shell32():
    try:
        shell32 = ctypes.windll.shell32
        fn = shell32.SHAppBarMessage
        fn.argtypes = [wintypes.DWORD, ctypes.POINTER(APPBARDATA)]
        fn.restype = ctypes.c_uint64
        return fn
    except Exception:
        return None

def _find_taskbar_hwnd():
    if win32gui is None:
        return 0
    try:
        return win32gui.FindWindow("Shell_TrayWnd", None) or 0
    except Exception:
        return 0

@dataclass
class Rect:

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

class TaskbarGeometry:

    def _query_taskbar_pos(self) -> APPBARDATA | None:
        fn = _shell32()
        if fn is None:
            return None
        try:
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = _find_taskbar_hwnd()
            result = fn(ABM_GETTASKBARPOS, ctypes.byref(abd))
            if not result:
                return None
            return abd
        except Exception:
            return None

    def taskbar_rect(self) -> Rect | None:
        abd = self._query_taskbar_pos()
        if abd is None:
            return None
        try:
            rc = abd.rc
            return Rect(int(rc.left), int(rc.top), int(rc.right), int(rc.bottom))
        except Exception:
            return None

    def tray_rect(self) -> Rect | None:
        if win32gui is None:
            return None
        try:
            tray = win32gui.FindWindow("Shell_TrayWnd", None)
            if not tray:
                return None
            notify = win32gui.FindWindowEx(tray, 0, "TrayNotifyWnd", None)
            if not notify:
                return None
            left, top, right, bottom = win32gui.GetWindowRect(notify)
            return Rect(int(left), int(top), int(right), int(bottom))
        except Exception:
            return None

    def edge(self) -> str:
        abd = self._query_taskbar_pos()
        if abd is None:
            return _DEFAULT_EDGE
        try:
            return _EDGE_MAP.get(int(abd.uEdge), _DEFAULT_EDGE)
        except Exception:
            return _DEFAULT_EDGE

    def bar_height(self) -> int | None:
        abd = self._query_taskbar_pos()
        if abd is None:
            return None
        try:
            edge = _EDGE_MAP.get(int(abd.uEdge), _DEFAULT_EDGE)
            rc = abd.rc
            if edge in ("bottom", "top"):
                return int(rc.bottom) - int(rc.top)
            return None
        except Exception:
            return None
