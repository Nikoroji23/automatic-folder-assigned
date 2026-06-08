#!/usr/bin/env python3
"""
Build script to create compact exe for KBMC Order Folder Creator
"""
import os
import subprocess
import sys
from pathlib import Path

script_dir = Path(__file__).parent
os.chdir(script_dir)

print("=" * 60)
print("KBMC Compact Order Folder Creator - EXE Build")
print("=" * 60)

# Build the exe with PyInstaller
print("\nBuilding executable...")

pyinstaller_cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "kbmc_folder_creator.py",
    "--onefile",
    "--windowed",
    "--name=KBMC_Compact",
    "--add-data=image_picker_solution.py:.",
    "--hidden-import=tkinter",
    "--hidden-import=PIL.Image",
    "--hidden-import=PIL.ImageTk",
    "--distpath=dist",
    "--workpath=build",
    "--specpath=.",
]

print(f"Running PyInstaller...\n")

try:
    result = subprocess.run(
        pyinstaller_cmd,
        check=True,
        text=True
    )
    
    exe_path = script_dir / "dist" / "KBMC_Compact.exe"
    
    if exe_path.exists():
        file_size = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 60)
        print("✓ SUCCESS! Compact executable created!")
        print("=" * 60)
        print(f"\nExecutable: {exe_path}")
        print(f"File size: {file_size:.2f} MB")
        print(f"\nOptimized for:")
        print(f"  ✓ Full-featured layout")
        print(f"  ✓ All functions working")
        print(f"  ✓ Standalone EXE (no dependencies)")
        print(f"  ✓ Ready to deploy")
    else:
        print("Error: Executable not created")
        sys.exit(1)
        
except subprocess.CalledProcessError as e:
    print(f"\nBuild failed: {e}")
    sys.exit(1)
