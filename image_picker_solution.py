# image_picker_solution.py
import os
import shutil
import threading
import queue
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

PRIMARY = "#C41E3A"
ACCENT = "#E74C3C"
BG = "#F5F5F5"
CARD = "#FFFFFF"
TEXT = "#333333"
SECONDARY_TEXT = "#666666"
LIGHT_BORDER = "#E0E0E0"


class ImagePickerDialog:
    """
    Optimized image picker:
      - tiles hosted as canvas windows for fast hit testing
      - threaded thumbnail loader (non-blocking UI)
      - throttled drag updates and auto-scroll
    """

    def __init__(self, parent, source_folder, order_number, move_callback=None, debug=False):
        self.parent = parent
        self.source_folder = source_folder
        self.order_number = order_number
        self.move_callback = move_callback
        self.debug = debug

        self.selected_images = []
        self.image_list = []
        self.image_tiles = {}      # filename -> (tile_widget, canvas_item_id)
        self.image_thumbs = {}     # filename -> PhotoImage or None
        self.image_checkmarks = {}
        self.selected_set = set()

        # drag state
        self.drag_start = None
        self.is_dragging = False
        self.pre_drag_state = set()
        self.ctrl_held = False
        self._last_drag_update = 0.0

        # thumbnail worker
        self._thumb_queue = queue.Queue()
        self._thumb_worker = None
        self._stop_worker = False

        # auto-scroll
        self._auto_scroll_speed = 0
        self._auto_scrolling = False

        # drag rectangle overlay id
        self._drag_rect_id = None

        # build dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Select Images for Order {order_number}")
        self.dialog.geometry("900x600")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel_pressed)

        # center over parent (best-effort)
        self._center_over_parent()

        self._build_ui()
        parent.wait_window(self.dialog)

    def _center_over_parent(self):
        """Center this dialog over the parent window (best-effort)."""
        try:
            self.dialog.update_idletasks()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            w = self.dialog.winfo_width()
            h = self.dialog.winfo_height()
            if pw <= 1 and ph <= 1:
                screen_w = self.dialog.winfo_screenwidth()
                screen_h = self.dialog.winfo_screenheight()
                x = (screen_w - w) // 2
                y = (screen_h - h) // 2
            else:
                x = px + max(0, (pw - w) // 2)
                y = py + max(0, (ph - h) // 2)
            self.dialog.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self):
        header = tk.Frame(self.dialog, bg=PRIMARY, height=56)
        header.pack(fill="x")
        tk.Label(header, text=f"📸 Select Images — {self.order_number}",
                 bg=PRIMARY, fg="white", font=("Segoe UI", 11, "bold"),
                 padx=12, pady=8).pack(anchor="w")

        tk.Label(self.dialog, text=f"Source: {self.source_folder}  •  Click to select • Drag to multi-select",
                 bg=BG, fg=TEXT, font=("Segoe UI", 9), padx=10, pady=6,
                 justify="left").pack(fill="x")

        btns = tk.Frame(self.dialog, bg=BG)
        btns.pack(fill="x", padx=8, pady=(4, 6))
        tk.Button(btns, text="✓ All", command=self.select_all,
                  bg="#2E7D32", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=8, pady=4, cursor="hand2").pack(side="left", padx=4)
        tk.Button(btns, text="✗ None", command=self.deselect_all,
                  bg=ACCENT, fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=8, pady=4, cursor="hand2").pack(side="left", padx=4)
        tk.Button(btns, text="Refresh", command=self.populate_images,
                  bg="#F57C00", fg="white", font=("Segoe UI", 9),
                  relief="flat", padx=8, pady=4, cursor="hand2").pack(side="left", padx=4)

        grid_frame = tk.Frame(self.dialog, bg=CARD, highlightthickness=1, highlightbackground=LIGHT_BORDER)
        grid_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.canvas = tk.Canvas(grid_frame, bg=CARD, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(grid_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # inner frame only for scrollregion anchoring
        self.inner = tk.Frame(self.canvas, bg=CARD)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Mouse wheel scroll
        def on_scroll(e):
            self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        self.canvas.bind("<MouseWheel>", on_scroll)

        # Drag detection on canvas
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._end_drag)

        # Status
        self.status_label = tk.Label(self.dialog, text="0 images selected",
                                     bg=BG, fg=TEXT, font=("Segoe UI", 9, "bold"),
                                     padx=8, pady=6)
        self.status_label.pack(fill="x")

        # Footer
        footer = tk.Frame(self.dialog, bg=CARD)
        footer.pack(fill="x", padx=8, pady=8)
        tk.Button(footer, text="Cancel", command=self.cancel_pressed,
                  bg="#999999", fg="white", font=("Segoe UI", 9),
                  relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right", padx=6)
        tk.Button(footer, text="OK", command=self.ok_pressed,
                  bg=PRIMARY, fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=14, pady=6, cursor="hand2").pack(side="right", padx=6)

        self.populate_images()

    def populate_images(self):
        """Create tiles as canvas windows and start threaded thumbnail loader"""
        # clear existing canvas items and inner children
        for fn, val in list(self.image_tiles.items()):
            tile, item_id = val
            try:
                self.canvas.delete(item_id)
            except Exception:
                pass
        for w in self.inner.winfo_children():
            w.destroy()

        self.image_list = []
        self.image_tiles = {}
        self.image_thumbs = {}
        self.image_checkmarks = {}
        self.selected_set = set()

        allowed = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
        try:
            files = sorted([f for f in os.listdir(self.source_folder)
                            if os.path.isfile(os.path.join(self.source_folder, f))])
        except Exception:
            files = []

        images = [f for f in files if Path(f).suffix.lower() in allowed]

        if not images:
            tk.Label(self.inner, text="📁 No images found", bg=CARD,
                     fg=SECONDARY_TEXT, font=("Segoe UI", 12)).pack(pady=40)
            self.dialog.update_idletasks()
            return

        self.image_list = images

        # Create placeholder tiles and place them as canvas windows
        cols = 4
        tile_w, tile_h = 190, 200
        h_spacing, v_spacing = 10, 10
        for idx, fn in enumerate(images):
            row = idx // cols
            col = idx % cols

            # Tile frame as child of canvas (avoid inner->canvas mismatch)
            tile = tk.Frame(self.canvas, bg=CARD, bd=2, relief="solid",
                            highlightthickness=2, highlightbackground=LIGHT_BORDER,
                            width=tile_w, height=tile_h)
            tile.grid_propagate(False)

            # Placeholder image label (we'll update image when thumbnail ready)
            img_label = tk.Label(tile, text="⏳", bg=CARD, fg=SECONDARY_TEXT,
                                 font=("Segoe UI", 20), cursor="hand2")
            img_label.pack(padx=8, pady=8)

            # Filename
            name_label = tk.Label(tile, text=fn[:25], bg=CARD, fg=TEXT,
                                  font=("Segoe UI", 7), wraplength=170, justify="center")
            name_label.pack(padx=4, pady=(0, 4), fill="x")

            # Checkmark (hidden initially)
            checkmark = tk.Label(tile, text="✓", bg=PRIMARY, fg="white",
                                 font=("Segoe UI", 24, "bold"), width=2, height=1)
            self.image_checkmarks[fn] = checkmark

            # Bind clicks to tile and children
            for widget in (tile, img_label, name_label):
                widget.bind("<Button-1>", lambda e, n=fn: self._click_image(n, e), add="+")

            # compute center positions for canvas.create_window
            x = col * (tile_w + h_spacing) + h_spacing + tile_w // 2
            y = row * (tile_h + v_spacing) + v_spacing + tile_h // 2
            item_id = self.canvas.create_window(x, y, window=tile, anchor="center")
            self.image_tiles[fn] = (tile, item_id)

            # store placeholder thumb (None for now)
            self.image_thumbs[fn] = None

            # initial tile appearance
            self._update_tile(fn)

        # finalize geometry and scrollregion
        self.dialog.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        # start threaded thumbnail loader
        self._start_thumbnail_worker()

        self.update_status()

    # ---------------- threaded thumbnail loader ----------------
    def _start_thumbnail_worker(self):
        if self._thumb_worker and self._thumb_worker.is_alive():
            return

        def worker(image_files, src_folder, q, stop_flag):
            for fn in image_files:
                if stop_flag():
                    break
                try:
                    path = os.path.join(src_folder, fn)
                    img = Image.open(path)
                    resample = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS
                    if img.mode not in ('RGB', 'RGBA', 'L'):
                        img = img.convert('RGB')
                    img.thumbnail((150, 150), resample)
                    q.put((fn, img))
                except Exception:
                    q.put((fn, None))
            q.put((None, None))  # sentinel

        self._stop_worker = False
        files = list(self.image_list)
        self._thumb_worker = threading.Thread(
            target=worker,
            args=(files, self.source_folder, self._thumb_queue, lambda: self._stop_worker),
            daemon=True
        )
        self._thumb_worker.start()
        self._process_thumb_queue()

    def _process_thumb_queue(self):
        try:
            while True:
                fn, pil_img = self._thumb_queue.get_nowait()
                if fn is None:
                    break
                if pil_img is None:
                    self.image_thumbs[fn] = None
                else:
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self.image_thumbs[fn] = tk_img
                    # update tile image if tile exists
                    val = self.image_tiles.get(fn)
                    if val:
                        tile, item_id = val
                        # find the image label (first child is the label we created)
                        for child in tile.winfo_children():
                            if isinstance(child, tk.Label) and getattr(child, "image", None) is None:
                                child.config(image=tk_img, text="")
                                child.image = tk_img  # keep reference
                                break
        except queue.Empty:
            pass

        if self._thumb_worker and self._thumb_worker.is_alive():
            self.dialog.after(80, self._process_thumb_queue)
        else:
            # final drain
            try:
                while True:
                    fn, pil_img = self._thumb_queue.get_nowait()
                    if fn is None:
                        break
            except queue.Empty:
                pass

    # ---------------- selection helpers ----------------
    def _click_image(self, filename, event):
        if self.is_dragging:
            return

        if filename in self.selected_set:
            self.selected_set.remove(filename)
        else:
            self.selected_set.add(filename)

        self._update_tile(filename)
        self.update_status()

    def _start_drag(self, event):
        self.drag_start = (event.x, event.y)
        self.is_dragging = False
        self.ctrl_held = (event.state & 0x4) != 0
        if self.ctrl_held:
            self.pre_drag_state = set(self.selected_set)
        else:
            self.pre_drag_state = set()

    def _on_drag(self, event):
        if not self.drag_start:
            return

        dx = abs(event.x - self.drag_start[0])
        dy = abs(event.y - self.drag_start[1])
        if dx < 8 and dy < 8:
            return

        # throttle to ~20 FPS
        now = time.time()
        if now - self._last_drag_update < 0.05:
            # still schedule auto-scroll update
            self._maybe_start_auto_scroll(event)
            return
        self._last_drag_update = now

        self.is_dragging = True
        self._maybe_start_auto_scroll(event)

        # convert drag coords to canvas coords
        x1 = self.canvas.canvasx(self.drag_start[0])
        y1 = self.canvas.canvasy(self.drag_start[1])
        x2 = self.canvas.canvasx(event.x)
        y2 = self.canvas.canvasy(event.y)
        rect_x1, rect_x2 = (x1, x2) if x1 < x2 else (x2, x1)
        rect_y1, rect_y2 = (y1, y2) if y1 < y2 else (y2, y1)

        # draw/update drag rectangle overlay
        if self._drag_rect_id:
            self.canvas.coords(self._drag_rect_id, rect_x1, rect_y1, rect_x2, rect_y2)
        else:
            self._drag_rect_id = self.canvas.create_rectangle(rect_x1, rect_y1, rect_x2, rect_y2,
                                                              outline="#1976D2", width=2, dash=(4,2), tags="dragrect")

        # fast overlap test using canvas.find_overlapping
        overlapping = set(self.canvas.find_overlapping(rect_x1, rect_y1, rect_x2, rect_y2))
        new_selected = set(self.pre_drag_state)

        # check each tile's canvas item id
        for fn, (tile, item_id) in self.image_tiles.items():
            if item_id in overlapping:
                new_selected.add(fn)

        # update only changed tiles
        added = new_selected - self.selected_set
        removed = self.selected_set - new_selected
        self.selected_set = new_selected

        for fn in added:
            self._update_tile(fn)
        for fn in removed:
            self._update_tile(fn)

        self.update_status()

    def _end_drag(self, event):
        self.is_dragging = False
        self.drag_start = None
        # remove drag rect after short delay so user sees final selection
        if self._drag_rect_id:
            self.dialog.after(200, lambda: (self.canvas.delete(self._drag_rect_id), setattr(self, "_drag_rect_id", None)))
        # stop auto-scroll
        self._auto_scroll_speed = 0
        self._auto_scrolling = False

    def _update_tile(self, filename):
        """Update tile appearance - VERY VISIBLE SELECTION"""
        val = self.image_tiles.get(filename)
        if not val:
            return
        tile, item_id = val
        is_selected = filename in self.selected_set

        if is_selected:
            tile.config(bg="#E8F5E9", highlightbackground=PRIMARY,
                        highlightcolor=PRIMARY, relief="solid", bd=3)
            checkmark = self.image_checkmarks[filename]
            checkmark.place(in_=tile, relx=0.95, rely=0.05, anchor="ne")
        else:
            tile.config(bg=CARD, highlightbackground=LIGHT_BORDER,
                        highlightcolor=LIGHT_BORDER, relief="solid", bd=2)
            checkmark = self.image_checkmarks[filename]
            checkmark.place_forget()

    def select_all(self):
        self.selected_set = set(self.image_list)
        for fn in self.image_list:
            self._update_tile(fn)
        self.update_status()

    def deselect_all(self):
        self.selected_set.clear()
        for fn in self.image_list:
            self._update_tile(fn)
        self.update_status()

    def update_status(self):
        count = len(self.selected_set)
        total = len(self.image_list)
        self.status_label.config(text=f"✓ {count} of {total} images selected")

    # ---------------- auto-scroll ----------------
    def _maybe_start_auto_scroll(self, event):
        canvas_h = self.canvas.winfo_height()
        margin = 40
        speed = 0
        if event.y < margin:
            speed = -3
        elif event.y > canvas_h - margin:
            speed = 3

        self._auto_scroll_speed = speed
        if speed != 0 and not self._auto_scrolling:
            self._auto_scrolling = True
            self._auto_scroll_step()

    def _auto_scroll_step(self):
        if not self._auto_scrolling:
            return
        speed = getattr(self, "_auto_scroll_speed", 0)
        if speed != 0:
            self.canvas.yview_scroll(speed, "units")
            self.canvas.after(30, self._auto_scroll_step)
        else:
            self._auto_scrolling = False

    # ---------------- OK / Cancel ----------------
    def ok_pressed(self):
        sel = list(self.selected_set)
        # stop worker
        self._stop_worker = True

        if self.move_callback and sel:
            try:
                self.move_callback(sel)
            except Exception:
                pass

        self.selected_images = sel
        self.dialog.destroy()

    def cancel_pressed(self):
        # stop worker
        self._stop_worker = True
        self.selected_images = []
        self.dialog.destroy()


def copy_selected_images_for_order(order_number: str, source_folder: str,
                                   dest_before_shipping: str, parent_window) -> tuple:
    """
    Open picker and move selected images. Returns (moved_count, errors).
    Place this function at module level so other modules can import it.
    """
    errors = []
    count = 0

    if not os.path.exists(source_folder):
        return 0, [f"Source folder not found: {source_folder}"]
    if not os.path.exists(dest_before_shipping):
        return 0, [f"Destination folder not found: {dest_before_shipping}"]

    def move_now(selected_files):
        nonlocal count, errors
        os.makedirs(dest_before_shipping, exist_ok=True)
        for fn in selected_files:
            try:
                src = os.path.join(source_folder, fn)
                dst = os.path.join(dest_before_shipping, fn)
                if os.path.exists(src):
                    shutil.move(src, dst)
                    count += 1
                else:
                    errors.append(f"Source file not found: {fn}")
            except Exception as e:
                errors.append(f"Failed to move {fn}: {e}")

    picker = ImagePickerDialog(parent_window, source_folder, order_number, move_callback=move_now)

    # fallback: if picker returned selected_images but move_now didn't run (count==0), try moving now
    if getattr(picker, "selected_images", None) and count == 0:
        for fn in picker.selected_images:
            src = os.path.join(source_folder, fn)
            dst = os.path.join(dest_before_shipping, fn)
            if os.path.exists(src):
                try:
                    shutil.move(src, dst)
                    count += 1
                except Exception as e:
                    errors.append(f"Failed to move {fn}: {e}")

    return count, errors
