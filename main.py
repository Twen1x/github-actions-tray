from __future__ import annotations

import logging
import signal
import sys
import webbrowser

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from app.action_state import ActionState
from app.config import ActionConfig, AppConfig, ConfigError, ConfigStore, OverlayConfig
from app.poller import Poller
from app.settings_window import SettingsWindow
from app.taskbar_geometry import TaskbarGeometry
from app.tray import IconRenderer, TrayIcon

logger = logging.getLogger(__name__)

PULSE_INTERVAL_MS = 600
MIN_POLL_INTERVAL = 5

def setup_dpi_awareness() -> None:
    import ctypes

    try:
        context = ctypes.c_void_p(-4)
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(context):
            return
    except Exception:
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def _default_config() -> AppConfig:
    return AppConfig(
        github_token="",
        poll_interval_seconds=10,
        actions=[ActionConfig(label="DEV", owner="", repo="", file="", branch="")],
        overlay=OverlayConfig(),
    )

def _build_states(cfg: AppConfig) -> list[ActionState]:
    return [ActionState(label=a.label, cfg=a) for a in cfg.actions]

class PollWorker(QObject):

    polled = Signal()

    def __init__(self, poller: Poller, interval_ms: int) -> None:
        super().__init__()
        self._poller = poller
        self._interval_ms = max(MIN_POLL_INTERVAL * 1000, int(interval_ms))
        self._timer: QTimer | None = None

    @Slot()
    def start(self) -> None:
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._tick()

    @Slot()
    def trigger(self) -> None:
        self._tick()

    @Slot(int)
    def set_interval(self, interval_ms: int) -> None:
        self._interval_ms = max(MIN_POLL_INTERVAL * 1000, int(interval_ms))
        if self._timer is not None:
            self._timer.setInterval(self._interval_ms)

    @Slot()
    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    def _tick(self) -> None:
        try:
            self._poller.poll_once()
        except Exception:
            logger.exception("poll_once failed")
        self.polled.emit()

