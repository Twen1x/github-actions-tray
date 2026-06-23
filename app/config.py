from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field

DEFAULT_OVERLAY_FIELDS = ["indicator", "label", "sha", "time"]


@dataclass
class ActionConfig:

    label: str
    owner: str
    repo: str
    file: str
    branch: str


@dataclass
class OverlayConfig:

    pos_x: int | None = None
    pos_y: int | None = None
    follow_taskbar: bool = True
    font_color: str | None = None
    enabled: bool = True
    fields: list[str] = field(default_factory=lambda: list(DEFAULT_OVERLAY_FIELDS))


@dataclass
class AppConfig:

    github_token: str
    poll_interval_seconds: int = 10
    actions: list[ActionConfig] = field(default_factory=list)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    language: str = "ru"


APP_NAME = "GitHubActionsTray"


def _config_dir() -> str:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(base, APP_NAME)


def _legacy_config_path() -> str:
    if getattr(sys, "frozen", False):
        here = os.path.dirname(sys.executable)
    else:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, "config.json")


_DEFAULT_CONFIG_PATH = os.path.join(_config_dir(), "config.json")

_TOKEN_PLACEHOLDER_RE = re.compile(r"^ghp_x+$", re.IGNORECASE)
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

_ACTION_REQUIRED_FIELDS = ("label", "owner", "repo", "file", "branch")

_MIN_POLL_INTERVAL = 5
_MIN_ACTIONS = 1
_MAX_ACTIONS = 4


def is_valid_hex_color(s: str) -> bool:
    if not isinstance(s, str):
        return False
    return _HEX_COLOR_RE.match(s) is not None


def validate(cfg: AppConfig) -> list[str]:
    errors: list[str] = []

    token = cfg.github_token
    if not isinstance(token, str) or not token.strip():
        errors.append("github_token: токен не должен быть пустым")
    elif _TOKEN_PLACEHOLDER_RE.match(token.strip()):
        errors.append(
            "github_token: токен равен плейсхолдеру 'ghp_xxxx...', укажите реальный токен"
        )

    actions = cfg.actions or []
    if not (_MIN_ACTIONS <= len(actions) <= _MAX_ACTIONS):
        errors.append(
            f"actions: число акшенов должно быть от {_MIN_ACTIONS} до {_MAX_ACTIONS} "
            f"включительно (сейчас {len(actions)})"
        )

    for index, action in enumerate(actions, start=1):
        for field_name in _ACTION_REQUIRED_FIELDS:
            value = getattr(action, field_name, None)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"actions[{index}].{field_name}: поле не должно быть пустым"
                )

    interval = cfg.poll_interval_seconds
    if not isinstance(interval, int) or isinstance(interval, bool):
        errors.append(
            "poll_interval_seconds: значение должно быть целым числом не меньше "
            f"{_MIN_POLL_INTERVAL} секунд"
        )
    elif interval < _MIN_POLL_INTERVAL:
        errors.append(
            f"poll_interval_seconds: значение должно быть не меньше {_MIN_POLL_INTERVAL} секунд"
        )

    font_color = cfg.overlay.font_color
    if font_color is not None and not is_valid_hex_color(font_color):
        errors.append(
            "overlay.font_color: ожидается None или цвет формата '#RRGGBB'"
        )

    return errors


class ConfigError(Exception):

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


