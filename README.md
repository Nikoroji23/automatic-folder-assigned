# Build EXE (Windows)

This project contains `kbmc_folder_creator.py` (Tkinter GUI) and `image_picker_solution.py`.

Quick build (Windows):

1. Open PowerShell in the project folder (where `kbmc_folder_creator.py` lives).
2. Run the provided helper batch file:

```powershell
.\build_exe.bat
```

What the script does:
- Upgrades pip and installs `Pillow` and `pyinstaller` from `requirements.txt`.
- Runs PyInstaller with `--onefile --windowed` to produce a GUI exe.
- The built EXE will be in `dist\kbmc_folder_creator.exe`.

Compact build (smaller EXE):

Run the compact build which uses `--strip` (and will use UPX if available on PATH):

```powershell
.\build_compact.bat
```

Automatic rebuild watcher:

You can watch for Python file changes and automatically rebuild the EXE using the included watcher:

```powershell
# install watchdog if needed
python -m pip install watchdog
# run the watcher (it will invoke build_exe.bat on changes)
python rebuild_on_change.py
```

Notes and troubleshooting:
- If PyInstaller fails to find imports, run PyInstaller manually adding `--hidden-import` flags for the missing modules.
- If the GUI window doesn't appear when running the EXE, run without `--windowed` to see console errors:

```powershell
python -m PyInstaller --onefile --clean --add-data "image_picker_solution.py;." kbmc_folder_creator.py
```

- If you want a smaller EXE, install UPX (https://upx.github.io/) and put `upx.exe` on PATH; the compact build will then compress the binary.
- Use a virtual environment for reproducible builds.

If you want, I can run the compact build or start the watcher for you now.