class TrayApplication:

    def __init__(self, qt_app, config_store: ConfigStore | None = None) -> None:
        self.qt_app = qt_app
        self.qt_app.setQuitOnLastWindowClosed(False)

        self.config_store = config_store or ConfigStore()

        self._config_invalid = False
        try:
            self.cfg = self.config_store.load()
        except (ConfigError, OSError, ValueError) as exc:
            logger.warning("Could not load configuration: %s", exc)
            self.cfg = _default_config()
            self._config_invalid = True

        self.states: list[ActionState] = _build_states(self.cfg)
        self.poller = Poller(self.cfg, self.states)
        self.renderer = IconRenderer()
        self.geom = TaskbarGeometry()

        self._pulse_on = True

        self.settings_window = SettingsWindow(
            config_store=self.config_store,
            poller=self.poller,
            cfg=self.cfg,
            on_saved=self._on_saved,
        )

        from app.overlay import TaskbarOverlay

        self.overlay = TaskbarOverlay(
            self.cfg,
            self.states,
            self.config_store,
            settings_window=self.settings_window,
        )

        self.tray = TrayIcon(
            self.states,
            self.renderer,
            lang=getattr(self.cfg, "language", "ru"),
            on_open_actions=self._open_actions,
            on_settings=self._open_settings,
            on_refresh=self._request_poll,
            on_quit=self._quit,
        )

        self.poll_thread = QThread()
        self.poll_worker = PollWorker(self.poller, self._poll_interval_ms())
        self.poll_worker.moveToThread(self.poll_thread)
        self.poll_thread.started.connect(self.poll_worker.start)
        self.poll_worker.polled.connect(self._refresh_ui)
        self.poll_thread.finished.connect(self.poll_worker.deleteLater)

        self.pulse_timer = QTimer()
        self.pulse_timer.setInterval(PULSE_INTERVAL_MS)
        self.pulse_timer.timeout.connect(self._on_pulse_tick)

        self._connect_color_scheme_changed()

    def _poll_interval_ms(self) -> int:
        seconds = self.cfg.poll_interval_seconds
        if not isinstance(seconds, int) or seconds < MIN_POLL_INTERVAL:
            seconds = MIN_POLL_INTERVAL
        return seconds * 1000

    def _connect_color_scheme_changed(self) -> None:
        try:
            hints = self.qt_app.styleHints()
            hints.colorSchemeChanged.connect(self._on_color_scheme_changed)
        except Exception:
            logger.debug("colorSchemeChanged unavailable; theme follows poll tick")

    def _on_color_scheme_changed(self, *_args) -> None:
        self.overlay.update()

    def _request_poll(self) -> None:
        from PySide6.QtCore import QMetaObject, Qt

        QMetaObject.invokeMethod(
            self.poll_worker, "trigger", Qt.ConnectionType.QueuedConnection
        )

    def _on_pulse_tick(self) -> None:
        self._pulse_on = not self._pulse_on
        if any(st.is_running for st in self.states):
            self.tray.update_icon(self.states, pulse_on=self._pulse_on)

    def _refresh_ui(self) -> None:
        self.tray.update_icon(self.states, pulse_on=self._pulse_on)
        self.overlay.update_content(self.states)
        self.overlay.reposition(self.geom)

    def _open_actions(self) -> None:
        opened: set[str] = set()
        for st in self.states:
            cfg = st.cfg
            url = f"https://github.com/{cfg.owner}/{cfg.repo}/actions"
            if url in opened or not cfg.owner or not cfg.repo:
                continue
            opened.add(url)
            try:
                webbrowser.open(url)
            except Exception:
                logger.debug("could not open %s in browser", url)

    def _open_settings(self) -> None:
        sw = self.settings_window
        if sw is None:
            return
        if not sw.isVisible():
            sw.load_from(self.cfg)
            sw.show()
        sw.raise_()
        sw.activateWindow()

    def _quit(self) -> None:
        self.pulse_timer.stop()
        try:
            from PySide6.QtCore import QMetaObject, Qt

            QMetaObject.invokeMethod(
                self.poll_worker, "stop", Qt.ConnectionType.QueuedConnection
            )
            self.poll_thread.quit()
            self.poll_thread.wait(2000)
        except Exception:
            logger.debug("error while stopping poll thread", exc_info=True)
        self.qt_app.quit()

    def _on_saved(self, new_cfg: AppConfig) -> None:
        self.cfg = new_cfg
        self.overlay.cfg = new_cfg
        self.poller.cfg = new_cfg

        new_states = _build_states(new_cfg)
        self.states = new_states
        self.poller.states = new_states
        self.overlay.states = new_states

        from PySide6.QtCore import Q_ARG, QMetaObject, Qt

        QMetaObject.invokeMethod(
            self.poll_worker,
            "set_interval",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, self._poll_interval_ms()),
        )

        self._config_invalid = False

        try:
            self.tray.set_language(getattr(new_cfg, "language", "ru"))
        except Exception:
            logger.debug("could not update tray language")

        if new_cfg.overlay.enabled:
            self.overlay.show()
            self.overlay.reposition(self.geom)
        else:
            self.overlay.hide()

        self._refresh_ui()

    def start(self) -> None:
        self.tray.show()

        self.overlay.update_content(self.states)
        if self.cfg.overlay.enabled:
            self.overlay.show()
        else:
            self.overlay.hide()
        QTimer.singleShot(0, lambda: self.overlay.reposition(self.geom))

        self.pulse_timer.start()
        self.poll_thread.start()

        if self._config_invalid:
            self._open_settings()

    def run(self) -> int:
        self.start()
        return self.qt_app.exec()

def main() -> int:
    logging.basicConfig(level=logging.INFO)

    import faulthandler

    if sys.stderr is not None:
        faulthandler.enable()

    def _excepthook(exc_type, exc, tb):
        logger.error("Unhandled exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _excepthook

    setup_dpi_awareness()

    from PySide6.QtWidgets import QApplication

    qt_app = QApplication.instance() or QApplication(sys.argv)

    from app.tray import app_icon

    qt_app.setWindowIcon(app_icon())

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    _sigint_timer = QTimer()
    _sigint_timer.start(200)
    _sigint_timer.timeout.connect(lambda: None)

    application = TrayApplication(qt_app)
    return application.run()

if __name__ == "__main__":
    sys.exit(main())