class ConfigStore:

    def __init__(self, path: str | None = None) -> None:
        self.path = path or _DEFAULT_CONFIG_PATH

    def load(self) -> AppConfig:
        path = self.path
        if not os.path.exists(path):
            legacy = _legacy_config_path()
            if os.path.exists(legacy):
                path = legacy
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if not isinstance(raw, dict):
            raise ConfigError(["config.json: ожидается объект JSON в корне файла"])

        if "workflows" in raw:
            return self.migrate_legacy(raw)

        return self._deserialize(raw)

    def save(self, cfg: AppConfig) -> None:
        errors = validate(cfg)
        if errors:
            raise ConfigError(errors)

        data = self._serialize(cfg)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    def migrate_legacy(self, raw: dict) -> AppConfig:
        errors: list[str] = []

        workflows = raw.get("workflows")
        if not isinstance(workflows, list):
            workflows = []

        if len(workflows) > _MAX_ACTIONS:
            raise ConfigError([
                f"workflows: превышено максимальное количество акшенов "
                f"({_MAX_ACTIONS}); найдено {len(workflows)}"
            ])

        owner = raw.get("owner")
        repo = raw.get("repo")
        if not isinstance(owner, str) or not owner.strip():
            errors.append("owner: отсутствует обязательное глобальное поле")
        if not isinstance(repo, str) or not repo.strip():
            errors.append("repo: отсутствует обязательное глобальное поле")

        actions: list[ActionConfig] = []
        for index, wf in enumerate(workflows, start=1):
            if not isinstance(wf, dict):
                errors.append(f"workflows[{index}]: ожидается объект")
                continue
            label = wf.get("label")
            file = wf.get("file")
            branch = wf.get("branch")
            for field_name, value in (("label", label), ("file", file), ("branch", branch)):
                if not isinstance(value, str) or not value.strip():
                    errors.append(
                        f"workflows[{index}].{field_name}: отсутствует обязательное поле"
                    )
            actions.append(
                ActionConfig(
                    label=label if isinstance(label, str) else "",
                    owner=owner if isinstance(owner, str) else "",
                    repo=repo if isinstance(repo, str) else "",
                    file=file if isinstance(file, str) else "",
                    branch=branch if isinstance(branch, str) else "",
                )
            )

        if errors:
            raise ConfigError(errors)

        interval = raw.get("poll_interval_seconds", 10)
        cfg = AppConfig(
            github_token=raw.get("github_token", ""),
            poll_interval_seconds=interval,
            actions=actions,
            overlay=OverlayConfig(),
        )
        return cfg

    @staticmethod
    def _deserialize(raw: dict) -> AppConfig:
        actions_raw = raw.get("actions") or []
        actions = [
            ActionConfig(
                label=a.get("label", ""),
                owner=a.get("owner", ""),
                repo=a.get("repo", ""),
                file=a.get("file", ""),
                branch=a.get("branch", ""),
            )
            for a in actions_raw
            if isinstance(a, dict)
        ]

        overlay_raw = raw.get("overlay") or {}
        if not isinstance(overlay_raw, dict):
            overlay_raw = {}
        fields = overlay_raw.get("fields")
        if not isinstance(fields, list) or not fields:
            fields = None
        overlay = OverlayConfig(
            pos_x=overlay_raw.get("pos_x"),
            pos_y=overlay_raw.get("pos_y"),
            follow_taskbar=overlay_raw.get("follow_taskbar", True),
            font_color=overlay_raw.get("font_color"),
            enabled=overlay_raw.get("enabled", True),
        )
        if fields is not None:
            overlay.fields = [str(f) for f in fields]

        return AppConfig(
            github_token=raw.get("github_token", ""),
            poll_interval_seconds=raw.get("poll_interval_seconds", 10),
            actions=actions,
            overlay=overlay,
            language=raw.get("language", "ru"),
        )

    @staticmethod
    def _serialize(cfg: AppConfig) -> dict:
        return {
            "github_token": cfg.github_token,
            "poll_interval_seconds": cfg.poll_interval_seconds,
            "language": getattr(cfg, "language", "ru"),
            "actions": [
                {
                    "label": a.label,
                    "owner": a.owner,
                    "repo": a.repo,
                    "file": a.file,
                    "branch": a.branch,
                }
                for a in cfg.actions
            ],
            "overlay": {
                "pos_x": cfg.overlay.pos_x,
                "pos_y": cfg.overlay.pos_y,
                "follow_taskbar": cfg.overlay.follow_taskbar,
                "font_color": cfg.overlay.font_color,
                "enabled": cfg.overlay.enabled,
                "fields": list(getattr(cfg.overlay, "fields", [])),
            },
        }
