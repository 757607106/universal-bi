@echo off
REM ========================================
REM Universal BI 一键部署脚本 (Windows)
REM ========================================
REM 功能：自动检查环境、安装依赖、配置服务
REM 使用：setup.bat [dev|docker]
REM ========================================

setlocal enabledelayedexpansion

REM 颜色输出（Windows 10+）
set "GREEN=[32m"
set "YELLOW=[33m"
set "RED=[31m"
set "BLUE=[34m"
set "NC=[0m"

REM 打印 Logo
echo.
echo  _   _       _                          _   ____ ___ 
echo ^| ^| ^| ^|_ __ ^(_^)_   _____ _ __ ___  __ _^| ^| ^| __ ^)_ _^|
echo ^| ^| ^| ^| '_ \^| \ \ / / _ \ '__/ __^|/ _` ^| ^| ^|  _ \^| ^| 
echo ^| ^|_^| ^| ^| ^| ^| ^|\ V /  __/ ^|  \__ \ ^(_^| ^| ^| ^| ^|_) ^| ^| 
echo  \___/^|_^| ^|_^|_^| \_/ \___^|_^|  ^|___/\__,_^|_^| ^|____/_^|
echo.
echo      AI 驱动的自然语言数据分析平台
echo.

REM 获取部署模式
set MODE=%1
if "%MODE%"=="" set MODE=dev

if "%MODE%"=="dev" (
    call :setup_dev
) else if "%MODE%"=="docker" (
    call :setup_docker
) else (
    echo %RED%[ERROR]%NC% 无效的部署模式: %MODE%
    echo 使用方法: setup.bat [dev^|docker]
    echo   dev    - 开发模式（本地安装依赖）
    echo   docker - Docker 模式（容器化部署）
    exit /b 1
)

echo.
echo %GREEN%[SUCCESS]%NC% 部署完成！
exit /b 0

REM ========================================
REM 开发模式部署
REM ========================================
:setup_dev
echo %BLUE%[INFO]%NC% ========== 开发模式部署 ==========

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%NC% Python 未安装，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version') do echo %GREEN%[SUCCESS]%NC% Python 已安装: %%i
)

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%NC% Node.js 未安装，请先安装 Node.js 16+
    echo 下载地址: https://nodejs.org/
    exit /b 1
) else (
    for /f %%i in ('node --version') do echo %GREEN%[SUCCESS]%NC% Node.js 已安装: %%i
)

REM 配置环境变量
if not exist .env (
    echo %BLUE%[INFO]%NC% 创建 .env 配置文件...
    copy .env.example .env
    echo %GREEN%[SUCCESS]%NC% .env 文件已创建
    echo.
    echo %YELLOW%[WARNING]%NC% 重要：请编辑 .env 文件，配置以下必填项：
    echo   1. DASHSCOPE_API_KEY (通义千问 API Key)
    echo   2. 数据库连接信息（如需修改）
    echo.
    pause
    notepad .env
) else (
    echo %BLUE%[INFO]%NC% .env 文件已存在，跳过创建
)

REM 安装后端依赖
echo %BLUE%[INFO]%NC% 安装后端 Python 依赖...
cd backend
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
cd ..
echo %GREEN%[SUCCESS]%NC% 后端依赖安装完成

REM 安装前端依赖
echo %BLUE%[INFO]%NC% 安装前端 Node.js 依赖...
cd frontend
call npm install --registry=https://registry.npmmirror.com
cd ..
echo %GREEN%[SUCCESS]%NC% 前端依赖安装完成

REM 创建启动脚本
echo @echo off > start_dev.bat
echo echo 启动 Universal BI 开发服务... >> start_dev.bat
echo. >> start_dev.bat
echo REM 启动后端 >> start_dev.bat
echo cd backend >> start_dev.bat
echo call venv\Scripts\activate.bat >> start_dev.bat
echo start "Universal BI Backend" cmd /k "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" >> start_dev.bat
echo cd .. >> start_dev.bat
echo. >> start_dev.bat
echo REM 启动前端 >> start_dev.bat
echo cd frontend >> start_dev.bat
echo start "Universal BI Frontend" cmd /k "npm run dev" >> start_dev.bat
echo cd .. >> start_dev.bat
echo. >> start_dev.bat
echo echo 后端服务运行在: http://localhost:8000 >> start_dev.bat
echo echo 前端服务运行在: http://localhost:3000 >> start_dev.bat
echo echo API 文档: http://localhost:8000/docs >> start_dev.bat
echo pause >> start_dev.bat

echo.
echo %GREEN%[SUCCESS]%NC% ========== 开发环境配置完成 ==========
echo.
echo %BLUE%[INFO]%NC% 启动开发服务:
echo   start_dev.bat
echo.
echo %BLUE%[INFO]%NC% 或者分别启动:
echo   后端: cd backend ^&^& venv\Scripts\activate ^&^& uvicorn app.main:app --reload
echo   前端: cd frontend ^&^& npm run dev
echo.
exit /b 0

REM ========================================
REM Docker 模式部署
REM ========================================
:setup_docker
echo %BLUE%[INFO]%NC% ========== Docker 模式部署 ==========

REM 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%NC% Docker 未安装，请先安装 Docker Desktop
    echo 下载地址: https://www.docker.com/products/docker-desktop
    exit /b 1
) else (
    for /f "tokens=3" %%i in ('docker --version') do echo %GREEN%[SUCCESS]%NC% Docker 已安装: %%i
)

REM 检查 Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo %RED%[ERROR]%NC% Docker Compose 未安装
        exit /b 1
    ) else (
        set DOCKER_COMPOSE=docker compose
    )
) else (
    set DOCKER_COMPOSE=docker-compose
)

REM 配置环境变量
if not exist .env (
    echo %BLUE%[INFO]%NC% 创建 .env 配置文件...
    copy .env.example .env
    echo %GREEN%[SUCCESS]%NC% .env 文件已创建
    echo.
    echo %YELLOW%[WARNING]%NC% 重要：请编辑 .env 文件，配置 DASHSCOPE_API_KEY
    pause
    notepad .env
) else (
    echo %BLUE%[INFO]%NC% .env 文件已存在，跳过创建
)

REM 构建并启动服务
echo %BLUE%[INFO]%NC% 构建 Docker 镜像...
%DOCKER_COMPOSE% build

echo %BLUE%[INFO]%NC% 启动 Docker 服务...
%DOCKER_COMPOSE% up -d

REM 等待服务启动
echo %BLUE%[INFO]%NC% 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
%DOCKER_COMPOSE% ps

echo.
echo %GREEN%[SUCCESS]%NC% ========== Docker 部署完成 ==========
echo.
echo %BLUE%[INFO]%NC% 服务访问地址:
echo   前端: http://localhost:3000
echo   后端: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo.
echo %BLUE%[INFO]%NC% 常用命令:
echo   查看日志: %DOCKER_COMPOSE% logs -f
echo   重启服务: %DOCKER_COMPOSE% restart
echo   停止服务: %DOCKER_COMPOSE% down
echo   查看状态: %DOCKER_COMPOSE% ps
echo.
exit /b 0
