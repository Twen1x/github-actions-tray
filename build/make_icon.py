from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ASSETS = os.path.join(ROOT, "assets")
ICON_PATH = os.path.join(ASSETS, "icon.ico")


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    from app.tray import circle_layout
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

    QGuiApplication.instance() or QGuiApplication([])
    os.makedirs(ASSETS, exist_ok=True)

    colors = [
        (45, 164, 78),
        (203, 36, 49),
        (227, 179, 65),
        (110, 118, 129),
    ]
    bg = (36, 41, 47)
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(QColor(*bg))
        r, centers = circle_layout(4, size)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        for color, (cx, cy) in zip(colors, centers):
            p.setBrush(QColor(*color))
            p.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)
        p.end()
        icon.addPixmap(pm)

    big = icon.pixmap(256, 256)
    if not big.save(ICON_PATH, "ICO"):
        print("Failed to write", ICON_PATH)
        return 1
    print("Wrote", ICON_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
