@echo off
setlocal
rem ============================================================
rem  Quiz Builder - share your local site quick tunnel pack
rem
rem   Run with an argument to pick the tunnel directly:
rem     run-tunnel.bat cf       Cloudflare Quick Tunnel
rem     run-tunnel.bat lhr      localhost.run    (OpenSSH, no install)
rem     run-tunnel.bat pinggy   pinggy.io        (OpenSSH, no install)
rem
rem   Run with no argument for an interactive menu.
rem ============================================================

cd /d "%~dp0"
set QUIZ_APP_HOST=127.0.0.1
set QUIZ_APP_PORT=8001
set URL=http://%QUIZ_APP_HOST%:%QUIZ_APP_PORT%

echo.
echo  ============================================================
echo   Quiz Builder - local site + quick share tunnel
echo  ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python 3 was not found. Install it from:
    echo          https://www.python.org/downloads/
    goto done_pause
)

echo  Local site : %URL%
start "Quiz Builder - %URL%" python testapp.py

where curl >nul 2>&1
if errorlevel 1 goto proceed

echo   Waiting for the local site to answer ...
set /a wait_n=0
set "HTTP_CODE=000"
:wait_loop
set /a wait_n+=1
curl -s -o NUL -m 2 -w "%%{http_code}" %URL%/ > "%TEMP%\quiz_http.txt" 2>nul
set /p HTTP_CODE=<"%TEMP%\quiz_http.txt"
if not "%HTTP_CODE%"=="000" (
    echo   [ok] Local site is up - HTTP %HTTP_CODE%
    goto proceed
)
if %wait_n% geq 10 goto server_wait_fail
ping -n 2 127.0.0.1 >nul
goto wait_loop

:server_wait_fail
echo.
echo  [ERROR] The local site did not answer at %URL%.
echo          Look at the new "Quiz Builder" window that just opened.
echo          Usually this means the address is already in use - close any
echo          older Quiz Builder windows, then run this file again.
echo.
goto done_pause

:proceed
if not "%~1"=="cf" goto not_cf
call :tunnel_cf
goto done_pause
:not_cf

if not "%~1"=="lhr" goto not_lhr
call :tunnel_lhr
goto done_pause
:not_lhr

if not "%~1"=="pinggy" goto not_pinggy
call :tunnel_pinggy
goto done_pause
:not_pinggy

:menu
echo.
echo  ============================================================
echo   Share your site with a Quick Tunnel:
echo     [1] Cloudflare Quick Tunnel   (cloudflared, install needed)
echo     [2] localhost.run             (OpenSSH ssh, no install)
echo     [3] pinggy.io                 (OpenSSH ssh, no install)
echo     [4] Exit
echo  ============================================================
set "CHOICE="
set /p CHOICE="  Enter your choice: "
if "%CHOICE%"=="4" goto:eof
if "%CHOICE%"=="3" call :tunnel_pinggy
if "%CHOICE%"=="2" call :tunnel_lhr
if "%CHOICE%"=="1" call :tunnel_cf
if not defined CHOICE goto:eof
echo.
echo  Tunnel ended. The local site is still running.
goto done_pause

:tunnel_cf
where cloudflared >nul 2>&1
if errorlevel 1 (
    echo  [skip] cloudflared is not installed.
    echo         Install it with:   winget install cloudflared
    echo         Or download:      https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
    goto:eof
)
echo.
echo  [cloudflared] Quick Tunnel...
echo   Your public URL appears below (look for "trycloudflare.com").
echo   Press Ctrl+C to stop it.
cmd /c "cloudflared tunnel --url %URL%"
goto:eof

:tunnel_lhr
where ssh >nul 2>&1
if errorlevel 1 (
    echo  [skip] OpenSSH client ssh was not found, enable it for free:
    echo         Settings - Apps - Optional features - Add OpenSSH Client
    goto:eof
)
echo.
echo  [localhost.run] Quick Tunnel (no install)...
echo   Your public URL appears below (look for "localhost.run" / "lhr.life").
echo   Press Ctrl+C to stop it.
cmd /c "ssh -o StrictHostKeyChecking=accept-new -o ExitOnForwardFailure=yes -o ServerAliveInterval=60 -R 80:localhost:8001 nokey@localhost.run"
goto:eof

:tunnel_pinggy
where ssh >nul 2>&1
if errorlevel 1 (
    echo  [skip] OpenSSH client ssh was not found, enable it for free:
    echo         Settings - Apps - Optional features - Add OpenSSH Client
    goto:eof
)
echo.
echo  [pinggy.io] Quick Tunnel (no install)...
echo   Your public URL appears below (look for "pinggy.link").
echo   Press Ctrl+C to stop it.
cmd /c "ssh -p 443 -o StrictHostKeyChecking=accept-new -o ExitOnForwardFailure=yes -R0:localhost:8001 a.pinggy.io"
goto:eof

:done_pause
if not defined QUIZ_NO_PAUSE pause
exit /b 0