@echo off
setlocal
title Stemprep - Spotify to Mixxx stems
set "VENV=%LOCALAPPDATA%\stemprep\venv"
if not exist "%VENV%\Scripts\stemprep.exe" (
  echo Stemprep is not installed yet. Run "Install Stemprep.bat" first.
  pause
  exit /b 1
)

rem Files or folders dragged onto the shortcut are processed directly.
if not "%~1"=="" (
  "%VENV%\Scripts\stemprep.exe" %*
  goto done
)

echo.
echo  Paste a Spotify playlist/album/track link, or a folder/file path,
echo  then press Enter. (Right-click pastes in this window.)
echo.
set /p "INPUT=> "
if "%INPUT%"=="" exit /b 0
"%VENV%\Scripts\stemprep.exe" "%INPUT%"

:done
echo.
echo Finished. Stems are in %USERPROFILE%\Music\stemprep\Stems
pause
