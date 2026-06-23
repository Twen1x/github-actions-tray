from __future__ import annotations

SUPPORTED = ("ru", "en")
DEFAULT_LANG = "ru"

_STRINGS: dict[str, dict[str, str]] = {
    "settings_title": {"ru": "Настройки", "en": "Settings"},
    "github_token": {"ru": "GitHub Token", "en": "GitHub Token"},
    "token_help": {
        "ru": "Создайте токен с доступом к репозиториям и вставьте его сюда: ",
        "en": "Create a token with repo access and paste it here: ",
    },
    "add": {"ru": "Добавить", "en": "Add"},
    "delete": {"ru": "Удалить", "en": "Delete"},
    "font_color_group": {"ru": "Цвет шрифта оверлея", "en": "Overlay font color"},
    "font_auto": {"ru": "Авто (по теме системы)", "en": "Auto (system theme)"},
    "font_custom": {"ru": "Свой цвет", "en": "Custom color"},
    "choose_color": {"ru": "Выбрать цвет", "en": "Choose color"},
    "show_overlay": {
        "ru": "Показывать оверлей на панели задач",
        "en": "Show overlay on the taskbar",
    },
    "autostart": {
        "ru": "Запускать при старте Windows",
        "en": "Run at Windows startup",
    },
    "save": {"ru": "Сохранить", "en": "Save"},
    "display_group": {
        "ru": "Что показывать (перетащите для порядка)",
        "en": "What to show (drag to reorder)",
    },
    "field_indicator": {"ru": "Индикатор", "en": "Indicator"},
    "field_label": {"ru": "Название", "en": "Label"},
    "field_sha": {"ru": "Коммит (номер)", "en": "Commit (sha)"},
    "field_author": {"ru": "Автор коммита", "en": "Commit author"},
    "field_message": {"ru": "Сообщение коммита", "en": "Commit message"},
    "field_time": {"ru": "Время", "en": "Time"},
    "language": {"ru": "Язык", "en": "Language"},
    "lang_ru": {"ru": "Русский", "en": "Russian"},
    "lang_en": {"ru": "Английский", "en": "English"},
    "tray_open_actions": {
        "ru": "Открыть Actions в браузере",
        "en": "Open Actions in browser",
    },
    "tray_settings": {"ru": "Настройки", "en": "Settings"},
    "tray_refresh": {"ru": "Обновить сейчас", "en": "Refresh now"},
    "tray_quit": {"ru": "Выход", "en": "Quit"},
    "err_config_title": {"ru": "Ошибки конфигурации", "en": "Configuration errors"},
    "err_open_link_title": {"ru": "Ошибка", "en": "Error"},
    "err_open_link": {
        "ru": "Не удалось открыть ссылку в браузере по умолчанию.\nОткройте вручную: ",
        "en": "Could not open the link in the default browser.\nOpen manually: ",
    },
    "err_color_title": {"ru": "Ошибка", "en": "Error"},
    "err_color": {
        "ru": "Недопустимый формат цвета. Ожидается '#RRGGBB'.",
        "en": "Invalid color format. Expected '#RRGGBB'.",
    },
    "ph_label": {"ru": "Метка", "en": "Label"},
    "ph_owner": {"ru": "Владелец (octocat)", "en": "Owner (octocat)"},
    "ph_repo": {"ru": "Репозиторий (my-repo)", "en": "Repo (my-repo)"},
    "ph_file": {"ru": "Workflow-файл (deploy.yml)", "en": "Workflow file (deploy.yml)"},
    "ph_branch": {"ru": "Ветка (main)", "en": "Branch (main)"},
    "tip_label": {
        "ru": "Подпись акшена в оверлее (любой текст)",
        "en": "Caption shown in the overlay (any text)",
    },
    "tip_owner": {
        "ru": "Владелец репозитория на GitHub (github.com/<owner>/...)",
        "en": "GitHub repository owner (github.com/<owner>/...)",
    },
    "tip_repo": {
        "ru": "Название репозитория",
        "en": "Repository name",
    },
    "tip_file": {
        "ru": "Имя файла workflow в .github/workflows/ (напр. deploy.yml)",
        "en": "Workflow file name in .github/workflows/ (e.g. deploy.yml)",
    },
    "tip_branch": {
        "ru": "Ветка, по которой берётся последний запуск",
        "en": "Branch whose latest run is shown",
    },
    "actions_hint": {
        "ru": "Запрос: github.com/<owner>/<repo>/actions/workflows/<file>/runs?branch=<branch>",
        "en": "Request: github.com/<owner>/<repo>/actions/workflows/<file>/runs?branch=<branch>",
    },
}

FIELD_KEYS = ("indicator", "label", "sha", "author", "message", "time")
DEFAULT_FIELDS = ["indicator", "label", "sha", "time"]

def normalize_lang(lang: str | None) -> str:
    if isinstance(lang, str) and lang.lower() in SUPPORTED:
        return lang.lower()
    return DEFAULT_LANG

def tr(key: str, lang: str = DEFAULT_LANG) -> str:
    lang = normalize_lang(lang)
    entry = _STRINGS.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get(DEFAULT_LANG, key))

def field_label(field_key: str, lang: str = DEFAULT_LANG) -> str:
    return tr(f"field_{field_key}", lang)
