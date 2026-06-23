from __future__ import annotations

import logging

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from typing import NamedTuple

from app.theme import taskbar_is_dark


class Size(NamedTuple):
    width: int
    height: int


PAD_L = 10
PAD_R = 10
PAD_V = 4
IND_W = 14
GAP = 8
ROW_MIN_H = 20

_RT_MINUTE = 60
_RT_HOUR = 3600
_RT_DAY = 86400
_RT_MAX_DAYS = 9999
_RT_UNKNOWN = "--"


def format_relative_time(t, now=None) -> str:
    from datetime import datetime

    if not isinstance(t, datetime):
        return _RT_UNKNOWN

    try:
        reference = now if now is not None else datetime.now(t.tzinfo)
        elapsed = (reference - t).total_seconds()
    except (TypeError, ValueError, OverflowError, OSError):
        return _RT_UNKNOWN

    if elapsed < 0:
        return "0s"

    if elapsed < _RT_MINUTE:
        return f"{int(elapsed)}s"
    if elapsed < _RT_HOUR:
        return f"{int(elapsed // _RT_MINUTE)}m"
    if elapsed < _RT_DAY:
        return f"{int(elapsed // _RT_HOUR)}h"

    days = int(elapsed // _RT_DAY)
    if days > _RT_MAX_DAYS:
        days = _RT_MAX_DAYS
    return f"{days}d"

try:
    import win32api
    import win32gui
except Exception:
    win32api = None
    win32gui = None

def enable_acrylic(hwnd: int, dark: bool) -> bool:
    try:
        import ctypes
        from ctypes import wintypes

        class ACCENTPOLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint),
                ("AnimationId", ctypes.c_int),
            ]

        class WINCOMPATTRDATA(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.POINTER(ACCENTPOLICY)),
                ("SizeOfData", ctypes.c_size_t),
            ]

        ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
        WCA_ACCENT_POLICY = 19

        tint = 0xB0202020 if dark else 0xB0F2F2F2

        accent = ACCENTPOLICY()
        accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 0
        accent.GradientColor = tint
        accent.AnimationId = 0

        data = WINCOMPATTRDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.SizeOfData = ctypes.sizeof(accent)
        data.Data = ctypes.pointer(accent)

        set_wca = ctypes.windll.user32.SetWindowCompositionAttribute
        set_wca.argtypes = [wintypes.HWND, ctypes.POINTER(WINCOMPATTRDATA)]
        set_wca.restype = ctypes.c_int
        return bool(set_wca(int(hwnd), ctypes.byref(data)))
    except Exception:
        return False

FULLSCREEN_POLL_MS = 1000
_MONITOR_DEFAULTTONEAREST = 2
_FULLSCREEN_EXCLUDED_CLASSES = {
    "WorkerW",
    "Progman",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
}

BG_RADIUS = 6
DEFAULT_BAR_HEIGHT = 40
FONT_PX = 11
AUTHOR_MAX_W = 90
MESSAGE_MAX_W = 160
MESSAGE_MAX_CHARS = 8
EMBED_IN_TASKBAR = True
RIGHT_MARGIN = 8
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_SWP_SHOWWINDOW = 0x0040
_SWP_ASYNCWINDOWPOS = 0x4000
_GWL_STYLE = -16
_WS_CHILD = 0x40000000
_WS_POPUP = 0x80000000

