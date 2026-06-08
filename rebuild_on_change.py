"""
Rebuild watcher: watches for changes to .py files in the project and runs the build script.
Usage:
    python rebuild_on_change.py

Requires: watchdog (install with `pip install watchdog`)
"""
import os
import sys
import time
import subprocess
from threading import Timer

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except Exception:
    print("Please install watchdog: python -m pip install watchdog")
    sys.exit(1)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_CMD = [sys.executable, os.path.join(PROJECT_DIR, 'build_exe.bat')] if sys.platform.startswith('win') else [sys.executable, '-m', 'PyInstaller', '--onefile', 'kbmc_folder_creator.py']

# Debounce timer so multiple rapid file saves only cause one build
_debounce_timer = None

class ChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.py'):
            return
        schedule_build()


def schedule_build(delay=1.0):
    global _debounce_timer
    if _debounce_timer is not None:
        _debounce_timer.cancel()
    _debounce_timer = Timer(delay, run_build)
    _debounce_timer.start()


def run_build():
    print('\nDetected change. Running build script...')
    try:
        # On Windows we can call the batch file directly
        if sys.platform.startswith('win'):
            subprocess.run([os.path.join(PROJECT_DIR, 'build_exe.bat')], cwd=PROJECT_DIR, check=False, shell=True)
        else:
            subprocess.run(BUILD_CMD, cwd=PROJECT_DIR, check=False)
    except Exception as e:
        print('Build failed to start:', e)


def main():
    print('Watching for Python changes in', PROJECT_DIR)
    observer = Observer()
    handler = ChangeHandler()
    observer.schedule(handler, PROJECT_DIR, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()
