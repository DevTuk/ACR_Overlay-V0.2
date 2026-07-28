@echo off
setlocal
cd /d "%~dp0"
set "PYTHON="
where py >nul 2>&1 && set "PYTHON=py -3"
if not defined PYTHON where python >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON (
    echo No se encontro Python.
    pause
    exit /b 1
)
%PYTHON% -m compileall -q main.py shortcut.py shortcut_dialog.py overlay acrally.py editor.py handbrake.py sharedmemory.py util.py
if errorlevel 1 goto :error
%PYTHON% -c "from overlay import Overlay; print('OK:', Overlay.__module__)"
if errorlevel 1 goto :error
echo.
echo Validacion correcta. El punto de entrada es overlay.app.Overlay.
pause
exit /b 0
:error
echo.
echo La validacion fallo.
pause
exit /b 1
