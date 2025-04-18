@echo off
setlocal EnableDelayedExpansion

:: ────── CONFIG ────────────────────────────────────────────────
rem 1) Root folder (use first argument, otherwise current dir)
set "folderPath=%~1"
if "%folderPath%"=="" set "folderPath=."

rem 2) Output file
set "outputFile=contents.txt"

rem 3) Space‑separated list of directory names to ignore
rem    (match is case‑insensitive, on the directory’s *last* segment)
set "ignoreDirs=__pycache__ .venv logs node_modules"
:: ──────────────────────────────────────────────────────────────

> "%outputFile%" echo Files and folders in "%folderPath%":
call :listFiles "%folderPath%"
echo(
echo Report written to "%outputFile%"
goto :eof


:listFiles
rem ── list regular files in the current folder ────────────────
for /f "delims=" %%a in ('dir /b /a-d "%~1"') do (
    echo %~1\%%a>>"%outputFile%"
)

rem ── loop through sub‑directories ────────────────────────────
for /d %%b in ("%~1\*") do (

    set "dirName=%%~nxb"

    rem ========== is this folder on the ignore list? ==========
    set "skipFolder="
    for %%i in (!ignoreDirs!) do (
        if /I "%%i"=="!dirName!" set "skipFolder=1"
    )

    if defined skipFolder (
        rem ---- write notice (optional) and continue ----
        echo Skipping folder %%b>>"%outputFile%"
    ) else (
        echo(>>"%outputFile%"
        echo Folder: %%b>>"%outputFile%"
        call :listFiles "%%b"
    )
)
goto :eof
