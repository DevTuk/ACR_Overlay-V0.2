@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Compilar ACRally Pacenote Overlay - ONEFILE

set "APP_NAME=ACRally Pacenote Overlay"
set "OUTPUT_DIR=EXE_COMPILADO"
set "BUILD_DIR=.pyinstaller-build-onefile"
set "PYI_DIST=.pyinstaller-dist-onefile"
set "VENV_DIR=.build-venv"
set "SPEC_FILE=%APP_NAME%.spec"
set "PYTHON="

rem ================================================================
rem  Detectar Python sin obligar una version concreta.
rem ================================================================
where py >nul 2>&1
if not errorlevel 1 (
    py -3.13 --version >nul 2>&1 && set "PYTHON=py -3.13"
    if not defined PYTHON py -3.12 --version >nul 2>&1 && set "PYTHON=py -3.12"
    if not defined PYTHON py -3.11 --version >nul 2>&1 && set "PYTHON=py -3.11"
    if not defined PYTHON py -3 --version >nul 2>&1 && set "PYTHON=py -3"
)

if not defined PYTHON (
    where python >nul 2>&1
    if not errorlevel 1 set "PYTHON=python"
)

if not defined PYTHON (
    echo.
    echo [ERROR] No se encontro Python.
    echo Instala Python desde python.org y activa "Add Python to PATH".
    goto :error
)

echo.
echo Python detectado:
%PYTHON% --version
if errorlevel 1 goto :error

rem ================================================================
rem  Validar estructura y recursos editables.
rem ================================================================
for %%F in (main.py shortcut.py shortcut_dialog.py single_instance.py requirements.txt icon.ico beep.wav config.yml stage_map.yml) do (
    if not exist "%%F" (
        echo.
        echo [ERROR] Falta el archivo obligatorio: %%F
        goto :error
    )
)

for %%F in (overlay\__init__.py overlay\app.py overlay\view.py overlay\settings.py overlay\lifecycle.py overlay\detection.py) do (
    if not exist "%%F" (
        echo.
        echo [ERROR] Falta el modulo: %%F
        goto :error
    )
)

if exist "overlay.py" (
    echo.
    echo [ERROR] Existe overlay.py junto con la carpeta overlay\.
    echo Elimina ese archivo para evitar el conflicto de imports.
    goto :error
)

if not exist "pacenotes\" (
    echo.
    echo [ERROR] Falta la carpeta pacenotes.
    goto :error
)

dir /b "pacenotes\*.yml" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] La carpeta pacenotes no contiene archivos .yml.
    echo Copia ahi tus notas reales antes de compilar.
    goto :error
)

if not exist "voices\" (
    echo.
    echo [ERROR] Falta la carpeta voices.
    goto :error
)

set "VOICE_FOUND="
for /d %%D in ("voices\*") do set "VOICE_FOUND=1"
if not defined VOICE_FOUND (
    echo.
    echo [ERROR] La carpeta voices no contiene ninguna carpeta de voz.
    echo Copia ahi tus voces reales antes de compilar.
    goto :error
)

rem ================================================================
rem  Entorno de compilacion aislado.
rem ================================================================
echo.
echo [1/4] Preparando entorno de compilacion...
if not exist "%VENV_DIR%\Scripts\python.exe" (
    %PYTHON% -m venv "%VENV_DIR%"
    if errorlevel 1 goto :error
)
set "BUILD_PY=%VENV_DIR%\Scripts\python.exe"

"%BUILD_PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :error

"%BUILD_PY%" -m pip install -r requirements.txt pyinstaller pillow
if errorlevel 1 goto :error

rem ================================================================
rem  Validacion previa.
rem ================================================================
echo.
echo [2/4] Validando codigo modular...
"%BUILD_PY%" -m compileall -q main.py shortcut.py shortcut_dialog.py single_instance.py overlay acrally.py editor.py handbrake.py sharedmemory.py util.py
if errorlevel 1 goto :error

"%BUILD_PY%" -c "from overlay import Overlay; assert Overlay.__module__ == 'overlay.app'; from single_instance import SingleInstance; print('Proyecto modular OK')"
if errorlevel 1 goto :error

rem ================================================================
rem  Limpiar solamente la compilacion ONEFILE anterior.
rem  No modifica la carpeta ProgramaPacenotesMod de ONEDIR.
rem ================================================================
echo.
echo [3/4] Limpiando compilacion ONEFILE anterior...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%PYI_DIST%" rmdir /s /q "%PYI_DIST%"
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
if exist "%SPEC_FILE%" del /q "%SPEC_FILE%"

rem ================================================================
rem  Compilar en modo ONEFILE.
rem
rem  PyInstaller empaqueta Python y sus dependencias dentro de un solo EXE.
rem  Al ejecutarlo, extraera temporalmente sus archivos internos.
rem ================================================================
echo.
echo [4/4] Compilando solamente %APP_NAME%.exe...
"%BUILD_PY%" -m PyInstaller ^
    --onefile ^
    --windowed ^
    --clean ^
    --noconfirm ^
    --name "%APP_NAME%" ^
    --icon "icon.ico" ^
    --add-data "icon.ico;." ^
    --add-data "beep.wav;." ^
    --hidden-import editor ^
    --hidden-import handbrake ^
    --hidden-import sharedmemory ^
    --hidden-import psutil ^
    --collect-all pygame ^
    --collect-all sounddevice ^
    --collect-submodules pycaw ^
    --collect-submodules comtypes ^
    --distpath "%PYI_DIST%" ^
    --workpath "%BUILD_DIR%" ^
    main.py
if errorlevel 1 goto :error

if not exist "%PYI_DIST%\%APP_NAME%.exe" (
    echo.
    echo [ERROR] PyInstaller termino, pero no se encontro el EXE.
    goto :error
)

mkdir "%OUTPUT_DIR%" >nul 2>&1
move /y "%PYI_DIST%\%APP_NAME%.exe" "%OUTPUT_DIR%\%APP_NAME%.exe" >nul
if errorlevel 1 goto :error

if not exist "%OUTPUT_DIR%\%APP_NAME%.exe" (
    echo.
    echo [ERROR] No se encontro el ejecutable final.
    goto :error
)

echo.
echo ================================================================
echo  COMPILACION ONEFILE TERMINADA
echo ================================================================
echo.
echo Ejecutable:
echo "%CD%\%OUTPUT_DIR%\%APP_NAME%.exe"
echo.
echo Se genero solamente el ejecutable. No se copiaron:
echo   - voices
echo   - pacenotes
echo   - config.yml
echo   - stage_map.yml
echo.
echo Copia este EXE a tu carpeta principal, donde ya existen esos recursos.
echo No ejecutes el EXE dentro de "%OUTPUT_DIR%" porque alli no encontrara
echo config.yml, stage_map.yml, voices ni pacenotes.
echo.
echo Nota: ONEFILE puede mostrar dos procesos mientras esta abierto,
echo extraer archivos temporales al iniciar y tardar mas en arrancar.
echo.
pause
exit /b 0

:error
echo.
echo ================================================================
echo  LA COMPILACION ONEFILE FALLO
echo ================================================================
echo Revisa el primer error mostrado arriba.
echo.
pause
exit /b 1
