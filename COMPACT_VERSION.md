# KBMC Folder Creator - Compact Version

## Changes Made

Your KBMC Folder Creator app has been optimized to be **compact like a VS Code tab**. Here's what was changed:

### UI/Window Optimizations

| Aspect | Before | After |
|--------|--------|-------|
| **Window Size** | 1200x1100 px | **600x650 px** |
| **Header Height** | 90 px | **50 px** |
| **Logo Size** | 70x60 px | **45x35 px** |
| **Font Sizes** | 10-11 pt labels | **9 pt labels** |
| **Padding** | 20-30 px | **6-8 px** |
| **Text Areas Height** | 18 lines (Order) | **10 lines** |
| **Activity Log** | 6 lines | **5 lines** |

### Layout Changes

1. **Compact Header** - Shortened with smaller logo
2. **Reduced Spacing** - All padding minimized throughout
3. **Simplified Labels** - Shorter, more concise text
4. **Single-Column Input** - Order & Video ID boxes side-by-side (still visible)
5. **Merged Status Section** - Status & Notes combined in one section
6. **Smaller Fonts** - All fonts reduced by 1-2 points for better fit

## How to Use

### Run the Compact Version

**Option 1: Direct Python**
```cmd
cd automatic-folder-assigned
.venv\Scripts\python.exe kbmc_folder_creator.py
```

**Option 2: Build as EXE**
```cmd
cd automatic-folder-assigned
build_compact_exe.bat
```

This creates: `dist/kbmc_folder_creator.exe` (600x650 window)

### Features Preserved

✓ All functionality preserved  
✓ Order folder creation  
✓ Auto-video copy  
✓ Image picker dialog  
✓ Activity logging  
✓ Status tracking  

## Files Modified

- **kbmc_folder_creator.py** - Window geometry and UI spacing optimized
- **build_compact_exe.bat** - New build script for compact version

## Tips

- Window is now **compact like a VS Code tab** - won't cover entire screen
- All text areas are scrollable, so you can still work with long content
- If you want the window to be even smaller, modify the geometry in `kbmc_folder_creator.py` line 152:
  ```python
  self.root.geometry("600x650")  # Change these dimensions as needed
  ```

## Next Steps

Run `build_compact_exe.bat` to create the final EXE, or test directly with Python first!
