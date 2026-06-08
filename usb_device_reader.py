"""
USB Device Reader Module
Handles detection and reading of mobile/tablet devices connected via USB
Supports Android, iOS via USB, and other MTP/ADB devices
"""

import os
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class DeviceType(Enum):
    """Supported device types"""
    ANDROID = "android"
    IOS = "ios"
    MTP = "mtp"
    UNKNOWN = "unknown"


@dataclass
class DeviceInfo:
    """Device information container"""
    device_id: str
    name: str
    device_type: DeviceType
    mount_path: str
    model: str
    is_connected: bool


class USBDeviceDetector:
    """Detects USB-connected mobile/tablet devices"""
    
    def __init__(self):
        self.devices: Dict[str, DeviceInfo] = {}
    
    def detect_devices(self) -> List[DeviceInfo]:
        """Detect all connected USB devices"""
        devices = []
        
        # Check for Android devices via ADB
        devices.extend(self._detect_adb_devices())
        
        # Check for MTP devices (both Android and iOS)
        devices.extend(self._detect_mtp_devices())
        
        # Check for mounted devices
        devices.extend(self._detect_mounted_devices())
        
        self.devices = {d.device_id: d for d in devices}
        return devices
    
    def _detect_adb_devices(self) -> List[DeviceInfo]:
        """Detect Android devices via ADB"""
        devices = []
        try:
            result = subprocess.run(['adb', 'devices', '-l'], 
                                  capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 2 and parts[1] != 'offline':
                    device_id = parts[0]
                    model = self._get_adb_device_model(device_id)
                    
                    devices.append(DeviceInfo(
                        device_id=device_id,
                        name=f"Android Device ({model})",
                        device_type=DeviceType.ANDROID,
                        mount_path=f"adb://{device_id}",
                        model=model,
                        is_connected=True
                    ))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return devices
    
    def _get_adb_device_model(self, device_id: str) -> str:
        """Get Android device model name"""
        try:
            result = subprocess.run(['adb', '-s', device_id, 'shell', 
                                   'getprop', 'ro.product.model'],
                                  capture_output=True, text=True, timeout=3)
            return result.stdout.strip() or "Unknown Model"
        except:
            return "Unknown Model"
    
    def _detect_mtp_devices(self) -> List[DeviceInfo]:
        """Detect MTP devices (Android/iOS over USB)"""
        devices = []
        try:
            # Try using jmtpfs or similar MTP detection
            result = subprocess.run(['lsusb'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                # Look for Apple and Android device identifiers
                if 'Apple' in line or 'Android' in line:
                    device_id = f"mtp_{len(devices)}"
                    device_type = DeviceType.IOS if 'Apple' in line else DeviceType.MTP
                    
                    devices.append(DeviceInfo(
                        device_id=device_id,
                        name=line,
                        device_type=device_type,
                        mount_path=f"/media/mtp/{device_id}",
                        model=line,
                        is_connected=True
                    ))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return devices
    
    def _detect_mounted_devices(self) -> List[DeviceInfo]:
        """Detect mounted USB devices in /media and /mnt"""
        devices = []
        mount_points = []
        
        # Check common mount locations
        for mount_dir in ['/media', '/mnt']:
            if os.path.exists(mount_dir):
                try:
                    for entry in os.listdir(mount_dir):
                        full_path = os.path.join(mount_dir, entry)
                        if os.path.isdir(full_path) and os.access(full_path, os.R_OK):
                            mount_points.append(full_path)
                except PermissionError:
                    pass
        
        for mount_path in mount_points:
            device_id = f"usb_{os.path.basename(mount_path)}"
            devices.append(DeviceInfo(
                device_id=device_id,
                name=os.path.basename(mount_path),
                device_type=DeviceType.UNKNOWN,
                mount_path=mount_path,
                model="USB Storage",
                is_connected=True
            ))
        
        return devices


class DeviceFileReader:
    """Reads files from connected USB devices"""
    
    def __init__(self, device: DeviceInfo):
        self.device = device
    
    def list_directory(self, path: str = "/") -> List[Dict]:
        """List contents of a directory on the device"""
        if self.device.device_type == DeviceType.ANDROID and self.device.mount_path.startswith("adb://"):
            return self._list_adb_directory(path)
        else:
            return self._list_mounted_directory(path)
    
    def _list_adb_directory(self, path: str) -> List[Dict]:
        """List directory contents via ADB"""
        contents = []
        try:
            device_id = self.device.device_id
            # List storage directory
            result = subprocess.run(
                ['adb', '-s', device_id, 'shell', 'ls', '-la', path],
                capture_output=True, text=True, timeout=5
            )
            
            lines = result.stdout.strip().split('\n')[1:]  # Skip 'total' line
            
            for line in lines:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 9:
                    is_dir = line[0] == 'd'
                    size = int(parts[4]) if not is_dir else 0
                    name = ' '.join(parts[8:])
                    
                    contents.append({
                        'name': name,
                        'type': 'directory' if is_dir else 'file',
                        'size': size,
                        'path': f"{path.rstrip('/')}/{name}"
                    })
        except Exception as e:
            print(f"Error reading ADB directory: {e}")
        
        return contents
    
    def _list_mounted_directory(self, path: str) -> List[Dict]:
        """List directory contents on mounted device"""
        contents = []
        try:
            full_path = os.path.join(self.device.mount_path, path.lstrip('/'))
            
            if not os.path.exists(full_path):
                return contents
            
            for entry in os.listdir(full_path):
                entry_path = os.path.join(full_path, entry)
                is_dir = os.path.isdir(entry_path)
                
                try:
                    size = 0 if is_dir else os.path.getsize(entry_path)
                except OSError:
                    size = 0
                
                contents.append({
                    'name': entry,
                    'type': 'directory' if is_dir else 'file',
                    'size': size,
                    'path': f"{path.rstrip('/')}/{entry}"
                })
        except PermissionError as e:
            print(f"Permission denied accessing {path}: {e}")
        
        return sorted(contents, key=lambda x: (x['type'] != 'directory', x['name']))
    
    def read_file(self, file_path: str) -> Optional[bytes]:
        """Read a file from the device"""
        if self.device.device_type == DeviceType.ANDROID and self.device.mount_path.startswith("adb://"):
            return self._read_adb_file(file_path)
        else:
            return self._read_mounted_file(file_path)
    
    def _read_adb_file(self, file_path: str) -> Optional[bytes]:
        """Read file via ADB"""
        try:
            device_id = self.device.device_id
            result = subprocess.run(
                ['adb', '-s', device_id, 'pull', file_path, '-'],
                capture_output=True, timeout=10
            )
            return result.stdout if result.returncode == 0 else None
        except Exception as e:
            print(f"Error reading ADB file: {e}")
            return None
    
    def _read_mounted_file(self, file_path: str) -> Optional[bytes]:
        """Read file from mounted device"""
        try:
            full_path = os.path.join(self.device.mount_path, file_path.lstrip('/'))
            with open(full_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    
    def get_images(self, search_paths: List[str] = None) -> List[Dict]:
        """Find all images on the device"""
        if search_paths is None:
            search_paths = ['/DCIM', '/Pictures', '/Photos', '/storage/emulated/0/DCIM']
        
        images = []
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        for search_path in search_paths:
            images.extend(self._find_images_recursive(search_path, image_extensions))
        
        return images
    
    def _find_images_recursive(self, path: str, extensions: set, max_depth: int = 5) -> List[Dict]:
        """Recursively find images"""
        images = []
        if max_depth <= 0:
            return images
        
        try:
            contents = self.list_directory(path)
            
            for item in contents:
                if item['type'] == 'file' and any(item['name'].lower().endswith(ext) for ext in extensions):
                    images.append({
                        'name': item['name'],
                        'path': item['path'],
                        'size': item['size']
                    })
                elif item['type'] == 'directory' and not item['name'].startswith('.'):
                    images.extend(self._find_images_recursive(item['path'], extensions, max_depth - 1))
        except Exception as e:
            print(f"Error scanning {path}: {e}")
        
        return images


class DeviceManager:
    """Main interface for managing USB devices"""
    
    def __init__(self):
        self.detector = USBDeviceDetector()
        self.devices: Dict[str, DeviceInfo] = {}
        self.readers: Dict[str, DeviceFileReader] = {}
    
    def refresh_devices(self) -> List[DeviceInfo]:
        """Refresh list of connected devices"""
        devices = self.detector.detect_devices()
        self.devices = {d.device_id: d for d in devices}
        self.readers = {d.device_id: DeviceFileReader(d) for d in devices}
        return devices
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Get device by ID"""
        return self.devices.get(device_id)
    
    def list_devices(self) -> List[DeviceInfo]:
        """Get all connected devices"""
        return list(self.devices.values())
    
    def get_reader(self, device_id: str) -> Optional[DeviceFileReader]:
        """Get file reader for a device"""
        return self.readers.get(device_id)
    
    def export_device_tree(self, device_id: str, output_path: str, 
                          search_paths: List[str] = None) -> Dict:
        """Export device directory structure to JSON"""
        device = self.get_device(device_id)
        if not device:
            return {}
        
        reader = self.get_reader(device_id)
        tree = {
            'device': {
                'id': device.device_id,
                'name': device.name,
                'type': device.device_type.value,
                'model': device.model
            },
            'contents': self._build_tree(reader, search_paths)
        }
        
        with open(output_path, 'w') as f:
            json.dump(tree, f, indent=2)
        
        return tree
    
    def _build_tree(self, reader: DeviceFileReader, paths: List[str] = None) -> List[Dict]:
        """Build directory tree recursively"""
        if paths is None:
            paths = ['/']
        
        result = []
        for path in paths:
            result.extend(self._build_tree_recursive(reader, path))
        
        return result
    
    def _build_tree_recursive(self, reader: DeviceFileReader, path: str) -> List[Dict]:
        """Recursively build tree structure"""
        try:
            contents = reader.list_directory(path)
            tree = []
            
            for item in contents:
                node = {
                    'name': item['name'],
                    'type': item['type'],
                    'size': item['size']
                }
                
                if item['type'] == 'directory' and not item['name'].startswith('.'):
                    node['children'] = self._build_tree_recursive(reader, item['path'])
                
                tree.append(node)
            
            return tree
        except Exception as e:
            print(f"Error building tree for {path}: {e}")
            return []


if __name__ == "__main__":
    # Example usage
    manager = DeviceManager()
    
    print("Scanning for USB devices...")
    devices = manager.refresh_devices()
    
    if devices:
        print(f"\nFound {len(devices)} device(s):\n")
        for device in devices:
            print(f"  ID: {device.device_id}")
            print(f"  Name: {device.name}")
            print(f"  Type: {device.device_type.value}")
            print(f"  Model: {device.model}")
            print(f"  Mount: {device.mount_path}\n")
        
        # Example: List images from first device
        first_device = devices[0]
        reader = manager.get_reader(first_device.device_id)
        
        print(f"Root directory contents of {first_device.name}:")
        contents = reader.list_directory("/")
        for item in contents[:10]:  # Show first 10
            print(f"  {item['type']:10} {item['name']:40} {item['size']:>10} bytes")
    else:
        print("No USB devices found!")