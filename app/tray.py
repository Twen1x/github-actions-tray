from __future__ import annotations

import webbrowser
from typing import Callable

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app.action_state import ActionState
from app.i18n import normalize_lang, tr

COLOR_RUNNING = (227, 179, 65)
COLOR_RUNNING_DIM = (120, 96, 35)
COLOR_BG = (36, 41, 47)
COLOR_EMPTY_SLOT = (55, 62, 71)
COLOR_SUCCESS = (45, 164, 78)
COLOR_FAILURE = (203, 36, 49)
COLOR_UNKNOWN = (110, 118, 129)

APP_ICON_COLORS = [COLOR_SUCCESS, COLOR_FAILURE, COLOR_RUNNING, COLOR_UNKNOWN]


def app_icon():
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter, QPixmap

    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(QColor(*COLOR_BG))
        r, centers = circle_layout(4, size)
        painter = QPainter(pm)
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(Qt.NoPen)
            for color, (cx, cy) in zip(APP_ICON_COLORS, centers):
                painter.setBrush(QColor(*color))
                painter.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)
        finally:
            painter.end()
        icon.addPixmap(pm)
    return icon


def circle_layout(n: int, size: int) -> tuple[int, list[tuple[int, int]]]:
    pad = max(2, size // 16)
    q = size / 4
    r = size // 4 - pad
    tl = (int(q), int(q))
    bl = (int(q), int(3 * q))
    tr = (int(3 * q), int(q))
    br = (int(3 * q), int(3 * q))
    return r, [tl, bl, tr, br]


class IconRenderer:

    def render(self, states: list[ActionState], size: int = 64,
               pulse_on: bool = True):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor, QPainter, QPixmap

        n = len(states)
        pm = QPixmap(size, size)
        pm.fill(QColor(*COLOR_BG))

        r, centers = circle_layout(min(n, 4), size)

        painter = QPainter(pm)
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(Qt.NoPen)
            for i, (cx, cy) in enumerate(centers):
                if i < n:
                    st = states[i]
                    color = st.color()
                    if st.is_running and not pulse_on:
                        color = COLOR_RUNNING_DIM
                else:
                    color = COLOR_EMPTY_SLOT
                painter.setBrush(QColor(*color))
                painter.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)
        finally:
            painter.end()
        return pm


_CONCLUSION_TEXT = {
    "ru": {
        "success": "успех",
        "failure": "ошибка",
        "timed_out": "таймаут",
        "startup_failure": "ошибка запуска",
        "cancelled": "отменён",
        "skipped": "пропущен",
    },
    "en": {
        "success": "success",
        "failure": "failure",
        "timed_out": "timed out",
        "startup_failure": "startup failure",
        "cancelled": "cancelled",
        "skipped": "skipped",
    },
}
_RUNNING_TEXT = {"ru": "выполняется…", "en": "running…"}
_NODATA_TEXT = {"ru": "нет данных", "en": "no data"}
_REQERR_TEXT = {"ru": "ошибка запроса", "en": "request error"}
_CONNECTING_TEXT = {"ru": "подключение…", "en": "connecting…"}


def human_status(state, lang: str = "ru") -> str:
    lang = normalize_lang(lang)
    if state.error and not state.has_data:
        return f"{_REQERR_TEXT[lang]}: {state.error}"
    if getattr(state, "is_loading", False):
        return _CONNECTING_TEXT[lang]
    if state.is_running:
        return _RUNNING_TEXT[lang]
    if state.status == "completed":
        return _CONCLUSION_TEXT[lang].get(
            state.conclusion, state.conclusion or "—"
        )
    return _NODATA_TEXT[lang]


def actions_url(state) -> str:
    cfg = state.cfg
    return f"https://github.com/{cfg.owner}/{cfg.repo}/actions"


class TrayIcon:

    def __init__(
        self,
        states: list,
        renderer: IconRenderer | None = None,
        *,
        lang: str = "ru",
        on_open_actions: Callable[[], None] | None = None,
        on_settings: Callable[[], None] | None = None,
        on_refresh: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
        parent=None,
    ) -> None:
        self.states = states
        self.renderer = renderer or IconRenderer()
        self._lang = normalize_lang(lang)

        self.on_open_actions = on_open_actions
        self.on_settings = on_settings
        self.on_refresh = on_refresh
        self.on_quit = on_quit

        self._tray = QSystemTrayIcon(parent)
        self._build_menu()
        self.update_icon(states)

    @property
    def tray(self) -> QSystemTrayIcon:
        return self._tray

    def update_icon(self, states: list, pulse_on: bool = True) -> None:
        self.states = states
        pixmap = self.renderer.render(states, pulse_on=pulse_on)
        self._tray.setIcon(QIcon(pixmap))
        self._tray.setToolTip(self._tooltip())

    def show(self) -> None:
        self._tray.setVisible(True)

    def hide(self) -> None:
        self._tray.setVisible(False)

    def _tooltip(self) -> str:
        parts = ["GitHub Actions"]
        for st in self.states:
            parts.append(f"{st.label}: {human_status(st, self._lang)}")
        return "\n".join(parts)

    def set_language(self, lang: str) -> None:
        self._lang = normalize_lang(lang)
        self.action_open.setText(tr("tray_open_actions", self._lang))
        self.action_settings.setText(tr("tray_settings", self._lang))
        self.action_refresh.setText(tr("tray_refresh", self._lang))
        self.action_quit.setText(tr("tray_quit", self._lang))
        self._tray.setToolTip(self._tooltip())

    def _build_menu(self) -> None:
        menu = QMenu()

        self.action_open = menu.addAction(tr("tray_open_actions", self._lang))
        self.action_open.triggered.connect(self._handle_open_actions)

        self.action_settings = menu.addAction(tr("tray_settings", self._lang))
        self.action_settings.triggered.connect(self._handle_settings)

        self.action_refresh = menu.addAction(tr("tray_refresh", self._lang))
        self.action_refresh.triggered.connect(self._handle_refresh)

        menu.addSeparator()

        self.action_quit = menu.addAction(tr("tray_quit", self._lang))
        self.action_quit.triggered.connect(self._handle_quit)

        self._menu = menu
        self._tray.setContextMenu(menu)

    def _handle_open_actions(self, *_) -> None:
        if self.on_open_actions is not None:
            self.on_open_actions()
        elif self.states:
            webbrowser.open(actions_url(self.states[0]))

    def _handle_settings(self, *_) -> None:
        if self.on_settings is not None:
            self.on_settings()

    def _handle_refresh(self, *_) -> None:
        if self.on_refresh is not None:
            self.on_refresh()

    def _handle_quit(self, *_) -> None:
        if self.on_quit is not None:
            self.on_quit()
