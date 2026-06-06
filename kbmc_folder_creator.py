import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import subprocess
import platform
from datetime import datetime
from PIL import Image, ImageTk
import shutil

APP_NAME = "KBMC Order Folder Creator with Auto-Video"
PRIMARY = "#C41E3A"  # Professional deep red
ACCENT = "#E74C3C"   # Bright red accent
BG = "#F5F5F5"       # Light gray background (modern)
CARD = "#FFFFFF"     # White cards
TEXT = "#333333"     # Dark text for light background
SECONDARY_TEXT = "#666666"  # Gray text
LIGHT_BORDER = "#E0E0E0"  # Light border
HOVER = "#A01830"    # Darker red for hover
ACCENT_HOVER = "#D63425"  # Darker accent for hover

# Video extensions to search for
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv']

class KBMCApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1200x1100")
        self.root.configure(bg=BG)

        self.destination = tk.StringVar()
        self.video_source = tk.StringVar()
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
            text="Order Folder Creator with Auto-Video Copy",
            bg=PRIMARY,
            fg="#FFD4D4",
            font=("Segoe UI", 14)
        )
        title_label.pack(side="left", padx=20)

        # ===== MAIN CONTENT =====
        scroll_container = tk.Frame(self.root, bg=BG)
        scroll_container.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(scroll_container, bg=BG, highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=v_scrollbar.set)

        v_scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        main = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=main, anchor="nw")

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        main.bind("<Configure>", on_frame_configure)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def enable_canvas_scroll(event):
            canvas.bind_all("<MouseWheel>", on_mousewheel)

        def disable_canvas_scroll(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", enable_canvas_scroll)
        canvas.bind("<Leave>", disable_canvas_scroll)

        # ===== SECTION: FOLDER PATHS =====
        paths_frame = tk.Frame(main, bg=CARD, relief="flat", bd=0)
        paths_frame.pack(fill="x", pady=(0, 15), padx=20)
        paths_frame.config(highlightthickness=1, highlightbackground=LIGHT_BORDER, highlightcolor=LIGHT_BORDER)

        # Destination Field
        dest_label = tk.Label(paths_frame, text="Destination Folder", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        dest_label.pack(anchor="w", padx=20, pady=(15, 5))

        dest_entry_frame = tk.Frame(paths_frame, bg="#F0F0F0", relief="solid", bd=2, highlightthickness=0)
        dest_entry_frame.pack(fill="x", padx=20, pady=(0, 15))

        dest_entry = tk.Entry(dest_entry_frame, textvariable=self.destination, font=("Segoe UI", 11), bg="#FFFFFF", fg=TEXT, relief="flat", bd=0, highlightthickness=0)
        dest_entry.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        dest_entry.insert(0, "📁 Click 'Browse' or paste folder path here...")
        self.setup_placeholder(dest_entry, "📁 Click 'Browse' or paste folder path here...")

        self.create_button(dest_entry_frame, "Browse", self.browse_destination, ACCENT, width=10, height=1, is_primary=False).pack(side="right", padx=(10, 0))

        # Video Source Field
        video_label = tk.Label(paths_frame, text="Video Source Folder", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        video_label.pack(anchor="w", padx=20, pady=(0, 5))

        video_entry_frame = tk.Frame(paths_frame, bg="#F0F0F0", relief="solid", bd=2, highlightthickness=0)
        video_entry_frame.pack(fill="x", padx=20, pady=(0, 15))

        video_entry = tk.Entry(video_entry_frame, textvariable=self.video_source, font=("Segoe UI", 11), bg="#FFFFFF", fg=TEXT, relief="flat", bd=0, highlightthickness=0)
        video_entry.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        video_entry.insert(0, "📹 Select folder where video files are stored...")
        self.setup_placeholder(video_entry, "📹 Select folder where video files are stored...")

        self.create_button(video_entry_frame, "Browse", self.browse_video_source, ACCENT, width=10, height=1, is_primary=False).pack(side="right", padx=(10, 0))

        # Date Field
        date_label = tk.Label(paths_frame, text="Date (MM-DD-YY)", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        date_label.pack(anchor="w", padx=20, pady=(0, 5))

        date_entry_frame = tk.Frame(paths_frame, bg="#F0F0F0", relief="solid", bd=2, highlightthickness=0)
        date_entry_frame.pack(fill="x", padx=20, pady=(0, 15))

        date_entry = tk.Entry(date_entry_frame, textvariable=self.date_var, font=("Segoe UI", 11), bg="#FFFFFF", fg=TEXT, relief="flat", bd=0, highlightthickness=0, width=25)
        date_entry.pack(side="left", padx=(10, 10), pady=8)
        date_entry.insert(0, "📅 Enter date (MM-DD-YY) or click 'Today'")
        self.setup_placeholder(date_entry, "📅 Enter date (MM-DD-YY) or click 'Today'")

        self.create_button(date_entry_frame, "Today", self.set_today, PRIMARY, width=10, height=1, is_primary=True).pack(side="left")

        format_hint = tk.Label(date_entry_frame, text="e.g., 06-03-26", bg=CARD, fg=SECONDARY_TEXT, font=("Segoe UI", 8))
        format_hint.pack(side="left", padx=10)

        # ===== SECTION: ORDER & VIDEO ID INPUTS =====
        inputs_frame = tk.Frame(main, bg=CARD, relief="flat", bd=0)
        inputs_frame.pack(fill="both", expand=True, pady=(0, 15), padx=20)
        inputs_frame.config(highlightthickness=1, highlightbackground=LIGHT_BORDER, highlightcolor=LIGHT_BORDER)
        inputs_frame.columnconfigure(0, weight=1, minsize=360)
        inputs_frame.columnconfigure(1, weight=1, minsize=360)
        inputs_frame.rowconfigure(0, weight=1)
        inputs_frame.rowconfigure(1, weight=0)

        # Top row: Order Numbers and Video IDs
        left_col = tk.Frame(inputs_frame, bg=CARD)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)

        orders_label = tk.Label(left_col, text="Order Numbers (one per line)", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        orders_label.pack(anchor="w", pady=(0, 5))

        orders_frame = tk.Frame(left_col, bg="#F0F0F0", relief="solid", bd=2, highlightthickness=0)
        orders_frame.pack(fill="both", expand=True)

        self.order_box = ScrolledText(
            orders_frame,
            font=("Segoe UI", 11),
            height=18,
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
        self.order_box.insert("1.0", "📋 Type order numbers here (one per line)\nExample:\n2502348234234\n2502348234235\n2502348234236")
        self.order_box.config(fg="#AAAAAA")

        def on_order_focus(event):
            if self.order_box.get("1.0", tk.END).startswith("📋"):
                self.order_box.delete("1.0", tk.END)
                self.order_box.config(fg=TEXT)

        self.order_box.bind("<FocusIn>", on_order_focus)

        middle_col = tk.Frame(inputs_frame, bg=CARD)
        middle_col.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)

        video_ids_label = tk.Label(middle_col, text="Video IDs (one per line)", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        video_ids_label.pack(anchor="w", pady=(0, 5))

        video_ids_frame = tk.Frame(middle_col, bg="#F0F0F0", relief="solid", bd=2, highlightthickness=0)
        video_ids_frame.pack(fill="both", expand=True)

        self.video_ids_box = ScrolledText(
            video_ids_frame,
            font=("Segoe UI", 11),
            height=18,
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
        self.video_ids_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.video_ids_box.insert("1.0", "🎬 Type corresponding video IDs (one per line)\nExample:\n2036\n2037\n2038")
        self.video_ids_box.config(fg="#AAAAAA")

        def on_video_focus(event):
            if self.video_ids_box.get("1.0", tk.END).startswith("🎬"):
                self.video_ids_box.delete("1.0", tk.END)
                self.video_ids_box.config(fg=TEXT)

        self.video_ids_box.bind("<FocusIn>", on_video_focus)

        # Bottom row: Notes and Missing Orders
        notes_row = tk.Frame(inputs_frame, bg=CARD)
        notes_row.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=(0, 20))
        notes_row.columnconfigure(0, weight=1, minsize=360)
        notes_row.columnconfigure(1, weight=1, minsize=360)

        notes_col = tk.Frame(notes_row, bg=CARD)
        notes_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        notes_label = tk.Label(notes_col, text="Automation Notes", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        notes_label.pack(anchor="w", pady=(0, 5))

        notes_frame = tk.Frame(notes_col, bg="#F0F0F0", relief="solid", bd=2, highlightthickness=0)
        notes_frame.pack(fill="both", expand=True)

        self.notes_box = ScrolledText(
            notes_frame,
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
            wrap="word",
            state="disabled"
        )
        self.notes_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.write_note("Note: Orders will still be created if no matching Video ID exists. Missing or unmatched entries are reported here.")

        missing_col = tk.Frame(notes_row, bg=CARD)
        missing_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        missing_label = tk.Label(missing_col, text="Orders Missing Video", bg=CARD, fg=PRIMARY, font=("Segoe UI", 10, "bold"))
        missing_label.pack(anchor="w", pady=(0, 5))

        missing_frame = tk.Frame(missing_col, bg="#F0F0F0", relief="solid", bd=2, highlightthickness=0)
        missing_frame.pack(fill="both", expand=True)

        self.missing_orders_box = ScrolledText(
            missing_frame,
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
            wrap="word",
            state="disabled"
        )
        self.missing_orders_box.pack(fill="both", expand=True, padx=10, pady=10)

        # ===== SECTION: ACTION BUTTONS =====
        actions_frame = tk.Frame(main, bg=BG)
        actions_frame.pack(fill="x", pady=(0, 15))

        btn1 = self.create_button(actions_frame, "✓ CREATE & COPY", self.create_folders_with_video, PRIMARY, width=25, height=1, is_primary=True)
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

    def browse_destination(self):
        folder = filedialog.askdirectory()
        if folder:
            self.destination.set(folder)
            self.write_log(f"📁 Destination selected: {folder}")

    def browse_video_source(self):
        folder = filedialog.askdirectory()
        if folder:
            self.video_source.set(folder)
            self.write_log(f"📹 Video source selected: {folder}")

    def write_log(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def write_note(self, text):
        self.notes_box.config(state="normal")
        self.notes_box.insert("end", text + "\n")
        self.notes_box.see("end")
        self.notes_box.config(state="disabled")

    def write_missing_order(self, order, reason=None):
        self.missing_orders_box.config(state="normal")
        if reason:
            self.missing_orders_box.insert("end", f"{order} — {reason}\n")
        else:
            self.missing_orders_box.insert("end", f"{order}\n")
        self.missing_orders_box.see("end")
        self.missing_orders_box.config(state="disabled")

    def find_video_file(self, video_id, video_source_folder):
        """Search for video file with given ID in video source folder"""
        if not os.path.exists(video_source_folder):
            return None
        
        for ext in VIDEO_EXTENSIONS:
            video_file = os.path.join(video_source_folder, f"{video_id}{ext}")
            if os.path.exists(video_file):
                return video_file
        
        return None

    def create_folders_with_video(self):
        destination = self.destination.get().strip()
        video_source = self.video_source.get().strip()
        date_input = self.date_var.get().strip()

        # ===== VALIDATION =====
        if not destination:
            messagebox.showerror("Error", "Select a destination folder.")
            return

        if not os.path.exists(destination):
            messagebox.showerror("Error", "Destination folder does not exist.")
            return

        if not video_source:
            messagebox.showerror("Error", "Select a video source folder.")
            return

        if not os.path.exists(video_source):
            messagebox.showerror("Error", "Video source folder does not exist.")
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
            if x.strip() and not x.strip().startswith("📋")
        ]

        # Get video IDs
        video_ids = [
            x.strip()
            for x in self.video_ids_box.get("1.0", "end").splitlines()
            if x.strip() and not x.strip().startswith("🎬")
        ]

        if not orders:
            messagebox.showerror("Error", "Enter at least one order number.")
            return

        has_no_video_ids = not bool(video_ids)
        extra_video_ids = []
        if len(video_ids) > len(orders):
            extra_video_ids = video_ids[len(orders):]
            video_ids = video_ids[:len(orders)]

        self.notes_box.config(state="normal")
        self.notes_box.delete("1.0", "end")
        self.notes_box.config(state="disabled")
        self.missing_orders_box.config(state="normal")
        self.missing_orders_box.delete("1.0", "end")
        self.missing_orders_box.config(state="disabled")

        self.progress["maximum"] = len(orders)
        self.progress["value"] = 0

        self.write_log(f"Starting folder creation with auto-video copy...\n")
        self.write_log(f"📅 Date: {date_input}")
        self.write_log(f"📍 Destination: {destination}")
        self.write_log(f"📹 Video source: {video_source}")
        self.write_log(f"📊 Orders: {len(orders)}\n")

        if has_no_video_ids:
            self.write_log("⚠️  No video IDs provided. Orders will still be created without video attachments.")
            self.write_note("No video IDs were provided; all orders will be created without video attachments.")

        if extra_video_ids:
            self.write_log(
                f"⚠️  Ignored {len(extra_video_ids)} extra Video ID(s) without matching orders: {', '.join(extra_video_ids)}"
            )
            self.write_note(
                f"Ignored extra Video ID(s): {', '.join(extra_video_ids)}"
            )

        video_ids_extended = video_ids + [None] * (len(orders) - len(video_ids))

        errors = []
        videos_found = 0
        videos_missing = 0
        missing_orders_numbers = []

        try:
            # ===== CREATE DATE FOLDER =====
            date_folder = os.path.join(destination, date_input)
            os.makedirs(date_folder, exist_ok=True)
            self.write_log(f"✓ Created date folder: {date_input}\n")

            # ===== CREATE ORDER FOLDERS INSIDE DATE FOLDER =====
            for i, (order, video_id) in enumerate(zip(orders, video_ids_extended), start=1):
                try:
                    # Order folder path: destination/DATE/ORDER_NUMBER/
                    order_folder = os.path.join(date_folder, order)

                    # BEFORE SHIPPING subfolder
                    before_shipping = os.path.join(order_folder, "BEFORE SHIPPING")
                    os.makedirs(before_shipping, exist_ok=True)

                    self.write_log(f"  ├─ {order}/")
                    self.write_log(f"  │  ├─ BEFORE SHIPPING/")

                    if video_id:
                        video_file = self.find_video_file(video_id, video_source)
                        if video_file:
                            try:
                                video_filename = os.path.basename(video_file)
                                destination_path = os.path.join(before_shipping, video_filename)
                                shutil.copy2(video_file, destination_path)
                                self.write_log(f"  │  │  ✓ Copied: {video_filename}")
                                videos_found += 1
                            except Exception as e:
                                self.write_log(f"  │  │  ✗ Failed to copy video: {str(e)}")
                                self.write_note(f"Order {order}: failed to copy video ID {video_id}.")
                                self.write_missing_order(order, f"failed to copy video ID {video_id}")
                                missing_orders_numbers.append(order)
                                videos_missing += 1
                        else:
                            self.write_log(f"  │  │  ⚠️  Video ID '{video_id}' not found in source folder")
                            self.write_note(f"Order {order}: video ID '{video_id}' not found.")
                            self.write_missing_order(order, f"video ID '{video_id}' missing in source")
                            missing_orders_numbers.append(order)
                            videos_missing += 1
                    else:
                        self.write_log(f"  │  │  ⚠️  No Video ID provided for order {order}. Order created without video.")
                        self.write_note(f"Order {order}: created without a matching Video ID.")
                        self.write_missing_order(order, "no Video ID provided")
                        missing_orders_numbers.append(order)

                    # UPON RETURNS subfolder
                    upon_returns = os.path.join(order_folder, "UPON RETURNS")
                    os.makedirs(upon_returns, exist_ok=True)
                    self.write_log(f"  │  └─ UPON RETURNS/")

                    self.progress["value"] = i
                    self.status.config(text=f"🔄 Processing {i}/{len(orders)}...", fg="#F57C00")
                    self.root.update_idletasks()

                except Exception as e:
                    error_msg = f"✗ Failed to create {order}: {str(e)}"
                    self.write_log(error_msg)
                    errors.append(error_msg)

            self.status.config(text="✅ Completed Successfully", fg="#2E7D32")
            # Summarize orders that did not receive copied videos (only order numbers)
            if missing_orders_numbers:
                # Preserve first-seen order and remove duplicates
                seen = []
                for o in missing_orders_numbers:
                    if o not in seen:
                        seen.append(o)
                self.write_note("Orders without copied videos: " + ", ".join(seen))
                # Replace missing orders box contents with concise order numbers
                self.missing_orders_box.config(state="normal")
                self.missing_orders_box.delete("1.0", "end")
                for o in seen:
                    self.missing_orders_box.insert("end", f"{o}\n")
                self.missing_orders_box.config(state="disabled")

            self.write_log(f"\n{'='*50}")
            
            if errors:
                self.write_log(f"⚠️  Completed with {len(errors)} error(s)")
                messagebox.showwarning(
                    "Partial Success",
                    f"Created {len(orders) - len(errors)}/{len(orders)} folders.\n\n"
                    f"Videos found: {videos_found}\n"
                    f"Videos missing: {videos_missing}\n\n"
                    f"Check the Activity Log for details."
                )
            else:
                self.write_log(f"✓ All {len(orders)} orders processed successfully!")
                self.write_log(f"✓ Videos copied: {videos_found}")
                if videos_missing > 0:
                    self.write_log(f"⚠️  Videos missing: {videos_missing}")
                if extra_video_ids:
                    self.write_log(f"⚠️  Extra video IDs ignored: {len(extra_video_ids)}")

                summary_message = (
                    f"Created {len(orders)} order folders in:\n\n"
                    f"{date_input}/\n\n"
                    f"Videos copied: {videos_found}\n"
                )
                if extra_video_ids:
                    summary_message += f"Extra video IDs ignored: {len(extra_video_ids)}\n"
                summary_message += f"Location: {destination}"
                messagebox.showinfo("Success", summary_message)
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
        # Normalize and expand user vars to avoid path issues
        full_path = os.path.normpath(os.path.expanduser(full_path))
        
        if not os.path.exists(full_path):
            messagebox.showerror("Error", f"Folder does not exist: {full_path}")
            return

        try:
            # Windows
            if platform.system() == "Windows":
                try:
                    os.startfile(full_path)
                except Exception:
                    # Fallback to explorer if startfile fails
                    subprocess.run(["explorer", full_path], check=False)
            # macOS
            elif platform.system() == "Darwin":
                subprocess.run(["open", full_path], check=False)
            # Linux
            else:
                subprocess.run(["xdg-open", full_path], check=False)
                
            self.write_log(f"📂 Opened: {full_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {str(e)}")
            self.write_log(f"✗ Failed to open {full_path}: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    KBMCApp(root)
    root.mainloop()