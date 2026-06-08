@echo off
REM Compact version build - optimized for small window (600x650)
REM This builds a smaller, more efficient EXE using PyInstaller
setlocal

echo Building compact KBMC app...
echo.

REM Ensure dependencies are installed
python -m pip install --upgrade pip -q
python -m pip install -r "%~dp0requirements.txt" -q

REM Build with PyInstaller - compact settings
echo Running PyInstaller (compact build)...
python -m PyInstaller --noconfirm --onefile --windowed --clean ^
  --strip ^
  --add-data "image_picker_solution.py;." ^
  --hidden-import=tkinter ^
  --hidden-import=PIL.Image ^
  --hidden-import=PIL.ImageTk ^
  "kbmc_folder_creator.py"

echo.
echo Compact build finished!
echo EXE location: .\dist\kbmc_folder_creator.exe
echo Window size: 600x650 pixels (compact, like a VS Code tab)
echo.
pause
