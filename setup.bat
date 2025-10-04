@echo off
echo =========================================
echo   Code Editor Pro - Setup Script (Windows)
echo =========================================
echo.

:: Check if Docker is installed
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker first.
    echo    Visit: https://docs.docker.com/get-docker/
    exit /b 1
)

:: Check if Docker Compose is installed
where docker-compose >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    echo    Visit: https://docs.docker.com/compose/install/
    exit /b 1
)

echo ✅ Docker is installed
echo ✅ Docker Compose is installed
echo.

:: Create directory structure
echo 📁 Creating directory structure...
if not exist static mkdir static
if not exist workspace mkdir workspace
echo ✅ Directories created
echo.

:: Build Docker image
echo 🔨 Building Docker image...
docker-compose build
if %errorlevel% neq 0 (
    echo ❌ Failed to build Docker image
    exit /b 1
)

echo ✅ Docker image built successfully
echo.
echo =========================================
echo   Setup Complete!
echo =========================================
echo.
echo To start the editor:
echo   docker-compose up -d
echo.
echo To view logs:
echo   docker-compose logs -f
echo.
echo To stop the editor:
echo   docker-compose down
echo.
echo Access the editor at: http://localhost:5000
echo Default login: demo / demo123
echo.
echo =========================================
pause
