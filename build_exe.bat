@echo off
cd /d "%~dp0"
echo Starting Build Process...
echo Cleaning previous builds...
rmdir /s /q build
rmdir /s /q dist

echo Building Executable...
venv\Scripts\pyinstaller --noconfirm --onefile --console --name "TeambitionHelper" --add-data "templates;templates" --add-data "image;image" --add-data "static;static" app.py

if %errorlevel% neq 0 (
    echo Build Failed!
    pause
    exit /b %errorlevel%
)

echo Packaging Distribution...
echo f | xcopy /y "config.json" "dist\config.json"
echo f | xcopy /y "start_server.bat" "dist\start_server.bat"

echo Build Complete!
echo ---------------------------------------------------
echo READY TO DEPLOY: The 'dist' folder contains everything.
echo ---------------------------------------------------
pause
