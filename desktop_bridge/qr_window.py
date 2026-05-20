from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Callable
from pathlib import Path

import qrcode
from PIL import Image, ImageTk


class QRWindow:
    def __init__(self, on_retry: Callable[[], None] | None = None, app_icon_path: str | None = None) -> None:
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._on_retry = on_retry
        self._app_icon_path = app_icon_path
        self._tk_icon_ref = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._ui_thread, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def show(self, url: str) -> None:
        self._queue.put(("show", url))

    def show_loading(self, message: str = "QR kod hazirlaniyor...") -> None:
        self._queue.put(("loading", message))

    def copy_to_clipboard(self, url: str) -> None:
        self._queue.put(("copy", url))

    def show_error(self, message: str) -> None:
        self._queue.put(("error", message))

    def show_startup_info(self, image_path: str, title: str = "Uygulama Hazir", note: str = "") -> None:
        self._queue.put(("startup", f"{title}|{image_path}|{note}"))

    def _ui_thread(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self._apply_icon(self.root)
        self.current_window: tk.Toplevel | None = None
        self._ready.set()

        def poll_queue() -> None:
            try:
                while True:
                    action, value = self._queue.get_nowait()
                    if action == "show":
                        self._show_now(value)
                    elif action == "loading":
                        self._show_loading_now(value)
                    elif action == "copy":
                        self.root.clipboard_clear()
                        self.root.clipboard_append(value)
                    elif action == "error":
                        self._show_error_now(value)
                    elif action == "startup":
                        parts = value.split("|", 2)
                        win_title = parts[0] if parts else "Uygulama Hazir"
                        img_path = parts[1] if len(parts) > 1 else ""
                        note = parts[2] if len(parts) > 2 else ""
                        self._show_startup_now(win_title, img_path, note)
            except queue.Empty:
                pass
            self.root.after(120, poll_queue)

        self.root.after(120, poll_queue)
        self.root.mainloop()

    def _show_now(self, url: str) -> None:
        if self.current_window and self.current_window.winfo_exists():
            self.current_window.destroy()

        window = tk.Toplevel(self.root)
        window.title("GameMode1 - Telefon QR")
        self._apply_icon(window)
        self._center_window(window, 360, 460)
        window.resizable(False, False)

        qr_img = qrcode.make(url).convert("RGB").resize((260, 260), Image.Resampling.NEAREST)
        tk_img = ImageTk.PhotoImage(qr_img)

        label_img = tk.Label(window, image=tk_img)
        label_img.image = tk_img
        label_img.pack(pady=16)

        label_url = tk.Label(window, text=url, wraplength=320, justify="center")
        label_url.pack(pady=8)

        info = tk.Label(window, text="Bu bağlantıyı sadece kendi cihazınızla paylaşın.", fg="#b00020")
        info.pack(pady=4)

        def copy_url() -> None:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("Kopyalandı", "Bağlantı panoya kopyalandı.")

        copy_button = tk.Button(window, text="URL'yi Kopyala", command=copy_url)
        copy_button.pack(pady=12)

        self.current_window = window

    def _show_loading_now(self, message: str) -> None:
        if self.current_window and self.current_window.winfo_exists():
            self.current_window.destroy()

        window = tk.Toplevel(self.root)
        window.title("GameMode1 - Telefon QR")
        self._apply_icon(window)
        self._center_window(window, 360, 220)
        window.resizable(False, False)

        title = tk.Label(window, text="QR Hazirlaniyor", font=("Segoe UI", 14, "bold"))
        title.pack(pady=(28, 8))

        body = tk.Label(window, text=message, wraplength=320, justify="center")
        body.pack(pady=(4, 12))

        hint = tk.Label(window, text="Bu islem tunnel olusumuna gore biraz surebilir.", fg="#666666", wraplength=320, justify="center")
        hint.pack(pady=(0, 8))

        self.current_window = window

    def _show_error_now(self, message: str) -> None:
        if self.current_window and self.current_window.winfo_exists():
            self.current_window.destroy()

        window = tk.Toplevel(self.root)
        window.title("GameMode1 - Telefon QR")
        self._apply_icon(window)
        self._center_window(window, 380, 250)
        window.resizable(False, False)

        title = tk.Label(window, text="QR Link Olusturulamadi", font=("Segoe UI", 13, "bold"), fg="#b00020")
        title.pack(pady=(20, 8))

        body = tk.Label(window, text=message, wraplength=340, justify="center")
        body.pack(pady=(4, 16))

        btn_row = tk.Frame(window)
        btn_row.pack(pady=(0, 8))

        def retry() -> None:
            if not self._on_retry:
                return
            threading.Thread(target=self._on_retry, daemon=True).start()

        retry_btn = tk.Button(btn_row, text="Tekrar Dene", width=14, command=retry)
        retry_btn.pack(side=tk.LEFT, padx=6)

        close_btn = tk.Button(btn_row, text="Kapat", width=10, command=window.destroy)
        close_btn.pack(side=tk.LEFT, padx=6)

        self.current_window = window

    def _show_startup_now(self, title_text: str, image_path: str, note: str) -> None:
        if self.current_window and self.current_window.winfo_exists():
            self.current_window.destroy()

        window = tk.Toplevel(self.root)
        window.title("GameMode1")
        self._apply_icon(window)
        self._center_window(window, 420, 340)
        window.resizable(False, False)

        title = tk.Label(window, text=title_text, font=("Segoe UI", 13, "bold"))
        title.pack(pady=(12, 8))

        image_label = tk.Label(window)
        image_label.pack(pady=(4, 10))

        try:
            img = Image.open(image_path).convert("RGB")
            img.thumbnail((380, 210), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            image_label.configure(image=tk_img)
            image_label.image = tk_img
        except Exception:
            image_label.configure(text="Gorsel yuklenemedi.")

        default_note = "Uygulama acildi. Sistem tepsisinde gorebilirsiniz."
        if note.strip():
            default_note = f"{default_note}\n\n{note.strip()}"
        hint = tk.Label(window, text=default_note, wraplength=380, justify="center")
        hint.pack(pady=(0, 10))

        ok_btn = tk.Button(window, text="Tamam", width=14, command=window.destroy)
        ok_btn.pack(pady=(0, 12))

        self.current_window = window

    def _center_window(self, window: tk.Toplevel, width: int, height: int) -> None:
        window.update_idletasks()
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        x = max((screen_w - width) // 2, 0)
        y = max((screen_h - height) // 2, 0)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def _apply_icon(self, window: tk.Misc) -> None:
        path = (self._app_icon_path or "").strip()
        if not path:
            return
        p = Path(path)
        if not p.exists():
            return
        try:
            if p.suffix.lower() == ".ico":
                window.iconbitmap(default=str(p))
                return
        except Exception:
            pass
        try:
            img = Image.open(str(p))
            self._tk_icon_ref = ImageTk.PhotoImage(img)
            window.iconphoto(True, self._tk_icon_ref)
        except Exception:
            pass
