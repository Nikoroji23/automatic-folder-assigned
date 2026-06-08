# kbmc_app.py
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import subprocess
import platform
from datetime import datetime
from PIL import Image, ImageTk
from image_picker_solution import copy_selected_images_for_order
import shutil

APP_NAME = "KBMC Order Folder Creator with Auto-Video"
PRIMARY = "#C41E3A"  # Professional deep red
ACCENT = "#E74C3C"   # Bright red accent
BG = "#F5F5F5"       # Light gray background (modern)
CARD = "#FFFFFF"     # White cards
TEXT = "#000000"     # Black text for light background
SECONDARY_TEXT = "#333333"  # Dark gray text
LIGHT_BORDER = "#E0E0E0"  # Light border
HOVER = "#A01830"    # Darker red for hover
ACCENT_HOVER = "#D63425"  # Darker accent for hover

# Video extensions to search for
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv']


def pick_images_for_orders_dialog_compact(parent, orders, images_source, date_folder_base,
                                          order_status, on_order_completed, logger=None):
    """
    Compact Assign Images dialog for small tabs.
    - orders: list of order strings
    - order_status: dict mapping order -> {'video_copied': bool, 'images_added': bool}
    - on_order_completed(order): callback to notify main UI that an order is completed
    """
    dlg = tk.Toplevel(parent)
    dlg.title("Assign Images")
    dlg.geometry("380x420")
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()

    # center over parent
    try:
        dlg.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        w = dlg.winfo_width()
        h = dlg.winfo_height()
        if pw <= 1 and ph <= 1:
            screen_w = dlg.winfo_screenwidth()
            screen_h = dlg.winfo_screenheight()
            x = (screen_w - w) // 2
            y = (screen_h - h) // 2
        else:
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
        dlg.geometry(f"+{x}+{y}")
    except Exception:
        pass

    tk.Label(dlg, text="Select order(s) then Pick Images", font=("Segoe UI", 9), padx=8, pady=6).pack(anchor="w")

    frame = tk.Frame(dlg)
    frame.pack(fill="both", expand=True, padx=8, pady=(0, 6))

    tv = ttk.Treeview(frame, columns=("order", "status"), show="headings", selectmode="extended", height=12)
    tv.heading("order", text="Order")
    tv.heading("status", text="Status")
    tv.column("order", anchor="w", width=220)
    tv.column("status", anchor="center", width=80)
    tv.pack(side="left", fill="both", expand=True)

    for o in orders:
        st = order_status.get(o, {})
        done = st.get("video_copied", False) and st.get("images_added", False)
        stat_text = "Done" if done else ("Video ✓" if st.get("video_copied", False) else "")
        tv.insert("", "end", iid=o, values=(o, stat_text))
        if done:
            tv.item(o, tags=("done",))
    tv.tag_configure("done", foreground="#999999")

    sb = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")

    btn_frame = tk.Frame(dlg)
    btn_frame.pack(fill="x", padx=8, pady=6)

    def pick_for_selected():
        sel = tv.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select at least one order.")
            return

        for iid in sel:
            order = iid
            st = order_status.setdefault(order, {})
            if st.get("video_copied", False) and st.get("images_added", False):
                try:
                    tv.delete(order)
                except Exception:
                    pass
                if on_order_completed:
                    on_order_completed(order)
                continue

            before_shipping = os.path.join(date_folder_base, order, "BEFORE SHIPPING")
            moved, errs = copy_selected_images_for_order(order, images_source, before_shipping, parent)

            if moved > 0:
                st["images_added"] = True

            if st.get("video_copied", False) and st.get("images_added", False):
                try:
                    tv.delete(order)
                except Exception:
                    pass
                if on_order_completed:
                    on_order_completed(order)

            if logger:
                logger(f"Images moved for {order}: {moved}")
                for e in errs:
                    logger(f"  Error: {e}")

            if moved > 0 and not errs:
                messagebox.showinfo("Done", f"{moved} image(s) moved for {order}.")
            elif moved > 0 and errs:
                messagebox.showwarning("Partial", f"{moved} image(s) moved for {order} with errors.")
            elif errs:
                messagebox.showwarning("Errors", f"Errors for {order}:\n" + "\n".join(errs))

    def done():
        dlg.destroy()

    tk.Button(btn_frame, text="Pick Images for Selected", command=pick_for_selected,
              bg="#1976D2", fg="white", font=("Segoe UI", 9), padx=6, pady=6).pack(side="left", padx=(0, 6))
    tk.Button(btn_frame, text="Done", command=done,
              bg="#999999", fg="white", font=("Segoe UI", 9), padx=6, pady=6).pack(side="right")

    parent.wait_window(dlg)


class KBMCApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x750")
        self.root.minsize(800, 600)
        self.root.configure(bg=BG)

        self.destination = tk.StringVar()
        self.video_source = tk.StringVar()
        self.images_source = tk.StringVar()
        self.date_var = tk.StringVar()
        self.buttons = []  # Store button references for hover effects
        self.animation_id = None
        self.animating_buttons = {}
        
        # Load logo
        self.logo_image = None
        logo_path = os.path.join(os.path.dirname(__file__), "kbmc_logo.png")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                img = img.resize((50, 45), Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Could not load logo: {e}")

        self.build_ui()

    def create_button(self, parent, text, command, bg_color, width=12, height=1):
        """Create modern styled button"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg_color,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            height=height,
            width=width,
            relief="flat",
            bd=0,
            activebackground=HOVER,
            activeforeground="white",
            cursor="hand2",
            padx=8,
            pady=5
        )
        btn.bind("<Enter>", lambda e, b=btn, color=bg_color: self.animate_button_hover(b, color, HOVER))
        btn.bind("<Leave>", lambda e, b=btn, color=bg_color: self.animate_button_leave(b, HOVER, color))
        return btn

    def interpolate_color(self, color1, color2, factor):
        """Interpolate between two hex colors"""
        c1 = int(color1[1:], 16)
        c2 = int(color2[1:], 16)
        r1, g1, b1 = (c1 >> 16) & 255, (c1 >> 8) & 255, c1 & 255
        r2, g2, b2 = (c2 >> 16) & 255, (c2 >> 8) & 255, c2 & 255
        r = int(r1 + (r2 - r1) * factor)
        g = int(g1 + (g2 - g1) * factor)
        b = int(b1 + (b2 - b1) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    def animate_button_hover(self, btn, start_color, end_color, steps=8):
        """Smooth button hover animation"""
        if btn in self.animating_buttons:
            self.root.after_cancel(self.animating_buttons[btn])
        
        def step(current_step):
            if current_step <= steps:
                factor = current_step / steps
                color = self.interpolate_color(start_color, end_color, factor)
                btn.config(bg=color)
                self.animating_buttons[btn] = self.root.after(20, step, current_step + 1)
            else:
                btn.config(bg=end_color)
                if btn in self.animating_buttons:
                    del self.animating_buttons[btn]
        
        step(0)

    def animate_button_leave(self, btn, current_color, target_color, steps=8):
        """Smooth button leave animation"""
        if btn in self.animating_buttons:
            self.root.after_cancel(self.animating_buttons[btn])
        
        def step(current_step):
            if current_step <= steps:
                factor = current_step / steps
                color = self.interpolate_color(current_color, target_color, factor)
                btn.config(bg=color)
                self.animating_buttons[btn] = self.root.after(20, step, current_step + 1)
            else:
                btn.config(bg=target_color)
                if btn in self.animating_buttons:
                    del self.animating_buttons[btn]
        
        step(0)

    def animate_frame_appearance(self, frame, duration_ms=300):
        """Animate frame appearance (fade-in like effect)"""
        original_bg = frame.cget("bg")
        steps = int(duration_ms / 20)
        
        def step(current_step):
            if current_step <= steps:
                alpha = current_step / steps
                # Apply a subtle highlighting effect
                frame.config(relief="solid", bd=0)
                self.root.after(20, step, current_step + 1)
            else:
                frame.config(relief="flat", bd=0)
        
        step(0)

    def animate_progress_smooth(self, target_value, duration_ms=500):
        """Smoothly animate progress bar to target value"""
        current = self.progress["value"]
        target = min(target_value, self.progress["maximum"])
        steps = int(duration_ms / 20)
        
        def step(current_step):
            if current_step <= steps:
                progress = current + (target - current) * (current_step / steps)
                self.progress["value"] = progress
                self.root.update_idletasks()
                self.root.after(20, step, current_step + 1)
            else:
                self.progress["value"] = target
        
        step(0)

    def animate_status_text(self, text, color, duration_ms=300):
        """Animate status text change with color transition"""
        def update_status():
            self.status.config(text=text, fg=color)
            self.status.update_idletasks()
        
        self.root.after(int(duration_ms / 2), update_status)

    def create_collapsible_section(self, parent, title, content_builder, initial_open=True):
        """Create a collapsible section with animation"""
        section_frame = tk.Frame(parent, bg=CARD, relief="flat", bd=0)
        section_frame.pack(fill="x", pady=(0, 8))
        section_frame.config(highlightthickness=1, highlightbackground=LIGHT_BORDER)
        
        # Header
        header_frame = tk.Frame(section_frame, bg=CARD, relief="flat", bd=0)
        header_frame.pack(fill="x", padx=10, pady=8)
        
        is_open = [initial_open]
        content_frame = tk.Frame(section_frame, bg=CARD)
        
        title_label = tk.Label(
            header_frame, 
            text=f"{'▼' if initial_open else '▶'} {title}",
            bg=CARD, 
            fg=PRIMARY, 
            font=("Segoe UI", 10, "bold"),
            cursor="hand2"
        )
        title_label.pack(side="left")
        
        def toggle_section():
            is_open[0] = not is_open[0]
            if is_open[0]:
                title_label.config(text=f"▼ {title}")
                content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
                content_builder(content_frame)
                self.animate_frame_appearance(content_frame, 200)
            else:
                title_label.config(text=f"▶ {title}")
                content_frame.pack_forget()
        
        title_label.bind("<Button-1>", lambda e: toggle_section())
        header_frame.bind("<Button-1>", lambda e: toggle_section())
        
        if initial_open:
            content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            content_builder(content_frame)
        
        return section_frame

    def build_ui(self):
        # ===== HEADER =====
        header = tk.Frame(self.root, bg=PRIMARY, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        header_content = tk.Frame(header, bg=PRIMARY)
        header_content.pack(fill="both", expand=True, padx=15, pady=10)

        if self.logo_image:
            logo_label = tk.Label(header_content, image=self.logo_image, bg=PRIMARY)
            logo_label.pack(side="left", padx=(0, 10))

        title_label = tk.Label(
            header_content,
            text="Order Folder Creator with Auto-Video",
            bg=PRIMARY,
            fg="white",
            font=("Segoe UI", 11, "bold")
        )
        title_label.pack(side="left")

        # ===== MAIN CONTENT =====
        main_frame = tk.Frame(self.root, bg=BG)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ===== PATHS SECTION =====
        paths_frame = tk.Frame(main_frame, bg=CARD, relief="flat", bd=0)
        paths_frame.pack(fill="x", pady=(0, 8))
        paths_frame.config(highlightthickness=1, highlightbackground=LIGHT_BORDER)

        # Destination
        tk.Label(paths_frame, text="Destination Folder", bg=CARD, fg=PRIMARY, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        dest_frame = tk.Frame(paths_frame, bg="#F0F0F0", relief="solid", bd=1)
        dest_frame.pack(fill="x", padx=10, pady=(0, 8))
        
        dest_entry = tk.Entry(dest_frame, textvariable=self.destination, font=("Segoe UI", 10), bg="#FFFFFF", fg=TEXT, relief="flat", bd=0)
        dest_entry.pack(side="left", fill="x", expand=True, padx=8, pady=5)
        self.create_button(dest_frame, "Browse", self.browse_destination, ACCENT, width=8).pack(side="right", padx=(5, 0))

        # Video Source
        tk.Label(paths_frame, text="Video Source Folder", bg=CARD, fg=PRIMARY, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(0, 2))
        video_frame = tk.Frame(paths_frame, bg="#F0F0F0", relief="solid", bd=1)
        video_frame.pack(fill="x", padx=10, pady=(0, 8))
        
        video_entry = tk.Entry(video_frame, textvariable=self.video_source, font=("Segoe UI", 10), bg="#FFFFFF", fg=TEXT, relief="flat", bd=0)
        video_entry.pack(side="left", fill="x", expand=True, padx=8, pady=5)
        self.create_button(video_frame, "Browse", self.browse_video_source, ACCENT, width=8).pack(side="right", padx=(5, 0))

        # Images Source
        tk.Label(paths_frame, text="Images Folder", bg=CARD, fg=PRIMARY, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(0, 2))
        images_frame = tk.Frame(paths_frame, bg="#F0F0F0", relief="solid", bd=1)
        images_frame.pack(fill="x", padx=10, pady=(0, 8))
        
        images_entry = tk.Entry(images_frame, textvariable=self.images_source, font=("Segoe UI", 10), bg="#FFFFFF", fg=TEXT, relief="flat", bd=0)
        images_entry.pack(side="left", fill="x", expand=True, padx=8, pady=5)
        self.create_button(images_frame, "Browse", self.browse_images_source, ACCENT, width=8).pack(side="right", padx=(5, 0))

        # Date
        tk.Label(paths_frame, text="Date (MM-DD-YY)", bg=CARD, fg=PRIMARY, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(0, 2))
        date_frame = tk.Frame(paths_frame, bg="#F0F0F0", relief="solid", bd=1)
        date_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        date_entry = tk.Entry(date_frame, textvariable=self.date_var, font=("Segoe UI", 10), bg="#FFFFFF", fg=TEXT, relief="flat", bd=0, width=15)
        date_entry.pack(side="left", padx=(8, 5), pady=5)
        self.create_button(date_frame, "Today", self.set_today, PRIMARY, width=8).pack(side="left", padx=(0, 5))
        tk.Label(date_frame, text="e.g., 06-03-26", bg="#F0F0F0", fg=SECONDARY_TEXT, font=("Segoe UI", 8)).pack(side="left")

        # ===== DATA SECTION =====
        data_frame = tk.Frame(main_frame, bg=CARD, relief="flat", bd=0)
        data_frame.pack(fill="both", expand=True, pady=(0, 8))
        data_frame.config(highlightthickness=1, highlightbackground=LIGHT_BORDER)
        data_frame.columnconfigure(0, weight=1)
        data_frame.columnconfigure(1, weight=1)

        # Order Numbers
        tk.Label(data_frame, text="Order Numbers", bg=CARD, fg=PRIMARY, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        
        orders_box_frame = tk.Frame(data_frame, bg="#F0F0F0", relief="solid", bd=1)
        orders_box_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10), ipady=0)
        data_frame.rowconfigure(1, weight=1)
        
        self.order_box = ScrolledText(
            orders_box_frame,
            font=("Consolas", 9),
            height=8,
            bg="#FFFFFF",
            fg="#000000",
            relief="flat",
            bd=0,
            insertbackground=PRIMARY,
            highlightthickness=0,
            wrap="word"
        )
        self.order_box.pack(fill="both", expand=True, padx=8, pady=8)
        self.order_box.insert("1.0", "2502348234234\n2502348234235\n2502348234236")

        def on_order_focus(event):
            if self.order_box.get("1.0", tk.END).startswith("250234"):
                pass
            if self.order_box.get("1.0", "1.1") == "2":
                self.order_box.config(fg=TEXT)

        self.order_box.bind("<FocusIn>", on_order_focus)

        # Video IDs
        tk.Label(data_frame, text="Video IDs", bg=CARD, fg=PRIMARY, font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=10, pady=(8, 2))
        
        video_ids_box_frame = tk.Frame(data_frame, bg="#F0F0F0", relief="solid", bd=1)
        video_ids_box_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=(0, 10), ipady=0)
        
        self.video_ids_box = ScrolledText(
            video_ids_box_frame,
            font=("Consolas", 9),
            height=8,
            bg="#FFFFFF",
            fg="#000000",
            relief="flat",
            bd=0,
            insertbackground=PRIMARY,
            highlightthickness=0,
            wrap="word"
        )
        self.video_ids_box.pack(fill="both", expand=True, padx=8, pady=8)
        self.video_ids_box.insert("1.0", "2036\n2037\n2038")

        # Status & Notes (below orders/video IDs)
        tk.Label(data_frame, text="Status & Notes", bg=CARD, fg=PRIMARY, font=("Segoe UI", 9, "bold")).grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 2))
        
        notes_box_frame = tk.Frame(data_frame, bg="#F0F0F0", relief="solid", bd=1)
        notes_box_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
        
        self.notes_box = ScrolledText(
            notes_box_frame,
            font=("Consolas", 8),
            height=3,
            bg="#FFFFFF",
            fg=TEXT,
            relief="flat",
            bd=0,
            insertbackground=PRIMARY,
            highlightthickness=0,
            wrap="word",
            state="disabled"
        )
        self.notes_box.pack(fill="both", expand=True, padx=8, pady=8)
        self.write_note("Ready. Configure paths and click 'CREATE & COPY'.")

        self.missing_orders_box = ScrolledText(
            notes_box_frame,
            font=("Consolas", 8),
            height=0,
            bg="#FFFFFF",
            fg=TEXT,
            relief="flat",
            bd=0,
            state="disabled"
        )

        # ===== ACTION BUTTONS =====
        actions_frame = tk.Frame(main_frame, bg=BG)
        actions_frame.pack(fill="x", pady=(0, 8))

        self.create_button(actions_frame, "✓ CREATE & COPY", self.create_folders_with_video, PRIMARY, width=20).pack(side="left", padx=(0, 5))
        self.create_button(actions_frame, "📂 OPEN", self.open_location, ACCENT, width=15).pack(side="left")

        # ===== PROGRESS & LOG =====
        progress_frame = tk.Frame(main_frame, bg=CARD, relief="flat", bd=0)
        progress_frame.pack(fill="both", expand=True)
        progress_frame.config(highlightthickness=1, highlightbackground=LIGHT_BORDER)

        tk.Label(progress_frame, text="Status & Log", bg=CARD, fg=PRIMARY, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 3))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Compact.Horizontal.TProgressbar", background=PRIMARY, troughcolor="#E0E0E0", bordercolor="white", lightcolor=PRIMARY, darkcolor=PRIMARY)
        
        self.progress = ttk.Progressbar(progress_frame, style="Compact.Horizontal.TProgressbar", mode='determinate', length=300)
        self.progress.pack(fill="x", padx=10, pady=(0, 3))

        self.status = tk.Label(progress_frame, text="🟢 Ready", bg=CARD, fg="#4CAF50", anchor="w", font=("Segoe UI", 8, "bold"))
        self.status.pack(fill="x", padx=10, pady=(0, 5))

        log_frame = tk.Frame(progress_frame, bg="#FAFAFA", relief="solid", bd=1)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log = ScrolledText(
            log_frame,
            height=4,
            font=("Consolas", 8),
            bg="#FAFAFA",
            fg=TEXT,
            relief="flat",
            bd=0,
            insertbackground=PRIMARY,
            highlightthickness=0
        )
        self.log.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Animate initial state
        self.root.after(500, lambda: self.animate_status_text("🟢 Ready", "#4CAF50"))

    def set_today(self):
        today = datetime.now()
        formatted_date = today.strftime("%m-%d-%y")
        self.date_var.set(formatted_date)
        self.write_log(f"📅 Date set to: {formatted_date}")

    def browse_destination(self):
        folder = filedialog.askdirectory()
        if folder:
            self.destination.set(folder)
            self.write_log(f"✓ Destination: {os.path.basename(folder)}")

    def browse_video_source(self):
        folder = filedialog.askdirectory()
        if folder:
            self.video_source.set(folder)
            self.write_log(f"✓ Video source: {os.path.basename(folder)}")

    def browse_images_source(self):
        folder = filedialog.askdirectory(title="Select images folder")
        if folder:
            self.images_source.set(folder)
            self.write_log(f"✓ Images source: {os.path.basename(folder)}")

    def write_log(self, text):
        """Write to log with smooth animation"""
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="normal")
        self.root.update_idletasks()

    def write_note(self, text):
        """Write note with smooth animation"""
        self.notes_box.config(state="normal")
        self.notes_box.insert("end", text + "\n")
        self.notes_box.see("end")
        self.notes_box.config(state="disabled")
        self.root.update_idletasks()

    def write_missing_order(self, order, reason=None):
        self.missing_orders_box.config(state="normal")
        if reason:
            self.missing_orders_box.insert("end", f"{order} — {reason}\n")
        else:
            self.missing_orders_box.insert("end", f"{order}\n")
        self.missing_orders_box.see("end")
        self.missing_orders_box.config(state="disabled")

    def validate_date(self, date_str):
        try:
            datetime.strptime(date_str, "%m-%d-%y")
            return True
        except ValueError:
            return False

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
        images_source = self.images_source.get().strip()
        date_input = self.date_var.get().strip()

        if not destination:
            messagebox.showerror("Error", "Select a destination folder.")
            return

        if not os.path.exists(destination):
            messagebox.showerror("Error", "Destination folder does not exist.")
            return

        if not video_source and not images_source:
            messagebox.showerror("Error", "Select a video or images source folder.")
            return

        if video_source and not os.path.exists(video_source):
            messagebox.showerror("Error", "Video source folder does not exist.")
            return

        if images_source and not os.path.exists(images_source):
            messagebox.showerror("Error", "Images source folder does not exist.")
            return

        if not date_input:
            messagebox.showerror("Error", "Enter a date (MM-DD-YY format).")
            return

        if not self.validate_date(date_input):
            messagebox.showerror("Error", f"Invalid date format.\nPlease use: MM-DD-YY\nExample: 06-03-26")
            return

        orders = [
            x.strip()
            for x in self.order_box.get("1.0", "end").splitlines()
            if x.strip() and not x.strip().startswith("📋")
        ]

        video_ids = [
            x.strip()
            for x in self.video_ids_box.get("1.0", "end").splitlines()
            if x.strip() and not x.strip().startswith("🎬")
        ]

        if not orders:
            messagebox.showerror("Error", "Enter at least one order number.")
            return

        # track per-order status
        order_status = {o: {"video_copied": False, "images_added": False} for o in orders}

        has_no_video_ids = not bool(video_ids)
        extra_video_ids = []
        if len(video_ids) > len(orders):
            extra_video_ids = video_ids[len(orders):]
            video_ids = video_ids[:len(orders)]

        remaining_order_video_pairs = list(zip(orders, video_ids))

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
        self.write_log(f"🖼️ Images source: {images_source}")
        self.write_log(f"📊 Orders: {len(orders)}\n")

        if has_no_video_ids and not images_source:
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
        images_copied = 0
        image_copy_errors = []

        try:
            date_folder = os.path.join(destination, date_input)
            os.makedirs(date_folder, exist_ok=True)
            self.write_log(f"✓ Created date folder: {date_input}\n")

            # First pass: create all order folders and BEFORE SHIPPING / UPON RETURNS
            for i, (order, video_id) in enumerate(zip(orders, video_ids_extended), start=1):
                try:
                    order_folder = os.path.join(date_folder, order)
                    before_shipping = os.path.join(order_folder, "BEFORE SHIPPING")
                    os.makedirs(before_shipping, exist_ok=True)

                    self.write_log(f"  ├─ {order}/")
                    self.write_log(f"  │  ├─ BEFORE SHIPPING/")

                    if video_id:
                        video_file = self.find_video_file(video_id, video_source)
                        if video_file:
                            try:
                                destination_path = os.path.join(before_shipping, os.path.basename(video_file))
                                if os.path.exists(destination_path):
                                    self.write_log(f"  │  │  ✓ Video already exists: {os.path.basename(video_file)}")
                                else:
                                    shutil.copy2(video_file, destination_path)
                                    self.write_log(f"  │  │  ✓ Copied: {os.path.basename(video_file)}")
                                    videos_found += 1
                                # mark video copied for this order
                                order_status[order]["video_copied"] = True
                            except Exception as e:
                                self.write_log(f"  │  │  ✗ Failed to copy video: {str(e)}")
                                self.write_note(f"Order {order}: failed to copy video ID {video_id}.")
                                self.write_missing_order(order, f"failed video copy")
                                missing_orders_numbers.append(order)
                                videos_missing += 1
                        else:
                            self.write_log(f"  │  │  ⚠️  Video ID '{video_id}' not found in source folder")
                            self.write_note(f"Order {order}: video ID '{video_id}' not found.")
                            self.write_missing_order(order, f"missing video ID")
                            missing_orders_numbers.append(order)
                            videos_missing += 1
                    elif video_source:
                        self.write_log(f"  │  │  ⚠️  No Video ID provided for order {order}.")
                        self.write_note(f"Order {order}: created without a matching Video ID.")
                        self.write_missing_order(order, "no Video ID provided")
                        missing_orders_numbers.append(order)

                    upon_returns = os.path.join(order_folder, "UPON RETURNS")
                    os.makedirs(upon_returns, exist_ok=True)
                    self.write_log(f"  │  └─ UPON RETURNS/")

                    self.animate_progress_smooth(i, 100)
                    self.animate_status_text(f"🔄 Processing {i}/{len(orders)}...", "#F57C00")
                    self.root.update_idletasks()

                except Exception as e:
                    error_msg = f"✗ Failed to create {order}: {str(e)}"
                    self.write_log(error_msg)
                    errors.append(error_msg)

            # callback when an order is completed (both video_copied and images_added)
            def on_order_completed(order_done):
                # remove the completed order from the Orders text box (exact match)
                current = [x.strip() for x in self.order_box.get("1.0", "end").splitlines() if x.strip()]
                new_order_list = [x for x in current if x != order_done]
                self.order_box.delete("1.0", "end")
                if new_order_list:
                    self.order_box.insert("1.0", "\n".join(new_order_list))

                # remove the completed order from the remaining pairs and rebuild the video IDs box
                nonlocal remaining_order_video_pairs
                remaining_order_video_pairs = [pair for pair in remaining_order_video_pairs if pair[0] != order_done]
                new_video_ids = [pair[1] for pair in remaining_order_video_pairs]
                self.video_ids_box.delete("1.0", "end")
                if new_video_ids:
                    self.video_ids_box.insert("1.0", "\n".join(new_video_ids))

                self.write_log(f"Order {order_done} completed and removed from Orders box.")

            # After creating all folders, if images_source is set, open a compact dialog
            # that lets the user pick which order(s) to open the image picker for.
            if images_source:
                pick_images_for_orders_dialog_compact(self.root, orders, images_source, date_folder,
                                                      order_status, on_order_completed, logger=self.write_log)

            self.animate_status_text("✅ Completed Successfully", "#2E7D32")
            self.animate_progress_smooth(len(orders), 200)

            if missing_orders_numbers:
                seen = []
                for o in missing_orders_numbers:
                    if o not in seen:
                        seen.append(o)
                self.write_note("Orders without copied videos: " + ", ".join(seen))
                self.missing_orders_box.config(state="normal")
                self.missing_orders_box.delete("1.0", "end")
                for o in seen:
                    self.missing_orders_box.insert("end", f"{o}\n")
                self.missing_orders_box.config(state="disabled")

            self.write_log(f"\n{'='*50}")

            if errors or image_copy_errors:
                self.write_log(f"⚠️  Completed with {len(errors) + len(image_copy_errors)} issue(s)")
                messagebox.showwarning(
                    "Completed with issues",
                    f"Completed with {len(errors) + len(image_copy_errors)} issue(s). Check the activity log."
                )
            else:
                messagebox.showinfo("Completed", "All orders processed successfully.")

        except Exception as e:
            messagebox.showerror("Fatal error", str(e))
            self.write_log(f"✗ Fatal error: {str(e)}")

    def open_location(self):
        dest = self.destination.get().strip()
        if not dest or not os.path.exists(dest):
            messagebox.showerror("Error", "Destination folder not set or does not exist.")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(dest)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", dest])
            else:
                subprocess.Popen(["xdg-open", dest])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = KBMCApp(root)
    root.mainloop()
