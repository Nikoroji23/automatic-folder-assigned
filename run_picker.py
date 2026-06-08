import tkinter as tk
from image_picker_solution import ImagePickerDialog

if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()
    picker = ImagePickerDialog(root, r"C:\Users\Admin\Pictures\Screenshots", "niko")
    print('SELECTED:', picker.selected_images)
    try:
        root.destroy()
    except Exception:
        pass
