@echo off
REM Build script: installs requirements and runs PyInstaller to make a single-file GUI exe
echo Installing/ensuring build dependencies...
python -m pip install --upgrade pip
python -m pip install -r "%~dp0requirements.txt"
echo Running PyInstaller to build one-file windowed exe...
pyinstaller --noconfirm --onefile --windowed --clean --add-data "image_picker_solution.py;." --hidden-import=tkinter --hidden-import=PIL.Image --hidden-import=PIL.ImageTk "%~dp0kbmc_folder_creator.py"
echo Build finished. The EXE will be in the "dist" folder.
pause
