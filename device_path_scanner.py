"""
device_path_scanner.py
======================
Detects and exposes image folders from ALL connected device types:
  - Local drives (Windows / macOS / Linux)
  - USB Android devices via MTP (Windows Shell COM, fallback ADB)
  - USB iOS devices (ifuse / idevice tools, gvfs)
  - Network / cloud mount points
  - Linux/macOS GVFS mounts

Usage:
    from device_path_scanner import DeviceScanner, browse_device_folder
    scanner = DeviceScanner()
    devices = scanner.scan_all()          # list of DeviceEntry
    path = browse_device_folder(parent)   # opens picker dialog, returns path string or ""
"""

import os
import sys
import subprocess
import platform
import string
import shutil
import tempfile
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Callable
import tkinter as tk
from tkinter import ttk, messagebox

# ──────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────

@dataclass
class DeviceEntry:
    label: str                   # display name, e.g. "Samsung Galaxy S21"
    path: str                    # best accessible path (may be temp for MTP)
    device_type: str             # "local" | "android_mtp" | "android_adb" | "ios" | "gvfs" | "network"
    is_mtp: bool = False         # True if path is a temp-copied staging area
    mtp_shell_path: str = ""     # original Windows shell path if MTP
    icon: str = "📁"
    available: bool = True
    sub_folders: List[str] = field(default_factory=list)

    def __str__(self):
        return f"{self.icon} {self.label}  [{self.device_type}]  →  {self.path}"


# ──────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────

