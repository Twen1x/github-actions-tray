@echo off
REM Build GitHub Actions Tray into release\GitHubActionsTray.exe
REM Usage (from the repo root):  build\build.bat
setlocal
cd /d "%~dp0.."

echo ==^> Installing build dependencies...
python -m pip install --upgrade pip || goto :err
python -m pip install -r requirements-dev.txt || goto :err

echo ==^> Generating application icon...
python build\make_icon.py || goto :err

echo ==^> Building executable with PyInstaller...
python -m PyInstaller build\app.spec --noconfirm --clean --distpath release --workpath build\work || goto :err

echo ==^> Cleaning up intermediate build files...
if exist build\work rmdir /s /q build\work
if exist GitHubActionsTray.spec del /q GitHubActionsTray.spec

echo.
echo Done. Executable: release\GitHubActionsTray.exe
goto :eof

:err
echo Build failed.
exit /b 1
