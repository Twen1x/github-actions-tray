from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app.config import ConfigError, is_valid_hex_color
from app.config import validate as validate_config
from app import autostart
from app.i18n import DEFAULT_FIELDS, FIELD_KEYS, field_label, normalize_lang, tr
from app.config import ActionConfig, AppConfig, OverlayConfig

MIN_ACTIONS = 1
MAX_ACTIONS = 4
_ACTION_FIELDS = ("label", "owner", "repo", "file", "branch")
GITHUB_TOKENS_URL = "https://github.com/settings/tokens"

class _ActionRow(QGroupBox):

    def __init__(self, index: int, on_delete: Callable[["_ActionRow"], None],
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_delete = on_delete
        self.set_index(index)

        layout = QHBoxLayout(self)
        self.edits: dict[str, QLineEdit] = {}
        for field_name in _ACTION_FIELDS:
            edit = QLineEdit(self)
            edit.setPlaceholderText(field_name)
            self.edits[field_name] = edit
            setattr(self, f"{field_name}_edit", edit)
            layout.addWidget(edit)

        self.delete_button = QPushButton("\u2715", self)
        self.delete_button.setFixedWidth(32)
        self.delete_button.clicked.connect(lambda: self._on_delete(self))
        layout.addWidget(self.delete_button)

    def set_index(self, index: int) -> None:
        self.index = index
        self.setTitle(f"Action {index}")

    def set_values(self, action: ActionConfig) -> None:
        self.label_edit.setText(action.label or "")
        self.owner_edit.setText(action.owner or "")
        self.repo_edit.setText(action.repo or "")
        self.file_edit.setText(action.file or "")
        self.branch_edit.setText(action.branch or "")

    def to_action(self) -> ActionConfig:
        return ActionConfig(
            label=self.label_edit.text(),
            owner=self.owner_edit.text(),
            repo=self.repo_edit.text(),
            file=self.file_edit.text(),
            branch=self.branch_edit.text(),
        )

class SettingsWindow(QWidget):

    def __init__(
        self,
        config_store=None,
        poller=None,
        cfg: AppConfig | None = None,
        on_saved: Callable[[AppConfig], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._config_store = config_store
        self._poller = poller
        self._on_saved = on_saved
        self._cfg: AppConfig | None = cfg
        self._font_color: str | None = None
        self._lang = normalize_lang(getattr(cfg, "language", "ru") if cfg else "ru")
        self._action_rows: list[_ActionRow] = []

        self._build_ui()
        self._retranslate()
        self.add_action()
        self._set_font_color_mode(None)
        self._populate_fields_list(list(DEFAULT_FIELDS))

        if cfg is not None:
            self.load_from(cfg)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        lang_row = QHBoxLayout()
        self.lang_label = QLabel(self)
        self.lang_combo = QComboBox(self)
        self.lang_combo.addItem("Русский", "ru")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self.lang_label)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch(1)
        root.addLayout(lang_row)

        self.token_group = QGroupBox(self)
        tg = QVBoxLayout(self.token_group)
        self.token_edit = QLineEdit(self.token_group)
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("github_token")
        tg.addWidget(self.token_edit)
        self.token_help = QLabel(self.token_group)
        self.token_help.setWordWrap(True)
        self.token_help.setOpenExternalLinks(False)
        self.token_help.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.token_help.linkActivated.connect(self._open_token_page)
        tg.addWidget(self.token_help)
        root.addWidget(self.token_group)

        self._actions_layout = QVBoxLayout()
        root.addLayout(self._actions_layout)
        self.add_button = QPushButton(self)
        self.add_button.clicked.connect(lambda *_: self.add_action())
        root.addWidget(self.add_button)

        self.actions_hint = QLabel(self)
        self.actions_hint.setWordWrap(True)
        self.actions_hint.setStyleSheet("color: gray; font-size: 11px;")
        root.addWidget(self.actions_hint)

        self.fields_group = QGroupBox(self)
        fg = QVBoxLayout(self.fields_group)
        self.fields_list = QListWidget(self.fields_group)
        self.fields_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.fields_list.setMaximumHeight(150)
        fg.addWidget(self.fields_list)
        root.addWidget(self.fields_group)

        self.color_group = QGroupBox(self)
        cg = QVBoxLayout(self.color_group)
        self.auto_radio = QRadioButton(self.color_group)
        self.custom_radio = QRadioButton(self.color_group)
        self._color_group_btn = QButtonGroup(self)
        self._color_group_btn.setExclusive(True)
        self._color_group_btn.addButton(self.auto_radio)
        self._color_group_btn.addButton(self.custom_radio)
        cg.addWidget(self.auto_radio)
        custom_row = QHBoxLayout()
        custom_row.addWidget(self.custom_radio)
        self.color_button = QPushButton(self.color_group)
        self.color_button.clicked.connect(self._choose_color)
        custom_row.addWidget(self.color_button)
        self.color_preview = QLabel("", self.color_group)
        custom_row.addWidget(self.color_preview)
        custom_row.addStretch(1)
        cg.addLayout(custom_row)
        self.auto_radio.toggled.connect(self._on_mode_changed)
        root.addWidget(self.color_group)

        self.enabled_check = QCheckBox(self)
        self.enabled_check.setChecked(True)
        root.addWidget(self.enabled_check)

        self.autostart_check = QCheckBox(self)
        self.autostart_check.setChecked(autostart.is_enabled())
        root.addWidget(self.autostart_check)

        self.save_button = QPushButton(self)
        self.save_button.clicked.connect(self.save)
        root.addWidget(self.save_button)

    def _retranslate(self) -> None:
        lang = self._lang
        self.setWindowTitle(tr("settings_title", lang))
        self.lang_label.setText(tr("language", lang) + ":")
        self.token_group.setTitle(tr("github_token", lang))
        self.token_help.setText(
            tr("token_help", lang)
            + f'<a href="{GITHUB_TOKENS_URL}">{GITHUB_TOKENS_URL}</a>'
        )
        self.add_button.setText(tr("add", lang))
        self.fields_group.setTitle(tr("display_group", lang))
        self.color_group.setTitle(tr("font_color_group", lang))
        self.auto_radio.setText(tr("font_auto", lang))
        self.custom_radio.setText(tr("font_custom", lang))
        self.color_button.setText(tr("choose_color", lang))
        self.enabled_check.setText(tr("show_overlay", lang))
        self.autostart_check.setText(tr("autostart", lang))
        self.save_button.setText(tr("save", lang))
        self.actions_hint.setText(tr("actions_hint", lang))
        for row in self._action_rows:
            row.delete_button.setToolTip(tr("delete", lang))
            for fname in _ACTION_FIELDS:
                row.edits[fname].setPlaceholderText(tr(f"ph_{fname}", lang))
                row.edits[fname].setToolTip(tr(f"tip_{fname}", lang))
        for i in range(self.fields_list.count()):
            item = self.fields_list.item(i)
            key = item.data(Qt.ItemDataRole.UserRole)
            item.setText(field_label(key, lang))

    def _on_language_changed(self, _index: int) -> None:
        self._lang = normalize_lang(self.lang_combo.currentData())
        self._retranslate()

    def _open_token_page(self, _url: str | None = None) -> None:
        if not QDesktopServices.openUrl(QUrl(GITHUB_TOKENS_URL)):
            QMessageBox.critical(
                self,
                tr("err_open_link_title", self._lang),
                tr("err_open_link", self._lang) + GITHUB_TOKENS_URL,
            )

    def _populate_fields_list(self, enabled_fields: list[str]) -> None:
        self.fields_list.clear()
        enabled = [f for f in enabled_fields if f in FIELD_KEYS]
        ordered = enabled + [f for f in FIELD_KEYS if f not in enabled]
        if "time" in ordered:
            ordered = [f for f in ordered if f != "time"] + ["time"]
        for key in ordered:
            item = QListWidgetItem(field_label(key, self._lang))
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsDragEnabled
            )
            item.setCheckState(
                Qt.CheckState.Checked if key in enabled else Qt.CheckState.Unchecked
            )
            self.fields_list.addItem(item)

    def _collect_fields(self) -> list[str]:
        out: list[str] = []
        for i in range(self.fields_list.count()):
            item = self.fields_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                out.append(item.data(Qt.ItemDataRole.UserRole))
        return out or list(DEFAULT_FIELDS)

    def _on_mode_changed(self, _checked: bool = False) -> None:
        self.color_button.setEnabled(self.custom_radio.isChecked())
        self._update_color_preview()

    def _set_font_color_mode(self, font_color: str | None) -> None:
        self._font_color = font_color
        if font_color is None:
            self.auto_radio.setChecked(True)
        else:
            self.custom_radio.setChecked(True)
        self.color_button.setEnabled(self.custom_radio.isChecked())
        self._update_color_preview()

    def _choose_color(self) -> None:
        if self._font_color and is_valid_hex_color(self._font_color):
            initial = QColor(self._font_color)
        else:
            initial = QColor("#FFFFFF")
        color = QColorDialog.getColor(initial, self, tr("choose_color", self._lang))
        if not color.isValid():
            return
        hex_value = color.name(QColor.NameFormat.HexRgb).upper()
        if not is_valid_hex_color(hex_value):
            QMessageBox.critical(
                self, tr("err_color_title", self._lang), tr("err_color", self._lang)
            )
            return
        self._font_color = hex_value
        self.custom_radio.setChecked(True)
        self._update_color_preview()

    def _update_color_preview(self) -> None:
        if self.custom_radio.isChecked() and self._font_color:
            self.color_preview.setText(self._font_color)
        else:
            self.color_preview.setText("")

    def _current_font_color(self) -> str | None:
        return None if self.auto_radio.isChecked() else self._font_color

    @property
    def action_count(self) -> int:
        return len(self._action_rows)

    def add_action(self, action: ActionConfig | None = None) -> None:
        if self.action_count >= MAX_ACTIONS:
            return
        if not isinstance(action, ActionConfig):
            action = None
        row = _ActionRow(self.action_count + 1, self._remove_row, self)
        if action is not None:
            row.set_values(action)
        row.delete_button.setToolTip(tr("delete", self._lang))
        for fname in _ACTION_FIELDS:
            row.edits[fname].setPlaceholderText(tr(f"ph_{fname}", self._lang))
            row.edits[fname].setToolTip(tr(f"tip_{fname}", self._lang))
        self._action_rows.append(row)
        self._actions_layout.addWidget(row)
        self._update_button_states()

    def remove_action(self) -> None:
        if self.action_count <= MIN_ACTIONS:
            return
        self._remove_row(self._action_rows[-1])

    def _remove_row(self, row: _ActionRow) -> None:
        if self.action_count <= MIN_ACTIONS:
            return
        if row not in self._action_rows:
            return
        self._action_rows.remove(row)
        self._actions_layout.removeWidget(row)
        row.setParent(None)
        row.deleteLater()
        self._renumber()
        self._update_button_states()

    def _clear_actions(self) -> None:
        while self._action_rows:
            row = self._action_rows.pop()
            self._actions_layout.removeWidget(row)
            row.setParent(None)
            row.deleteLater()

    def _renumber(self) -> None:
        for i, row in enumerate(self._action_rows, start=1):
            row.set_index(i)

    def _update_button_states(self) -> None:
        self.add_button.setEnabled(self.action_count < MAX_ACTIONS)
        only_one = self.action_count <= MIN_ACTIONS
        for row in self._action_rows:
            row.delete_button.setEnabled(not only_one)

    def load_from(self, cfg: AppConfig) -> None:
        self._cfg = cfg
        self._lang = normalize_lang(getattr(cfg, "language", "ru"))
        idx = self.lang_combo.findData(self._lang)
        if idx >= 0:
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(idx)
            self.lang_combo.blockSignals(False)

        self.token_edit.setText(cfg.github_token or "")

        overlay = cfg.overlay or OverlayConfig()
        self._set_font_color_mode(overlay.font_color)
        self.enabled_check.setChecked(getattr(overlay, "enabled", True))
        self.autostart_check.setChecked(autostart.is_enabled())
        self._populate_fields_list(
            list(getattr(overlay, "fields", None) or DEFAULT_FIELDS)
        )

        self._clear_actions()
        actions = list(cfg.actions or [])[:MAX_ACTIONS]
        if not actions:
            self.add_action()
        else:
            for action in actions:
                self.add_action(action)

        self._retranslate()

    def collect(self) -> AppConfig:
        actions = [row.to_action() for row in self._action_rows]
        base = self._cfg
        base_overlay = base.overlay if base is not None else OverlayConfig()
        overlay = OverlayConfig(
            pos_x=base_overlay.pos_x,
            pos_y=base_overlay.pos_y,
            follow_taskbar=base_overlay.follow_taskbar,
            font_color=self._current_font_color(),
            enabled=self.enabled_check.isChecked(),
            fields=self._collect_fields(),
        )
        poll_interval = base.poll_interval_seconds if base is not None else 10
        return AppConfig(
            github_token=self.token_edit.text(),
            poll_interval_seconds=poll_interval,
            actions=actions,
            overlay=overlay,
            language=self._lang,
        )

    def validate(self) -> list[str]:
        return list(validate_config(self.collect()))

    def save(self) -> bool:
        cfg = self.collect()
        errors = list(validate_config(cfg))
        if errors:
            self._show_errors(errors)
            return False
        if self._config_store is not None:
            try:
                self._config_store.save(cfg)
            except ConfigError as exc:
                self._show_errors(exc.errors)
                return False
        if self._poller is not None:
            self._poller.reconfigure(cfg)
        autostart.set_enabled(self.autostart_check.isChecked())
        self._cfg = cfg
        if self._on_saved is not None:
            self._on_saved(cfg)
        return True

    def _show_errors(self, errors: list[str]) -> None:
        QMessageBox.critical(
            self,
            tr("err_config_title", self._lang),
            "\n".join(errors) or "—",
        )