def _run(cmd: list, timeout=8) -> str:
    """Run a subprocess, return stdout or '' on failure."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def normalize_path(p: str) -> str:
    """Normalise slashes for current OS."""
    if not p:
        return p
    if platform.system() == "Windows":
        return str(Path(p))
    return p.replace("\\", "/")


def safe_path_join(*parts) -> str:
    """Join path parts safely across OS."""
    return normalize_path(os.path.join(*[str(p) for p in parts]))


# ──────────────────────────────────────────────
# Platform-specific scanners
# ──────────────────────────────────────────────

class _WindowsScanner:
    """Scan Windows: local drives + MTP devices via Shell COM + WMI."""

    def scan(self) -> List[DeviceEntry]:
        entries = []
        entries += self._scan_local_drives()
        entries += self._scan_mtp_via_shell()
        entries += self._scan_via_wmi()
        return entries

    # ---- local drives ----
    def _scan_local_drives(self) -> List[DeviceEntry]:
        entries = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    label = self._get_drive_label(drive)
                    dtype = self._classify_drive(drive)
                    icon = {"removable": "💾", "cdrom": "💿", "remote": "🌐"}.get(dtype, "💽")
                    entries.append(DeviceEntry(
                        label=label or f"Drive {letter}:",
                        path=drive,
                        device_type="local",
                        icon=icon,
                    ))
                except Exception:
                    pass
        return entries

    def _get_drive_label(self, drive: str) -> str:
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(256)
            ctypes.windll.kernel32.GetVolumeInformationW(
                drive, buf, 256, None, None, None, None, 0)
            return buf.value or drive.rstrip("\\")
        except Exception:
            return drive.rstrip("\\")

    def _classify_drive(self, drive: str) -> str:
        try:
            import ctypes
            t = ctypes.windll.kernel32.GetDriveTypeW(drive)
            return {2: "removable", 3: "fixed", 4: "remote", 5: "cdrom", 6: "ramdisk"}.get(t, "fixed")
        except Exception:
            return "fixed"

    # ---- MTP via Windows Shell COM (win32com) ----
    def _scan_mtp_via_shell(self) -> List[DeviceEntry]:
        entries = []
        try:
            import win32com.client   # pywin32
            shell = win32com.client.Dispatch("Shell.Application")
            # Desktop namespace
            desktop = shell.Namespace(0)
            computer = None
            for item in desktop.Items():
                if item.Name in ("This PC", "Computer", "My Computer"):
                    computer = item
                    break
            if computer is None:
                return entries

            folder = shell.Namespace(computer.Path)
            if folder is None:
                return entries

            for item in folder.Items():
                name = item.Name
                path = item.Path
                # MTP devices have paths like "::{GUID}" or start with \\
                if path and (path.startswith("::") or "MTP" in str(item.Type).upper()
                             or self._looks_like_phone(name)):
                    entry = DeviceEntry(
                        label=name,
                        path="",          # will be resolved on demand
                        device_type="android_mtp",
                        is_mtp=True,
                        mtp_shell_path=path,
                        icon="📱",
                    )
                    # try to find DCIM or Pictures sub-folder
                    sub = self._find_mtp_image_folder(shell, item)
                    if sub:
                        entry.path = sub
                        entry.sub_folders = [sub]
                    entries.append(entry)
        except ImportError:
            pass  # pywin32 not installed — fall through to ADB
        except Exception:
            pass
        return entries

    def _looks_like_phone(self, name: str) -> bool:
        keywords = ["phone", "tablet", "android", "iphone", "ipad", "galaxy",
                    "pixel", "oneplus", "xiaomi", "huawei", "sony", "nokia",
                    "motorola", "lg ", "htc", "oppo", "vivo", "realme"]
        return any(k in name.lower() for k in keywords)

    def _find_mtp_image_folder(self, shell, device_item) -> str:
        """
        Walk MTP device to find DCIM/Camera or Pictures.
        Returns a temp directory path with copied images, or "".
        """
        try:
            dev_folder = shell.Namespace(device_item.Path)
            if dev_folder is None:
                return ""
            for storage in dev_folder.Items():
                storage_folder = shell.Namespace(storage.Path)
                if storage_folder is None:
                    continue
                for top in storage_folder.Items():
                    if top.Name.upper() in ("DCIM", "PICTURES", "PHOTOS"):
                        # Try to resolve to a real path via CopyHere into temp
                        target = self._mtp_stage_folder(shell, top)
                        if target:
                            return target
        except Exception:
            pass
        return ""

    def _mtp_stage_folder(self, shell, mtp_item) -> str:
        """
        Stage MTP folder into a local temp directory so Python can enumerate it.
        Returns the temp path or "".
        """
        try:
            tmp = tempfile.mkdtemp(prefix="kbmc_mtp_")
            dest_folder = shell.Namespace(tmp)
            if dest_folder is None:
                return tmp          # return empty tmp so caller can try again
            dest_folder.CopyHere(mtp_item, 4 | 16)  # 4=no progress, 16=no errors dialog
            return tmp
        except Exception:
            return ""

    # ---- WMI fallback ----
    def _scan_via_wmi(self) -> List[DeviceEntry]:
        entries = []
        try:
            import wmi
            c = wmi.WMI()
            for disk in c.Win32_DiskDrive():
                if "USB" in (disk.InterfaceType or ""):
                    for part in disk.associators("Win32_DiskDriveToDiskPartition"):
                        for logical in part.associators("Win32_LogicalDiskToPartition"):
                            path = logical.DeviceID + "\\"
                            if os.path.exists(path):
                                entries.append(DeviceEntry(
                                    label=disk.Caption or path,
                                    path=path,
                                    device_type="android_mtp",
                                    icon="📱",
                                ))
        except Exception:
            pass
        return entries


class _AndroidADBScanner:
    """Pull image list via ADB (works when USB debugging is on)."""

    ADB_IMAGE_PATHS = [
        "/sdcard/DCIM/Camera",
        "/sdcard/Pictures",
        "/sdcard/DCIM",
        "/storage/emulated/0/DCIM/Camera",
        "/storage/emulated/0/Pictures",
    ]

    def _adb_available(self) -> bool:
        return shutil.which("adb") is not None

    def scan(self) -> List[DeviceEntry]:
        if not self._adb_available():
            return []
        devices = self._list_devices()
        entries = []
        for serial in devices:
            label = self._get_device_name(serial)
            path = self._find_best_path(serial)
            if path:
                entries.append(DeviceEntry(
                    label=f"{label} (ADB)",
                    path=path,
                    device_type="android_adb",
                    is_mtp=False,
                    icon="🤖",
                ))
        return entries

    def _list_devices(self) -> List[str]:
        out = _run(["adb", "devices"])
        serials = []
        for line in out.splitlines()[1:]:
            if "\tdevice" in line:
                serials.append(line.split("\t")[0].strip())
        return serials

    def _get_device_name(self, serial: str) -> str:
        model = _run(["adb", "-s", serial, "shell", "getprop", "ro.product.model"])
        return model or serial

    def _find_best_path(self, serial: str) -> str:
        """
        Return a temp directory populated by 'adb pull' of the best image folder.
        This is slow for large libraries — caller should stage asynchronously.
        Returns the ADB path string (not pulled yet) so UI can pull on demand.
        """
        for p in self.ADB_IMAGE_PATHS:
            result = _run(["adb", "-s", serial, "shell", "ls", p])
            if result and "No such file" not in result:
                return f"adb://{serial}{p}"   # virtual path — UI must handle pull
        return ""

    def pull_to_temp(self, adb_virtual_path: str, progress_cb: Optional[Callable] = None) -> str:
        """
        Pull adb://SERIAL/path into a temp folder. Returns local temp path.
        """
        # parse adb://serial/path
        without_scheme = adb_virtual_path[len("adb://"):]
        slash = without_scheme.index("/")
        serial = without_scheme[:slash]
        remote_path = without_scheme[slash:]

        tmp = tempfile.mkdtemp(prefix="kbmc_adb_")
        cmd = ["adb", "-s", serial, "pull", remote_path, tmp]
        try:
            subprocess.run(cmd, timeout=120)
        except Exception:
            pass
        return tmp


class _iOSScanner:
    """Detect iOS devices via ifuse or idevice tools."""

    def scan(self) -> List[DeviceEntry]:
        entries = []
        entries += self._scan_ifuse()
        entries += self._scan_gvfs_ios()
        return entries

    def _scan_ifuse(self) -> List[DeviceEntry]:
        if not shutil.which("idevice_id"):
            return []
        out = _run(["idevice_id", "-l"])
        entries = []
        for udid in out.splitlines():
            udid = udid.strip()
            if not udid:
                continue
            name = _run(["ideviceinfo", "-u", udid, "-k", "DeviceName"]) or "iPhone/iPad"
            mount = self._mount_ifuse(udid)
            if mount:
                entries.append(DeviceEntry(
                    label=f"{name} (ifuse)",
                    path=mount,
                    device_type="ios",
                    icon="🍎",
                ))
        return entries

    def _mount_ifuse(self, udid: str) -> str:
        tmp = tempfile.mkdtemp(prefix="kbmc_ios_")
        try:
            subprocess.run(["ifuse", "--udid", udid, tmp], timeout=15)
            dcim = os.path.join(tmp, "DCIM")
            if os.path.exists(dcim):
                return dcim
            return tmp
        except Exception:
            return ""

    def _scan_gvfs_ios(self) -> List[DeviceEntry]:
        """macOS/Linux GVFS AFC mount."""
        bases = [
            Path.home() / ".gvfs",
            Path("/run/user") / str(os.getuid()) / "gvfs" if platform.system() == "Linux" else Path("/nonexistent"),
        ]
        entries = []
        for base in bases:
            if base.exists():
                for sub in base.iterdir():
                    if "afc" in sub.name.lower() or "iphone" in sub.name.lower() or "ipad" in sub.name.lower():
                        dcim = sub / "DCIM"
                        entries.append(DeviceEntry(
                            label=sub.name,
                            path=str(dcim) if dcim.exists() else str(sub),
                            device_type="ios",
                            icon="🍎",
                        ))
        return entries


class _LinuxGVFSScanner:
    """Scan Linux GVFS mounts for Android MTP and removable media."""

    def scan(self) -> List[DeviceEntry]:
        entries = []
        uid = str(os.getuid())
        gvfs_roots = [
            Path(f"/run/user/{uid}/gvfs"),
            Path.home() / ".gvfs",
        ]
        for root in gvfs_roots:
            if root.exists():
                for dev in root.iterdir():
                    name = dev.name
                    icon = "📱" if "mtp" in name.lower() or "android" in name.lower() else "💾"
                    # Find best image sub-path
                    path = self._best_image_path(dev)
                    entries.append(DeviceEntry(
                        label=name,
                        path=path,
                        device_type="gvfs",
                        icon=icon,
                    ))
        # also check /media/<user>
        media_user = Path(f"/media/{os.environ.get('USER', 'user')}")
        if media_user.exists():
            for dev in media_user.iterdir():
                entries.append(DeviceEntry(
                    label=dev.name,
                    path=str(dev),
                    device_type="local",
                    icon="💾",
                ))
        return entries

    def _best_image_path(self, dev_path: Path) -> str:
        candidates = ["DCIM/Camera", "DCIM", "Pictures", "Photos"]
        for c in candidates:
            p = dev_path / c
            if p.exists():
                return str(p)
        return str(dev_path)


class _MacOSScanner:
    """Scan macOS: Volumes + iOS AFC + Android GVFS."""

    def scan(self) -> List[DeviceEntry]:
        entries = []
        # /Volumes
        volumes = Path("/Volumes")
        if volumes.exists():
            for vol in volumes.iterdir():
                if vol.name == "Macintosh HD":
                    continue
                entries.append(DeviceEntry(
                    label=vol.name,
                    path=str(vol),
                    device_type="local",
                    icon="💾",
                ))
        # GVFS
        entries += _LinuxGVFSScanner().scan()
        return entries


# ──────────────────────────────────────────────
# Main scanner facade
# ──────────────────────────────────────────────

class DeviceScanner:
    """
    Unified scanner for all device types. Call scan_all() to get DeviceEntry list.
    """

    def scan_all(self) -> List[DeviceEntry]:
        entries: List[DeviceEntry] = []
        os_name = platform.system()

        if os_name == "Windows":
            entries += _WindowsScanner().scan()
            entries += _AndroidADBScanner().scan()
            entries += _iOSScanner().scan()
        elif os_name == "Darwin":
            entries += _MacOSScanner().scan()
            entries += _AndroidADBScanner().scan()
            entries += _iOSScanner().scan()
        else:  # Linux
            entries += _LinuxGVFSScanner().scan()
            entries += _AndroidADBScanner().scan()
            entries += _iOSScanner().scan()

        # De-duplicate by path
        seen = set()
        unique = []
        for e in entries:
            if e.path not in seen:
                seen.add(e.path)
                unique.append(e)

        return unique

    def is_adb_path(self, path: str) -> bool:
        return path.startswith("adb://")

    def resolve_adb_path(self, path: str, progress_cb=None) -> str:
        """Pull ADB path to temp dir, return local path."""
        return _AndroidADBScanner().pull_to_temp(path, progress_cb)


# ──────────────────────────────────────────────
# Device Browser Dialog
# ──────────────────────────────────────────────

PRIMARY   = "#C41E3A"
ACCENT    = "#E74C3C"
BG        = "#F5F5F5"
CARD      = "#FFFFFF"
TEXT      = "#222222"
LIGHT_BORDER = "#E0E0E0"


class DeviceBrowserDialog:
    """
    A dialog that lists all detected devices/folders and lets the user
    either pick one from the list OR type/paste a custom path.
    Returns the selected path string (normalised) or "" if cancelled.
    """

    def __init__(self, parent: tk.Widget, title="Select Images Folder"):
        self.parent = parent
        self.title_text = title
        self.result_path: str = ""
        self._scanner = DeviceScanner()
        self._devices: List[DeviceEntry] = []
        self._adb_scanner = _AndroidADBScanner()
        self._build()

    def _build(self):
        self.dlg = tk.Toplevel(self.parent)
        self.dlg.title(self.title_text)
        self.dlg.geometry("640x540")
        self.dlg.resizable(True, True)
        self.dlg.transient(self.parent)
        self.dlg.grab_set()
        self.dlg.configure(bg=BG)
        self._center()

        # ── Header ──
        hdr = tk.Frame(self.dlg, bg=PRIMARY, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📱  Device & Folder Browser",
                 bg=PRIMARY, fg="white", font=("Segoe UI", 11, "bold"),
                 padx=12, pady=10).pack(anchor="w")

        # ── Info strip ──
        tk.Label(self.dlg,
                 text="Detected devices and drives are listed below. "
                      "Select one or paste a custom path.",
                 bg=BG, fg="#555", font=("Segoe UI", 8),
                 padx=10, pady=4, justify="left").pack(fill="x")

        # ── Refresh button ──
        top_bar = tk.Frame(self.dlg, bg=BG)
        top_bar.pack(fill="x", padx=10, pady=(0, 4))
        self._status_lbl = tk.Label(top_bar, text="Scanning…", bg=BG, fg="#888",
                                    font=("Segoe UI", 8))
        self._status_lbl.pack(side="left")
        tk.Button(top_bar, text="⟳ Refresh", command=self._do_scan,
                  bg=ACCENT, fg="white", font=("Segoe UI", 8, "bold"),
                  relief="flat", padx=8, pady=3, cursor="hand2").pack(side="right")

        # ── Device list (Treeview) ──
        list_frame = tk.Frame(self.dlg, bg=CARD, highlightthickness=1,
                              highlightbackground=LIGHT_BORDER)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        cols = ("icon_label", "type", "path")
        self._tree = ttk.Treeview(list_frame, columns=cols, show="headings",
                                  selectmode="browse", height=14)
        self._tree.heading("icon_label", text="Device / Drive")
        self._tree.heading("type",       text="Type")
        self._tree.heading("path",       text="Path")
        self._tree.column("icon_label",  anchor="w", width=220)
        self._tree.column("type",        anchor="center", width=110)
        self._tree.column("path",        anchor="w", width=260)

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        self._tree.tag_configure("phone",   foreground="#1565C0")
        self._tree.tag_configure("ios",     foreground="#6A1B9A")
        self._tree.tag_configure("adb",     foreground="#2E7D32")
        self._tree.tag_configure("local",   foreground="#333333")
        self._tree.tag_configure("network", foreground="#E65100")

        self._tree.bind("<Double-1>", lambda e: self._select_item())
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # ── Custom path entry ──
        custom_frame = tk.Frame(self.dlg, bg=CARD, highlightthickness=1,
                                highlightbackground=LIGHT_BORDER)
        custom_frame.pack(fill="x", padx=10, pady=(0, 6))

        tk.Label(custom_frame, text="Custom path (paste or type):",
                 bg=CARD, fg=PRIMARY, font=("Segoe UI", 8, "bold"),
                 padx=8, pady=4).pack(anchor="w")

        path_row = tk.Frame(custom_frame, bg=CARD)
        path_row.pack(fill="x", padx=8, pady=(0, 8))

        self._path_var = tk.StringVar()
        path_entry = tk.Entry(path_row, textvariable=self._path_var,
                              font=("Segoe UI", 9), bg="#FFFFFF", fg=TEXT,
                              relief="flat", bd=1)
        path_entry.pack(side="left", fill="x", expand=True, ipady=4)

        tk.Button(path_row, text="Browse…", command=self._browse_custom,
                  bg="#607D8B", fg="white", font=("Segoe UI", 8),
                  relief="flat", padx=8, pady=4, cursor="hand2").pack(side="right", padx=(6, 0))

        # ── ADB pull notice ──
        self._adb_notice = tk.Label(self.dlg, text="",
                                    bg="#FFF9C4", fg="#5D4037",
                                    font=("Segoe UI", 8), padx=10, pady=4,
                                    justify="left", wraplength=580)

        # ── Footer buttons ──
        footer = tk.Frame(self.dlg, bg=BG)
        footer.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(footer, text="Cancel", command=self._cancel,
                  bg="#9E9E9E", fg="white", font=("Segoe UI", 9),
                  relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right", padx=4)
        tk.Button(footer, text="Select Folder", command=self._select_item,
                  bg=PRIMARY, fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=14, pady=6, cursor="hand2").pack(side="right", padx=4)

        # Launch scan in background
        threading.Thread(target=self._background_scan, daemon=True).start()

        self.parent.wait_window(self.dlg)

    # ── Scanning ──

    def _background_scan(self):
        try:
            devices = self._scanner.scan_all()
        except Exception:
            devices = []
        self.dlg.after(0, self._populate_tree, devices)

    def _do_scan(self):
        self._status_lbl.config(text="Scanning…")
        self._tree.delete(*self._tree.get_children())
        threading.Thread(target=self._background_scan, daemon=True).start()

    def _populate_tree(self, devices: List[DeviceEntry]):
        self._devices = devices
        self._tree.delete(*self._tree.get_children())
        if not devices:
            self._status_lbl.config(text="No devices found.")
            return

        for i, d in enumerate(devices):
            tag = "local"
            if d.device_type in ("android_mtp", "android_adb"):
                tag = "adb" if d.device_type == "android_adb" else "phone"
            elif d.device_type == "ios":
                tag = "ios"
            elif d.device_type == "network":
                tag = "network"

            display_path = d.path if len(d.path) <= 48 else "…" + d.path[-45:]
            self._tree.insert("", "end", iid=str(i),
                              values=(f"{d.icon} {d.label}", d.device_type, display_path),
                              tags=(tag,))

        self._status_lbl.config(text=f"{len(devices)} device(s) / drive(s) found.")

    # ── Tree interactions ──

    def _on_tree_select(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(self._devices):
            d = self._devices[idx]
            self._path_var.set(d.path)
            if d.device_type == "android_adb" and d.path.startswith("adb://"):
                self._adb_notice.config(
                    text="⚠  ADB device detected. When you click 'Select Folder', "
                         "images will be pulled to a local temp folder first (may take a moment).")
                self._adb_notice.pack(fill="x", padx=10, pady=(0, 4))
            else:
                self._adb_notice.pack_forget()

    def _select_item(self):
        path = self._path_var.get().strip()
        if not path:
            sel = self._tree.selection()
            if sel:
                idx = int(sel[0])
                if idx < len(self._devices):
                    path = self._devices[idx].path

        if not path:
            messagebox.showwarning("No selection", "Please select a device or enter a path.",
                                   parent=self.dlg)
            return

        # Handle ADB virtual paths
        if path.startswith("adb://"):
            path = self._pull_adb(path)
            if not path:
                return

        if not os.path.exists(path):
            ans = messagebox.askyesno(
                "Path not found",
                f"The path does not exist or cannot be accessed:\n{path}\n\n"
                "Use it anyway?",
                parent=self.dlg)
            if not ans:
                return

        self.result_path = normalize_path(path)
        self.dlg.destroy()

    def _browse_custom(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(parent=self.dlg,
                                         title="Browse for images folder")
        if folder:
            self._path_var.set(normalize_path(folder))

    def _pull_adb(self, adb_path: str) -> str:
        """Pull ADB path with a progress dialog."""
        prog_dlg = tk.Toplevel(self.dlg)
        prog_dlg.title("Pulling images from device…")
        prog_dlg.geometry("360x100")
        prog_dlg.transient(self.dlg)
        prog_dlg.grab_set()
        prog_dlg.resizable(False, False)
        tk.Label(prog_dlg, text="Copying images from device to temporary folder…\nThis may take a moment.",
                 font=("Segoe UI", 9), pady=10).pack()
        pb = ttk.Progressbar(prog_dlg, mode="indeterminate")
        pb.pack(fill="x", padx=20)
        pb.start(15)
        prog_dlg.update()

        result = []

        def do_pull():
            r = self._scanner.resolve_adb_path(adb_path)
            result.append(r)
            prog_dlg.after(0, prog_dlg.destroy)

        t = threading.Thread(target=do_pull, daemon=True)
        t.start()
        self.dlg.wait_window(prog_dlg)
        t.join(timeout=1)

        pulled = result[0] if result else ""
        if not pulled or not os.path.exists(pulled):
            messagebox.showerror("ADB Error",
                                 "Could not pull images from device.\n"
                                 "Make sure USB Debugging is enabled on the device.",
                                 parent=self.dlg)
            return ""
        return pulled

    def _cancel(self):
        self.result_path = ""
        self.dlg.destroy()

    def _center(self):
        try:
            self.dlg.update_idletasks()
            sw = self.dlg.winfo_screenwidth()
            sh = self.dlg.winfo_screenheight()
            w = self.dlg.winfo_width()
            h = self.dlg.winfo_height()
            self.dlg.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
        except Exception:
            pass


# ──────────────────────────────────────────────
# Public API — drop-in replacement for filedialog.askdirectory
# ──────────────────────────────────────────────

def browse_device_folder(parent: tk.Widget,
                         title: str = "Select Images Folder") -> str:
    """
    Open the Device Browser dialog. Returns the selected path string or "".
    Drop-in replacement for tkinter.filedialog.askdirectory for device support.
    """
    dlg = DeviceBrowserDialog(parent, title=title)
    return dlg.result_path