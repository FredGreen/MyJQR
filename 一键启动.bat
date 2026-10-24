@echo off
title MyJQR 一键启动

REM ============================================================
REM  MyJQR 开机一键启动（对应 docs/本地运行手册.md 三·五 的 6 步）
REM  双击运行即可；已在运行的服务会自动跳过，可放心重复执行。
REM  注意：本文件为 GBK 编码 + CRLF 换行，请勿改存为 UTF-8。
REM ============================================================

set "ROOT=D:\workspace\pyworkspace\MyJQR"
set "PY=%ROOT%\.venv\Scripts\python.exe"
cd /d "%ROOT%"

echo ============================================================
echo   MyJQR 开机一键启动
echo ============================================================
echo.

REM ---------- ① Docker 引擎（就绪则直接跳过） ----------
docker info >nul 2>&1
if not errorlevel 1 goto docker_ok
echo [1/6] 正在启动 Docker Desktop，等待引擎就绪，最多 3 分钟...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
set /a Tries=0
:waitdocker
docker info >nul 2>&1
if not errorlevel 1 goto docker_ok
set /a Tries+=1
if %Tries% LSS 60 (
    ping -n 4 127.0.0.1 >nul
    goto waitdocker
)
echo.
echo [失败] Docker 引擎 3 分钟内未就绪。请手动打开 Docker Desktop，等它跑起来后重新双击本脚本。
pause
exit /b 1
:docker_ok
echo [1/6] Docker 已就绪

REM ---------- ② MySQL / Redis 容器 ----------
echo [2/6] 拉起 MySQL / Redis 容器...
docker compose up -d mysql redis
docker compose ps

REM ---------- ③ 后端 API - 端口 9000 ----------
netstat -ano | findstr ":9000 " | findstr "LISTENING" >nul
if not errorlevel 1 goto api_ok
echo [3/6] 已在新窗口启动后端 API
start "MyJQR-API-9000" cmd /k "cd /d %ROOT%\backend && %PY% -m uvicorn app.main:app --reload --port 9000"
goto api_done
:api_ok
echo [3/6] 后端 API 已在运行，跳过
:api_done

REM ---------- ④ ARQ worker - 真正调模型的进程 ----------
powershell -NoProfile -Command "if (Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object {$_.CommandLine -match 'arq app.tasks.worker'}) { exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 goto worker_ok
echo [4/6] 已在新窗口启动 ARQ worker
start "MyJQR-ARQ-worker" cmd /k "cd /d %ROOT%\backend && %PY% -X utf8 -m arq app.tasks.worker.WorkerSettings"
goto worker_done
:worker_ok
echo [4/6] ARQ worker 已在运行，跳过
:worker_done

REM ---------- ⑤ 前端两个 - 用户端 8080 / 管理后台 8081 ----------
netstat -ano | findstr ":8080 " | findstr "LISTENING" >nul
if not errorlevel 1 goto web_ok
echo [5/6] 已在新窗口启动用户端前端
start "MyJQR-Web-8080" cmd /k "cd /d %ROOT%\apps\web && npm run dev"
goto web_done
:web_ok
echo [5/6] 用户端前端已在运行，跳过
:web_done

netstat -ano | findstr ":8081 " | findstr "LISTENING" >nul
if not errorlevel 1 goto admin_ok
echo       已在新窗口启动管理后台前端
start "MyJQR-Admin-8081" cmd /k "cd /d %ROOT%\apps\admin && npm run dev"
goto admin_done
:admin_ok
echo       管理后台前端已在运行，跳过
:admin_done

REM ---------- ⑥ ngrok 公网访问 - 可选 ----------
set "DO_NGROK="
set /p DO_NGROK=[6/6] 是否启动 ngrok 公网访问？输入 y 后回车=启动，直接回车=跳过：
if /i "%DO_NGROK%"=="y" goto ngrok_yes
echo       跳过 ngrok。以后需要时在任意 PowerShell 里执行：ngrok start myjqr
goto ngrok_done
:ngrok_yes
start "MyJQR-ngrok" cmd /k "ngrok start myjqr"
echo       已在新窗口启动 ngrok，公网域名固定不变
:ngrok_done

REM ---------- 等待 API 就绪 ----------
echo.
echo 等待 API 就绪...
set /a Tries=0
:waitapi
curl -s -o nul -m 2 http://127.0.0.1:9000/health
if not errorlevel 1 goto api_ready
set /a Tries+=1
if %Tries% LSS 30 (
    ping -n 2 127.0.0.1 >nul
    goto waitapi
)
echo [注意] API 30 秒内未就绪——请在标题为 MyJQR-API 的窗口里查看报错。
goto summary
:api_ready
echo API 已就绪。
ping -n 4 127.0.0.1 >nul
start "" http://localhost:8080

:summary
echo.
echo ============================================================
echo   启动完成！地址：
echo   用户端     http://localhost:8080
echo   管理后台   http://localhost:8081/admin/    账号 admin / admin123456
echo   公网       https://cabana-unsubtly-monkhood.ngrok-free.dev   [需启动 ngrok]
echo.
echo   各服务窗口保持最小化即可，关闭窗口=停止对应服务；
echo   本窗口可以直接关闭。
echo ============================================================
pause
