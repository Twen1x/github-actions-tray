# GitHub Actions Tray

[English](README.md) | **Русский**

Индикатор статуса GitHub Actions для Windows: иконка в системном трее плюс
компактный оверлей рядом с панелью задач. Отслеживает до **4 рабочих процессов**
одновременно и показывает их состояние в реальном времени без открытия браузера.

## Возможности

- Иконка в трее с 4 точками (по одной на каждое отслеживаемое действие).
- Оверлей у панели задач: индикатор, метка, SHA коммита, автор, сообщение, время.
- Периодический опрос GitHub Actions API (интервал настраивается).
- Цвета индикатора по статусу:

  | Цвет | Статус |
  |------|--------|
  | 🔵 синий | подключение (данных ещё нет) |
  | 🟡 жёлтый | выполняется (в очереди / в процессе) |
  | 🟢 зелёный | успех |
  | 🔴 красный | сбой (ошибка / таймаут / сбой запуска) |
  | ⚪ серый | нет данных / отменено / пустой слот |

- Языки интерфейса: русский и английский.
- Авто-тема (цвет текста следует за светлой/тёмной темой Windows) или свой цвет.
- Опциональный запуск при старте Windows.

## Загрузка

Скачайте последний **`GitHubActionsTray.exe`** со страницы
[Releases](https://github.com/Twen1x/github-actions-tray/releases) и запустите —
**Python и другие зависимости не нужны**. Исполняемый файл полностью автономный
(среда выполнения Python и все библиотеки упакованы внутрь).

> Python нужен только если вы хотите запускать из исходников или собирать
> исполняемый файл самостоятельно.

## Требования

- **Windows 10/11**
- **Python 3.9+** — только для запуска из исходников или сборки
- Зависимости: `PySide6`, `pywin32`, `requests` (см. `requirements.txt`)

## Запуск из исходников

```cmd
pip install -r requirements.txt
python main.py
```

При первом запуске, если `config.json` отсутствует или некорректен, окно настроек
открывается автоматически.

## Конфигурация

Конфигурация хранится в
`%LOCALAPPDATA%\GitHubActionsTray\config.json`
(обычно `C:\Users\<имя>\AppData\Local\GitHubActionsTray\config.json`).
Папка создаётся автоматически при первом сохранении.
Используйте `config.example.json` как отправную точку.

```json
{
  "github_token": "ghp_...",
  "poll_interval_seconds": 10,
  "language": "ru",
  "actions": [
    { "label": "DEV", "owner": "octocat", "repo": "my-repo", "file": "deploy.yml", "branch": "develop" }
  ],
  "overlay": {
    "enabled": true,
    "font_color": null,
    "fields": ["indicator", "label", "sha", "time"]
  }
}
```

### Поля

| Поле | Описание |
|------|----------|
| `github_token` | Персональный токен доступа с правом чтения Actions/репозитория. Не должен быть пустым или плейсхолдером. |
| `poll_interval_seconds` | Интервал опроса в секундах. Минимум **5**. |
| `language` | `ru` или `en`. |
| `actions[]` | От 1 до 4 объектов. Поля: `label`, `owner`, `repo`, `file` (имя файла workflow), `branch`. Все обязательны. |
| `overlay.enabled` | Показывать ли оверлей у панели задач. |
| `overlay.font_color` | `null` (авто по теме) или цвет в формате `#RRGGBB`. |
| `overlay.fields` | Какие поля показывать и в каком порядке: `indicator`, `label`, `sha`, `author`, `message`, `time`. |

Создать токен можно здесь: https://github.com/settings/tokens
Большинство настроек проще менять через окно настроек (правый клик по иконке в трее).

## Сборка .exe

Сборка создаёт **один файл** `release\GitHubActionsTray.exe` через PyInstaller.
Запускайте **из корня проекта**:

```cmd
build\build.bat
```

или PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File build\build.ps1
```

Скрипт устанавливает зависимости, генерирует иконку (`build\make_icon.py`), собирает
`.exe` и удаляет промежуточную папку `build\work`.

> Закройте запущенное приложение перед пересборкой (иконка в трее → «Выход»),
> иначе PyInstaller не сможет перезаписать `release\GitHubActionsTray.exe`.

## Автозапуск

Включается в окне настроек («Запускать при старте Windows»). Добавляет запись в
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.

## Структура проекта

```
main.py                  точка входа
app/                     пакет приложения
  config.py              модели конфигурации + загрузка/валидация config.json
  action_state.py        состояние одного действия + логика цветов
  poller.py              опрос GitHub Actions API
  tray.py                иконка в трее + отрисовка иконки
  overlay.py             оверлей у панели задач + геометрия + форматирование времени
  settings_window.py     окно настроек
  taskbar_geometry.py    геометрия панели задач (win32)
  theme.py               определение системной темы и цвета текста
  i18n.py                переводы RU/EN
  autostart.py           запуск при входе в Windows
build/                   скрипты сборки и spec-файл PyInstaller
assets/icon.ico          иконка приложения
config.example.json      пример конфигурации
```

## Лицензия

MIT — см. файл [LICENSE](LICENSE).