class TaskbarOverlay(QWidget):

    def __init__(
        self,
        cfg,
        states: list,
        config_store,
        settings_window=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.cfg = cfg
        self.states = states
        self.config_store = config_store
        self.settings_window = settings_window

        self._hidden_for_fullscreen = False
        self._embedded = False
        self._hwnd = None
        self._last_placed_size = None
        self._geom = None

        self._setup_window_flags()
        self.setup_appearance()
        initial = self._compute_size()
        self.resize(initial.width, initial.height)
        self._acrylic = False
        self._apply_glass()
        self._setup_fullscreen_watch()

    def _apply_glass(self) -> None:
        return

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_glass()

    def _setup_window_flags(self) -> None:
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )

    def setup_appearance(self) -> None:
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setFocusPolicy(Qt.NoFocus)

    def text_color(self) -> QColor:
        fc = getattr(self.cfg.overlay, "font_color", None)
        if fc:
            c = QColor(fc)
            if c.isValid():
                return c
        return QColor("#FFFFFF") if taskbar_is_dark() else QColor("#000000")

    def update_content(self, states: list) -> None:
        self.states = states
        self.repaint()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        try:
            rect = self.rect()
            text_color = self.text_color()
            self._paint_background(painter, rect, text_color)
            self._paint_content(painter, rect, text_color)
        finally:
            painter.end()

    def _paint_background(self, painter: QPainter, rect, text_color: QColor) -> None:
        return

    def _visible_fields(self) -> list[str]:
        from app.i18n import DEFAULT_FIELDS, FIELD_KEYS

        raw = getattr(self.cfg.overlay, "fields", None) or []
        fields = [f for f in raw if f in FIELD_KEYS]
        fields = fields or list(DEFAULT_FIELDS)
        if "time" in fields:
            fields = [f for f in fields if f != "time"] + ["time"]
        return fields

    def _field_text(self, st, key: str) -> str:
        if key == "label":
            return str(getattr(st, "label", "") or "")
        if getattr(st, "is_loading", False):
            return "\u2026"
        if key == "sha":
            return st.short_sha()
        if key == "author":
            return st.author_text()
        if key == "message":
            msg = st.message_text()
            if msg != "--" and len(msg) > MESSAGE_MAX_CHARS:
                msg = msg[:MESSAGE_MAX_CHARS] + "\u2026"
            return msg
        if key == "time":
            return (
                format_relative_time(st.last_commit_time)
                if st.last_commit_time is not None
                else "--"
            )
        return ""

    def _field_columns(self, fm) -> list[tuple[str, int]]:
        cols: list[tuple[str, int]] = []
        for key in self._visible_fields():
            if key == "indicator":
                cols.append((key, IND_W))
                continue
            widths = [fm.horizontalAdvance(self._field_text(s, key))
                      for s in self.states] or [0]
            w = max(widths)
            if key == "author":
                w = min(max(w, fm.horizontalAdvance("nick")), AUTHOR_MAX_W)
            elif key == "message":
                w = min(max(w, 40), MESSAGE_MAX_W)
            elif key == "sha":
                w = max(w, fm.horizontalAdvance("9999999"))
            elif key == "time":
                w = max(w, fm.horizontalAdvance("888m"))
            elif key == "label":
                w = max(w, fm.horizontalAdvance("PROD"))
            cols.append((key, int(w)))
        return cols

    def _paint_content(self, painter: QPainter, rect, text_color: QColor) -> None:
        n = len(self.states)
        if n == 0:
            return

        from PySide6.QtGui import QFont, QFontMetrics

        font = QFont(painter.font())
        font.setPixelSize(FONT_PX)
        painter.setFont(font)
        fm = QFontMetrics(font)

        cols = self._field_columns(fm)

        inner_top = rect.top() + PAD_V
        inner_h = rect.height() - 2 * PAD_V
        row_h = inner_h / n if n else inner_h
        indicator_d = max(5.0, min(row_h * 0.55, 12.0))

        for i, st in enumerate(self.states):
            top = inner_top + i * row_h
            cy = top + row_h / 2.0
            x = rect.left() + PAD_L

            for key, w in cols:
                if key == "indicator":
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(*st.color()))
                    painter.drawEllipse(
                        QRectF(x + (w - indicator_d) / 2.0,
                               cy - indicator_d / 2.0,
                               indicator_d, indicator_d)
                    )
                else:
                    text = self._field_text(st, key)
                    if key in ("author", "message"):
                        text = fm.elidedText(text, Qt.ElideRight, w)
                    painter.setPen(text_color)
                    painter.drawText(
                        QRectF(x, top, w, row_h),
                        int(Qt.AlignVCenter | Qt.AlignLeft),
                        text,
                    )
                x += w + GAP

    def reposition(self, geom) -> None:
        overlay_cfg = self.cfg.overlay
        self._geom = geom
        if not getattr(overlay_cfg, "enabled", True):
            if self.isVisible():
                self.hide()
            return

        try:
            size = self._compute_size()
            self.resize(size.width, size.height)

            if self._place_on_taskbar(geom, size):
                return

            from PySide6.QtWidgets import QApplication

            screen = self.screen() or QApplication.primaryScreen()
            if screen is None:
                return
            geo = screen.geometry()
            avail = screen.availableGeometry()
            tb_top = avail.bottom() + 1
            tb_h = geo.bottom() - avail.bottom()
            if tb_h <= 1:
                tb_top = avail.bottom() - size.height + 1
                tb_h = size.height
            x = geo.right() - size.width - RIGHT_MARGIN
            y = tb_top + max(0, (tb_h - size.height)) // 2
            self.move(int(x), int(y))
            self.raise_()
        except Exception:
            logging.getLogger(__name__).debug("reposition failed", exc_info=True)

    def _place_on_taskbar(self, geom, size: Size) -> bool:
        if win32gui is None:
            return False
        try:
            bar = geom.taskbar_rect()
            if bar is None:
                return False
            tray = geom.tray_rect()
            if self._hwnd is None:
                self._hwnd = int(self.winId())
            hwnd = self._hwnd

            dpr = self._device_pixel_ratio()
            w = int(round(size.width * dpr))
            h = int(round(size.height * dpr))
            anchor_left = tray.left if tray is not None else bar.right - 200
            x = anchor_left - w - int(round(8 * dpr))
            y = bar.top + (bar.height - h) // 2

            _HWND_TOPMOST = -1
            win32gui.SetWindowPos(
                hwnd, _HWND_TOPMOST, int(x), int(y), w, h,
                _SWP_NOACTIVATE | _SWP_SHOWWINDOW,
            )
            self._last_placed_size = size
            return True
        except Exception:
            logging.getLogger(__name__).debug("place_on_taskbar failed", exc_info=True)
            return False

    def _compute_size(self) -> Size:
        from PySide6.QtGui import QFont, QFontMetrics

        n = max(1, len(self.states))
        font = QFont(self.font())
        font.setPixelSize(FONT_PX)
        fm = QFontMetrics(font)
        cols = self._field_columns(fm)
        width = PAD_L + PAD_R
        if cols:
            width += sum(w for _k, w in cols) + GAP * (len(cols) - 1)
        row_h = max(ROW_MIN_H, FONT_PX + 8)
        height = n * row_h + 2 * PAD_V
        return Size(int(width), int(height))

    def _embed_and_place(self, size: Size) -> bool:
        if win32gui is None:
            return False
        try:
            tb = win32gui.FindWindow("Shell_TrayWnd", None)
            if not tb:
                return False
            if self._hwnd is None:
                self._hwnd = int(self.winId())
            hwnd = self._hwnd
            if not self._embedded:
                style = win32gui.GetWindowLong(hwnd, _GWL_STYLE)
                style = (style | _WS_CHILD) & ~_WS_POPUP
                win32gui.SetWindowLong(hwnd, _GWL_STYLE, style)
                win32gui.SetParent(hwnd, tb)
                self._embedded = True

            tb_l, tb_t, tb_r, tb_b = win32gui.GetWindowRect(tb)
            notify = win32gui.FindWindowEx(tb, 0, "TrayNotifyWnd", None)
            anchor_left = (
                win32gui.GetWindowRect(notify)[0] if notify else tb_r - 200
            )
            dpr = self._device_pixel_ratio()
            w = int(round(size.width * dpr))
            h = int(round(size.height * dpr))
            x = (anchor_left - tb_l) - w - int(round(8 * dpr))
            y = ((tb_b - tb_t) - h) // 2
            if x < 0:
                x = 0
            if y < 0:
                y = 0
            win32gui.SetWindowPos(
                hwnd, 0, x, y, w, h,
                _SWP_NOZORDER | _SWP_NOACTIVATE | _SWP_SHOWWINDOW,
            )
            return True
        except Exception:
            return False

    def _device_pixel_ratio(self) -> float:
        try:
            dpr = float(self.devicePixelRatioF())
            if dpr > 0:
                return dpr
        except Exception:
            pass
        try:
            screen = self.screen()
            if screen is not None:
                dpr = float(screen.devicePixelRatio())
                if dpr > 0:
                    return dpr
        except Exception:
            pass
        return 1.0

    def _setup_fullscreen_watch(self) -> None:
        self._fullscreen_timer = QTimer(self)
        self._fullscreen_timer.setInterval(FULLSCREEN_POLL_MS)
        self._fullscreen_timer.timeout.connect(self._check_fullscreen)
        self._fullscreen_timer.start()

    def _check_fullscreen(self) -> None:
        try:
            fullscreen = self._foreground_is_fullscreen()
        except Exception:
            fullscreen = False

        if not getattr(self.cfg.overlay, "enabled", True):
            if self.isVisible():
                self.hide()
            return

        if self._embedded:
            return

        if fullscreen:
            if not self._hidden_for_fullscreen:
                self._hidden_for_fullscreen = True
                self.hide()
            return

        if self._hidden_for_fullscreen:
            self._hidden_for_fullscreen = False
            self.show()

        if self._geom is not None:
            try:
                self._place_on_taskbar(self._geom, self._compute_size())
            except Exception:
                logging.getLogger(__name__).debug("re-raise failed", exc_info=True)

    def _foreground_is_fullscreen(self) -> bool:
        if win32gui is None:
            return False

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False

        try:
            own_hwnd = int(self.winId())
        except Exception:
            own_hwnd = 0
        if hwnd == own_hwnd:
            return False

        try:
            cls = win32gui.GetClassName(hwnd)
        except Exception:
            cls = ""
        if cls in _FULLSCREEN_EXCLUDED_CLASSES:
            return False

        try:
            win_left, win_top, win_right, win_bottom = win32gui.GetWindowRect(hwnd)
        except Exception:
            return False

        monitor_rect = self._overlay_monitor_rect()
        if monitor_rect is None:
            return False

        mon_left, mon_top, mon_right, mon_bottom = monitor_rect
        return (
            win_left <= mon_left
            and win_top <= mon_top
            and win_right >= mon_right
            and win_bottom >= mon_bottom
        )

    def _overlay_monitor_rect(self):
        if win32api is None:
            return None
        try:
            own_hwnd = int(self.winId())
            monitor = win32api.MonitorFromWindow(
                own_hwnd, _MONITOR_DEFAULTTONEAREST
            )
            info = win32api.GetMonitorInfo(monitor)
            return tuple(info["Monitor"])
        except Exception:
            return None

