from __future__ import annotations

import logging
import re

from app.config import OverlayConfig

logger = logging.getLogger(__name__)

Color = str

COLOR_WHITE: Color = "#FFFFFF"
COLOR_BLACK: Color = "#000000"

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

def _is_valid_hex_color(value: str) -> bool:
    return isinstance(value, str) and _HEX_COLOR_RE.match(value) is not None

def _read_apps_use_light_theme():
    return _read_personalize_dword("AppsUseLightTheme")

def _read_personalize_dword(name: str):
    try:
        import winreg
    except ImportError:
        return None

    sub_key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            value, value_type = winreg.QueryValueEx(key, name)
            if value_type != winreg.REG_DWORD:
                return None
            return int(value)
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return None

def taskbar_is_dark() -> bool:
    value = _read_personalize_dword("SystemUsesLightTheme")
    if value == 0:
        return True
    if value == 1:
        return False
    return True

def _qt_color_scheme_is_dark():
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import Qt

        app = QGuiApplication.instance()
        if app is None:
            return None
        scheme = app.styleHints().colorScheme()
        return scheme == Qt.ColorScheme.Dark
    except Exception:
        return None

def system_is_dark_theme() -> bool:
    try:
        value = _read_apps_use_light_theme()
        if value == 0:
            return True
        if value == 1:
            return False
        qt_dark = _qt_color_scheme_is_dark()
        if qt_dark is not None:
            return qt_dark
    except Exception:
        logger.debug("system_is_dark_theme detection failed", exc_info=True)
    return False

def resolve_text_color(overlay_cfg: OverlayConfig) -> Color:
    font_color = getattr(overlay_cfg, "font_color", None)
    if font_color is not None:
        if _is_valid_hex_color(font_color):
            return font_color.upper()
        logger.warning(
            "Invalid overlay font_color %r ignored; expected '#RRGGBB'. "
            "Falling back to system theme color.",
            font_color,
        )
    return COLOR_WHITE if system_is_dark_theme() else COLOR_BLACK
