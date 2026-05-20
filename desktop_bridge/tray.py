from __future__ import annotations

import threading
import traceback
from pathlib import Path
from typing import Callable

import pystray
from PIL import Image, ImageDraw


class TrayController:
    def __init__(
        self,
        icon_path: Path,
        on_show_qr: Callable[[], None],
        on_toggle_startup: Callable[[], None],
        startup_enabled_getter: Callable[[], bool],
        notify: Callable[[str, str], None],
        on_restart: Callable[[], None],
        on_exit: Callable[[], None],
        on_download_apk: Callable[[], None] | None = None,
    ) -> None:
        self.icon_path = icon_path
        self.startup_enabled_getter = startup_enabled_getter
        self._icon = pystray.Icon(
            "GameMode1",
            self._load_image(),
            "GameMode1",
            self._build_menu(
                on_show_qr,
                on_toggle_startup,
                notify,
                on_restart,
                on_exit,
                on_download_apk,
            ),
        )

    def _load_image(self) -> Image.Image:
        if self.icon_path.exists():
            try:
                return Image.open(self.icon_path)
            except OSError:
                pass
        img = Image.new("RGBA", (64, 64), (236, 86, 166, 255))
        draw = ImageDraw.Draw(img)
        draw.ellipse((10, 10, 54, 54), fill=(255, 255, 255, 255))
        return img

    @staticmethod
    def _safe_run(fn: Callable[[], None]) -> Callable[..., None]:
        def wrapped(*args: object) -> None:
            def runner() -> None:
                try:
                    fn()
                except Exception:
                    traceback.print_exc()
                finally:
                    # Ensure checked menu item states (e.g. startup tick) refresh immediately.
                    if args:
                        icon = args[0]
                        update_menu = getattr(icon, "update_menu", None)
                        if callable(update_menu):
                            try:
                                update_menu()
                            except Exception:
                                pass

            threading.Thread(target=runner, daemon=True).start()

        return wrapped

    def _build_menu(
        self,
        on_show_qr: Callable[[], None],
        on_toggle_startup: Callable[[], None],
        notify: Callable[[str, str], None],
        on_restart: Callable[[], None],
        on_exit: Callable[[], None],
        on_download_apk: Callable[[], None] | None = None,
    ) -> pystray.Menu:
        items = [
            pystray.MenuItem("Telefon Icin QR Kod Goster", self._safe_run(on_show_qr)),
        ]
        if on_download_apk:
            items.append(pystray.MenuItem("Mobil Uygulamayi Indir", self._safe_run(on_download_apk)))
        items.extend([
            pystray.MenuItem(
                "Baslangicta Calistir",
                self._safe_run(on_toggle_startup),
                checked=lambda _: self.startup_enabled_getter(),
            ),
            pystray.MenuItem("Yeniden Baslat", self._safe_run(on_restart)),
            pystray.MenuItem("Cikis", self._safe_run(on_exit)),
        ])
        return pystray.Menu(*items)

    def run(self) -> None:
        self._icon.run()

    def run_async(self) -> None:
        threading.Thread(target=self.run, daemon=True).start()

    def stop(self) -> None:
        self._icon.stop()

    def notify(self, title: str, message: str) -> None:
        try:
            self._icon.notify(message, title=title)
        except Exception:
            pass
