@echo off
REM Compact build: attempts to reduce EXE size by stripping and using UPX if available
setlocal
python -m pip install --upgrade pip
python -m pip install -r "%~dp0requirements.txt"






pauseecho Compact build finished. See the dist folder.python -m PyInstaller --noconfirm --onefile --windowed --clean --strip --add-data "image_picker_solution.py;." --hidden-import=tkinter --hidden-import=PIL.Image --hidden-import=PIL.ImageTk "kbmc_folder_creator.py"REM Try to use UPX if available in PATH; PyInstaller will use it if found.necho Running PyInstaller (compact build)...