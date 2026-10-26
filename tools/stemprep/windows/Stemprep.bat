@echo off
setlocal
title Stemprep - Spotify to Mixxx stems
set "VENV=%LOCALAPPDATA%\stemprep\venv"
set "STEMPREP=%VENV%\Scripts\stemprep.exe"
if not exist "%STEMPREP%" (
  echo Stemprep is not installed yet. Run "Install Stemprep.bat" first.
  pause
  exit /b 1
)

rem Files or folders dragged onto the shortcut are processed directly.
if not "%~1"=="" (
  "%STEMPREP%" %*
  goto done
)

:menu
echo.
echo  1  Sync my playlists (download new tracks, make stems)
echo  2  Add a Spotify playlist to sync
echo  3  Show my playlists
echo  4  Stop syncing a playlist (files are kept)
echo  5  Process one link, folder or file
echo  6  Redo bars/phrases/drops after a Stemprep update (fast)
echo  7  High quality stems for all my tracks (slow: leave it running overnight)
echo.
set "CHOICE="
set /p "CHOICE=Choose 1-7 and press Enter: "

if "%CHOICE%"=="1" (
  "%STEMPREP%" sync
  goto done
)
if "%CHOICE%"=="2" (
  echo.
  echo  Paste the playlist link. ^(Right-click pastes in this window.^)
  set /p "LINK=> "
  echo  Folder name, or Enter to use the playlist name:
  set /p "FOLDER=> "
  goto add
)
if "%CHOICE%"=="3" (
  "%STEMPREP%" list
  goto menu
)
if "%CHOICE%"=="4" (
  "%STEMPREP%" list
  echo.
  echo  Name or link of the playlist to stop syncing:
  set /p "NAME=> "
  goto remove
)
if "%CHOICE%"=="5" (
  echo.
  echo  Paste a Spotify link, or a folder/file path:
  set /p "INPUT=> "
  goto one
)
if "%CHOICE%"=="6" (
  "%STEMPREP%" reanalyze
  goto done
)
if "%CHOICE%"=="7" (
  echo.
  echo  Making high quality stems. You can close this window any time;
  echo  next time it continues where it stopped. Mixxx uses the new stems
  echo  the next time a track is loaded.
  "%STEMPREP%" hq
  goto done
)
exit /b 0

:add
if "%LINK%"=="" goto menu
if "%FOLDER%"=="" (
  "%STEMPREP%" add "%LINK%"
) else (
  "%STEMPREP%" add "%LINK%" --folder "%FOLDER%"
)
goto done

:remove
if "%NAME%"=="" goto menu
"%STEMPREP%" remove "%NAME%"
goto menu

:one
if "%INPUT%"=="" goto menu
"%STEMPREP%" "%INPUT%"

:done
echo.
echo Finished. Stems are in %USERPROFILE%\Music\stemprep\Stems
pause
