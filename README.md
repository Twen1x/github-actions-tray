# GitHub Actions Tray

A GitHub Actions status indicator for Windows: a system tray icon plus a compact
overlay next to the taskbar. Tracks up to **4 workflows** at once and shows their
state in real time without opening a browser.

## Features

- Tray icon with 4 dots (one per tracked action).
- Taskbar overlay: indicator, label, commit SHA, author, message, time.
- Periodic polling of the GitHub Actions API (configurable interval).
- Indicator colors by status:

  | Color | Status |
  |-------|--------|
  | 🔵 blue | connecting (no data yet) |
  | 🟡 yellow | running (queued / in progress) |
  | 🟢 green | success |
  | 🔴 red | failure (failure / timed out / startup failure) |
  | ⚪ gray | no data / cancelled / empty slot |

- Interface languages: Russian and English.
- Auto theme (text color follows the Windows light/dark theme) or a custom color.
- Optional "run at Windows startup".

## Download

Grab the latest **`GitHubActionsTray.exe`** from the
[Releases](https://github.com/Twen1x/github-actions-tray/releases) page and run it —
**no Python or other dependencies required**. The executable is fully self-contained
(the Python runtime and all libraries are bundled inside).

> Python is only needed if you want to run from source or build the executable yourself.

## Requirements

- **Windows 10/11**
- **Python 3.9+** — only for running from source or building
- Dependencies: `PySide6`, `pywin32`, `requests` (see `requirements.txt`)

## Run from source

```cmd
pip install -r requirements.txt
python main.py
```

On first launch, if `config.json` is missing or invalid, the settings window opens
automatically.

## Configuration

The configuration is stored in
`%LOCALAPPDATA%\GitHubActionsTray\config.json`
(usually `C:\Users\<name>\AppData\Local\GitHubActionsTray\config.json`).
The folder is created automatically on first save.
location on the next save. Use `config.example.json` as a starting point.

```json
{
  "github_token": "ghp_...",
  "poll_interval_seconds": 10,
  "language": "en",
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

### Fields

| Field | Description |
|-------|-------------|
| `github_token` | Personal Access Token with read access to Actions/repository. Must not be empty or a placeholder. |
| `poll_interval_seconds` | Polling interval in seconds. Minimum **5**. |
| `language` | `ru` or `en`. |
| `actions[]` | 1 to 4 objects. Fields: `label`, `owner`, `repo`, `file` (workflow file name), `branch`. All required. |
| `overlay.enabled` | Whether to show the taskbar overlay. |
| `overlay.font_color` | `null` (auto by theme) or a `#RRGGBB` color. |
| `overlay.fields` | Which fields to show and in what order: `indicator`, `label`, `sha`, `author`, `message`, `time`. |

Create a token here: https://github.com/settings/tokens
Most settings are easier to change via the Settings window (right-click the tray icon).

## Build the .exe

The build produces a **single file** `release\GitHubActionsTray.exe` via PyInstaller.
Run **from the project root**:

```cmd
build\build.bat
```

or PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File build\build.ps1
```

The script installs dependencies, generates the icon (`build\make_icon.py`), builds
the `.exe`, and removes the intermediate `build\work` folder.

> Close the running app before rebuilding (tray icon → "Exit"), otherwise PyInstaller
> cannot overwrite `release\GitHubActionsTray.exe`.

## Autostart

Enabled in the settings window ("Run at Windows startup"). Adds an entry under
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.

## Project structure

```
main.py                  entry point
app/                     application package
  config.py              config models + loading/validation of config.json
  action_state.py        single action state + color logic
  poller.py              GitHub Actions API polling
  tray.py                tray icon + icon rendering
  overlay.py             taskbar overlay + geometry + relative time formatting
  settings_window.py     settings window
  taskbar_geometry.py    taskbar geometry (win32)
  theme.py               system theme detection and text color
  i18n.py                RU/EN translations
  autostart.py           run at Windows login
build/                   build scripts and PyInstaller spec
assets/icon.ico          application icon
config.example.json      example configuration
```

## License

MIT — see the [LICENSE](LICENSE) file.
