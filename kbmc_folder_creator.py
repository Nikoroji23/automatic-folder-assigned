import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import subprocess
import platform
from datetime import datetime
from PIL import Image, ImageTk

APP_NAME = "KBMC Order Folder Creator"
PRIMARY = "#C41E3A"  # Professional deep red
ACCENT = "#E74C3C"   # Bright red accent
BG = "#F5F5F5"       # Light gray background (modern)
CARD = "#FFFFFF"     # White cards
TEXT = "#333333"     # Dark text for light background
SECONDARY_TEXT = "#666666"  # Gray text
LIGHT_BORDER = "#E0E0E0"  # Light border
HOVER = "#A01830"    # Darker red for hover
ACCENT_HOVER = "#D63425"  # Darker accent for hover

class KBMCApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1200x900")
        self.root.configure(bg=BG)

        self.destination = tk.StringVar()
        self.date_var = tk.StringVar()
        self.buttons = []  # Store button references for hover effects
        
        # Load logo
        self.logo_image = None
        logo_path = os.path.join(os.path.dirname(__file__), "kbmc_logo.png")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                img = img.resize((70, 60), Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Could not load logo: {e}")

        self.build_ui()

    def create_button(self, parent, text, command, bg_color, width=None, height=None, is_primary=True):
        """Create a modern styled button with subtle hover effects"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg_color,
            fg="white" if is_primary else "white",
            font=("Segoe UI", 10, "bold"),
            height=height or 1,
            width=width or 15,
            relief="flat",
            bd=0,
            activebackground=HOVER if is_primary else ACCENT_HOVER,
            activeforeground="white",
            cursor="hand2",
            padx=12,
            pady=8
        )
        
        # Store for later reference
        self.buttons.append((btn, bg_color, HOVER if is_primary else ACCENT_HOVER))
        
        # Bind hover effects
        btn.bind("<Enter>", lambda e, b=btn, hover_color=HOVER if is_primary else ACCENT_HOVER: b.config(bg=hover_color))
        btn.bind("<Leave>", lambda e, b=btn, normal_color=bg_color: b.config(bg=normal_color))
        
        return btn

    def build_ui(self):
        self.root.configure(bg=BG)
        
        # ===== HEADER =====
        header = tk.Frame(self.root, bg=PRIMARY, height=90)
        header.pack(fill="x")
        
        header_content = tk.Frame(header, bg=PRIMARY)
        header_content.pack(fill="both", expand=True, padx=30, pady=15)

        # Logo
        if self.logo_image:
            logo_label = tk.Label(header_content, image=self.logo_image, bg=PRIMARY)
            logo_label.pack(side="left", padx=(0, 15))
        else:
            logo_label = tk.Label(
                header_content,
                text="🏢 KBMC",
                bg=PRIMARY,
                fg="white",
                font=("Segoe UI", 24, "bold")
            )
            logo_label.pack(side="left")

        title_label = tk.Label(
            header_content,
            text="Order Folder Creator Enterprise",
            bg=PRIMARY,
            fg="#FFD4D4",
            font=("Segoe UI", 14)
        )
        title_label.pack(side="left", padx=20)

        # ===== MAIN CONTENT =====
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=30, pady=20)

        # ===== SECTION: INPUT FIELDS =====
        input_frame = tk.Frame(main, bg=CARD, relief="flat", bd=0)
        input_frame.pack(fill="x", pady=(0, 15))
        
        # Add subtle border effect
        input_frame.config(highlightthickness=1, highlightbackground=LIGHT_BORDER, highlightcolor=LIGHT_BORDER)

        # Destination Field
        dest_label = tk.Label(input_frame, text="Destination Folder", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        dest_label.pack(anchor="w", padx=20, pady=(15, 5))

        dest_entry_frame = tk.Frame(input_frame, bg="#F0F0F0", relief="solid", bd=2, highlightthickness=0)
        dest_entry_frame.pack(fill="x", padx=20, pady=(0, 15))

        dest_entry = tk.Entry(dest_entry_frame, textvariable=self.destination, font=("Segoe UI", 11), bg="#FFFFFF", fg=TEXT, relief="flat", bd=0, highlightthickness=0)
        dest_entry.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        dest_entry.insert(0, "📁 Click 'Browse' or paste folder path here...")
        self.setup_placeholder(dest_entry, "📁 Click 'Browse' or paste folder path here...")

        self.create_button(dest_entry_frame, "Browse", self.browse, ACCENT, width=10, height=1, is_primary=False).pack(side="right", padx=(10, 0))

        # Date Field
        date_label = tk.Label(input_frame, text="Date (MM-DD-YY)", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        date_label.pack(anchor="w", padx=20, pady=(0, 5))

        date_entry_frame = tk.Frame(input_frame, bg="#F0F0F0", relief="solid", bd=2, highlightthickness=0)
        date_entry_frame.pack(fill="x", padx=20, pady=(0, 15))

        date_entry = tk.Entry(date_entry_frame, textvariable=self.date_var, font=("Segoe UI", 11), bg="#FFFFFF", fg=TEXT, relief="flat", bd=0, highlightthickness=0, width=25)
        date_entry.pack(side="left", padx=(10, 10), pady=8)
        date_entry.insert(0, "📅 Enter date (MM-DD-YY) or click 'Today'")
        self.setup_placeholder(date_entry, "📅 Enter date (MM-DD-YY) or click 'Today'")

        self.create_button(date_entry_frame, "Today", self.set_today, PRIMARY, width=10, height=1, is_primary=True).pack(side="left")

        format_hint = tk.Label(date_entry_frame, text="e.g., 06-03-26", bg=CARD, fg=SECONDARY_TEXT, font=("Segoe UI", 8))
        format_hint.pack(side="left", padx=10)

        # Order Numbers Field
        orders_label = tk.Label(input_frame, text="Order Numbers (one per line)", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        orders_label.pack(anchor="w", padx=20, pady=(0, 5))

        orders_frame = tk.Frame(input_frame, bg="#F0F0F0", relief="solid", bd=2, highlightthickness=0)
        orders_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.order_box = ScrolledText(
            orders_frame,
            font=("Segoe UI", 11),
            height=8,
            bg="#FFFFFF",
            fg=TEXT,
            relief="flat",
            bd=0,
            insertbackground=PRIMARY,
            selectbackground=PRIMARY,
            selectforeground="white",
            highlightthickness=0,
            wrap="word"
        )
        self.order_box.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add placeholder text
        self.order_box.insert("1.0", "📋 Type order numbers here (one per line)\nExample:\n123456\n789012\n345678")
        self.order_box.config(fg="#AAAAAA")
        
        # Clear placeholder on first focus
        def on_order_focus(event):
            if self.order_box.get("1.0", tk.END).startswith("📋"):
                self.order_box.delete("1.0", tk.END)
                self.order_box.config(fg=TEXT)
        
        self.order_box.bind("<FocusIn>", on_order_focus)

        # ===== SECTION: ACTION BUTTONS =====
        actions_frame = tk.Frame(main, bg=BG)
        actions_frame.pack(fill="x", pady=(0, 15))

        btn1 = self.create_button(actions_frame, "✓ CREATE FOLDERS", self.create_folders, PRIMARY, width=25, height=1, is_primary=True)
        btn1.pack(side="left", padx=(0, 10))

        btn2 = self.create_button(actions_frame, "📂 OPEN LOCATION", self.open_location, ACCENT, width=25, height=1, is_primary=False)
        btn2.pack(side="left")

        # ===== SECTION: PROGRESS & STATUS =====
        progress_frame = tk.Frame(main, bg=CARD, relief="flat", bd=0)
        progress_frame.pack(fill="x", pady=(0, 15))
        progress_frame.config(highlightthickness=1, highlightbackground=LIGHT_BORDER, highlightcolor=LIGHT_BORDER)

        status_label = tk.Label(progress_frame, text="Status", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        status_label.pack(anchor="w", padx=20, pady=(15, 5))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Modern.Horizontal.TProgressbar", background=PRIMARY, troughcolor="#E0E0E0", bordercolor="white", lightcolor=PRIMARY, darkcolor=PRIMARY)
        
        self.progress = ttk.Progressbar(progress_frame, style="Modern.Horizontal.TProgressbar", mode='determinate', length=300)
        self.progress.pack(fill="x", padx=20, pady=5)

        self.status = tk.Label(
            progress_frame,
            text="🟢 Ready",
            bg=CARD,
            fg="#4CAF50",
            anchor="w",
            font=("Segoe UI", 9, "bold")
        )
        self.status.pack(fill="x", padx=20, pady=(0, 15))

        # ===== SECTION: ACTIVITY LOG =====
        log_frame = tk.Frame(main, bg=CARD, relief="flat", bd=0)
        log_frame.pack(fill="both", expand=True)
        log_frame.config(highlightthickness=1, highlightbackground=LIGHT_BORDER, highlightcolor=LIGHT_BORDER)

        log_label = tk.Label(log_frame, text="Activity Log", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        log_label.pack(anchor="w", padx=20, pady=(15, 10))

        self.log = ScrolledText(
            log_frame,
            height=6,
            font=("Consolas", 9),
            bg="#FAFAFA",
            fg=TEXT,
            relief="flat",
            bd=0,
            insertbackground=PRIMARY,
            selectbackground=PRIMARY,
            selectforeground="white",
            highlightthickness=0
        )
        self.log.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def set_today(self):
        """Set date to today in MM-DD-YY format"""
        today = datetime.now()
        formatted_date = today.strftime("%m-%d-%y")
        self.date_var.set(formatted_date)
        self.write_log(f"📅 Date set to today: {formatted_date}")

    def setup_placeholder(self, entry, placeholder):
        """Setup placeholder text for entry fields"""
        entry_placeholder = [placeholder]
        
        def on_focus_in(event):
            if entry.get() == entry_placeholder[0]:
                entry.delete(0, tk.END)
                entry.config(fg=TEXT)
        
        def on_focus_out(event):
            if entry.get() == "":
                entry.insert(0, entry_placeholder[0])
                entry.config(fg="#AAAAAA")
        
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        entry.config(fg="#AAAAAA")

    def validate_date(self, date_str):
        """Validate date format MM-DD-YY"""
        try:
            datetime.strptime(date_str, "%m-%d-%y")
            return True
        except ValueError:
            return False

    def browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.destination.set(folder)
            self.write_log(f"📁 Destination selected: {folder}")

    def write_log(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def create_folders(self):
        destination = self.destination.get().strip()
        date_input = self.date_var.get().strip()

        # ===== VALIDATION =====
        if not destination:
            messagebox.showerror("Error", "Select a destination folder.")
            return

        if not os.path.exists(destination):
            messagebox.showerror("Error", "Destination folder does not exist.")
            return

        if not date_input:
            messagebox.showerror("Error", "Enter a date (MM-DD-YY format).")
            return

        if not self.validate_date(date_input):
            messagebox.showerror("Error", f"Invalid date format.\nPlease use: MM-DD-YY\nExample: 06-03-26")
            return

        # Get order numbers
        orders = [
            x.strip()
            for x in self.order_box.get("1.0", "end").splitlines()
            if x.strip()
        ]

        orders = list(dict.fromkeys(orders))

        if not orders:
            messagebox.showerror("Error", "Enter at least one order number.")
            return

        self.progress["maximum"] = len(orders)
        self.progress["value"] = 0

        self.log.delete("1.0", "end")
        self.write_log(f"Starting folder creation...\n")
        self.write_log(f"📅 Date: {date_input}")
        self.write_log(f"📍 Location: {destination}")
        self.write_log(f"📊 Orders: {len(orders)}\n")

        errors = []

        try:
            # ===== CREATE DATE FOLDER =====
            date_folder = os.path.join(destination, date_input)
            os.makedirs(date_folder, exist_ok=True)
            self.write_log(f"✓ Created date folder: {date_input}\n")

            # ===== CREATE ORDER FOLDERS INSIDE DATE FOLDER =====
            for i, order in enumerate(orders, start=1):
                try:
                    # Order folder path: destination/DATE/ORDER_NUMBER/
                    order_folder = os.path.join(date_folder, order)

                    # BEFORE SHIPPING subfolder
                    before_shipping = os.path.join(order_folder, "BEFORE SHIPPING")
                    os.makedirs(before_shipping, exist_ok=True)

                    # UPON RETURNS subfolder
                    upon_returns = os.path.join(order_folder, "UPON RETURNS")
                    os.makedirs(upon_returns, exist_ok=True)

                    self.progress["value"] = i
                    self.status.config(text=f"🔄 Processing {i}/{len(orders)}...", fg="#F57C00")
                    self.root.update_idletasks()

                    self.write_log(f"  ├─ {order}/")
                    self.write_log(f"  │  ├─ BEFORE SHIPPING/")
                    self.write_log(f"  │  └─ UPON RETURNS/")

                except Exception as e:
                    error_msg = f"✗ Failed to create {order}: {str(e)}"
                    self.write_log(error_msg)
                    errors.append(error_msg)

            self.status.config(text="✅ Completed Successfully", fg="#2E7D32")
            self.write_log(f"\n{'='*50}")
            
            if errors:
                self.write_log(f"⚠️  Completed with {len(errors)} error(s)")
                messagebox.showwarning(
                    "Partial Success",
                    f"Created {len(orders) - len(errors)}/{len(orders)} folders.\n\n"
                    f"Check the Activity Log for details."
                )
            else:
                self.write_log(f"✓ All {len(orders)} orders processed successfully!")
                messagebox.showinfo(
                    "Success",
                    f"Created {len(orders)} order folders in:\n\n"
                    f"{date_input}/\n\n"
                    f"Location: {destination}"
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create folders: {str(e)}")
            self.write_log(f"✗ Fatal error: {str(e)}")

    def open_location(self):
        """Cross-platform folder opening"""
        path = self.destination.get().strip()
        date_input = self.date_var.get().strip()
        
        if not path:
            messagebox.showerror("Error", "Select a destination folder first.")
            return
        
        if not date_input:
            messagebox.showerror("Error", "Enter a date first.")
            return
            
        # Open the date folder
        full_path = os.path.join(path, date_input)
        
        if not os.path.exists(full_path):
            messagebox.showerror("Error", f"Folder does not exist: {full_path}")
            return

        try:
            # Windows
            if platform.system() == "Windows":
                os.startfile(full_path)
            # macOS
            elif platform.system() == "Darwin":
                subprocess.run(["open", full_path], check=True)
            # Linux
            else:
                subprocess.run(["xdg-open", full_path], check=True)
                
            self.write_log(f"📂 Opened: {full_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {str(e)}")
            self.write_log(f"✗ Failed to open {full_path}: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    KBMCApp(root)
    root.mainloop()