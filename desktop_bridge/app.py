from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from urllib.parse import quote
import ctypes

import httpx
import uvicorn

from .process_manager import ProcessManager
from .qr_window import QRWindow
from .security import token_manager
from .settings import AppSettings
from .startup import is_startup_enabled, set_startup_enabled
from .tray import TrayController
from .tunnel_manager import TunnelManager


class DesktopBridgeApp:
    def __init__(self, settings: AppSettings) -> None:
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GameMode1.bridge")
        except Exception:
            pass
        self.settings = settings
        root = Path(__file__).resolve().parent.parent
        cloudflared = os.environ.get("LOL_BRIDGE_CLOUDFLARED_PATH", str(root / "cloudflared.exe"))
        tunnel_name = os.environ.get("LOL_BRIDGE_TUNNEL_NAME") or None
        self.tunnel = TunnelManager(cloudflared_path=cloudflared, target_url=f"http://127.0.0.1:{settings.backend_port}", tunnel_name=tunnel_name)

        icon_abs = Path(settings.icon_path)
        if not icon_abs.is_absolute():
            icon_abs = root / icon_abs
        self.qr_window = QRWindow(on_retry=self._show_qr, app_icon_path=str(icon_abs))

        self.process_manager = ProcessManager()
        self.tray: TrayController | None = None
        self._repo_root = Path(__file__).resolve().parent.parent
        local_appdata = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        self._first_run_marker = local_appdata / "LolMakroBridge" / "startup-notice-shown.flag"

        self._device_id: str | None = None

    def _notify(self, title: str, message: str) -> None:
        if self.tray:
            self.tray.notify(title, message)

    def _ensure_tunnel_started(self) -> str:
        fixed_public_url = os.environ.get("LOL_BRIDGE_PUBLIC_URL", "").strip()
        if fixed_public_url:
            normalized = fixed_public_url.rstrip("/")
            lowered = normalized.lower()
            if "localhost" in lowered or "127.0.0.1" in lowered:
                raise RuntimeError("LOL_BRIDGE_PUBLIC_URL localhost olamaz. Cloudflare public domain kullanin.")
            return normalized
        tunnel_name = os.environ.get("LOL_BRIDGE_TUNNEL_NAME")
        if tunnel_name:
            self.tunnel.start()
            url = self.tunnel.public_url
            if url:
                return url
            raise RuntimeError(f"Tunnel {tunnel_name} baslatilamadi.")
        if self.tunnel.is_running and self.tunnel.public_url:
            return self.tunnel.public_url
        return self.tunnel.start()

    def _get_site_url(self) -> str | None:
        value = os.environ.get("NEXT_PUBLIC_SITE_URL", "").strip().rstrip("/")
        return value or None

    def _get_configured_public_base(self) -> str | None:
        value = os.environ.get("LOL_BRIDGE_PUBLIC_URL", "").strip().rstrip("/")
        return value or None

    def _load_device_id(self) -> str:
        config_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "LolMakroBridge"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "device.json"
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text(encoding="utf-8"))
                if "device_id" in data:
                    return data["device_id"]
            except Exception:
                pass
        import uuid
        device_id = "pc_" + uuid.uuid4().hex[:16]
        config_file.write_text(json.dumps({"device_id": device_id}), encoding="utf-8")
        return device_id

    def _register_with_site(self) -> None:
        site_url = self._get_site_url()
        if not site_url:
            return
        self._device_id = self._load_device_id()
        remote_url = self._get_configured_public_base()
        if not remote_url:
            try:
                remote_url = self._ensure_tunnel_started()
            except Exception:
                remote_url = None
        if not remote_url:
            return
        try:
            payload = {
                "device_id": self._device_id,
                "remote_url": remote_url,
                "pc_name": socket.gethostname(),
            }
            resp = httpx.post(f"{site_url}/api/pc/register", json=payload, timeout=10)
            if resp.status_code == 200:
                self._notify("GameMode1", "Site kaydi basarili.")
        except Exception:
            pass

    def _check_apk_update(self) -> None:
        site_url = self._get_site_url()
        if not site_url:
            return
        try:
            resp = httpx.get(f"{site_url}/api/latestapk", timeout=10)
            if resp.status_code != 200:
                return
            data = resp.json()
            latest = data.get("version", "")
            if not latest:
                return

            config_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "LolMakroBridge"
            config_dir.mkdir(parents=True, exist_ok=True)
            version_file = config_dir / "apk_version.json"
            current = ""
            if version_file.exists():
                try:
                    current = json.loads(version_file.read_text(encoding="utf-8")).get("version", "")
                except Exception:
                    current = ""

            if self._is_newer_version(latest, current):
                self._notify(
                    "GameMode1",
                    f"Mobil uygulama guncellemesi: v{latest}. {data.get('download_url', '')} adresinden indirin.",
                )
        except Exception:
            pass

    @staticmethod
    def _is_newer_version(latest: str, current: str) -> bool:
        def _parse(v: str) -> tuple[int, ...]:
            try:
                return tuple(int(x) for x in v.split(".", 3))
            except Exception:
                return (0,)
        return _parse(latest) > _parse(current) if current else True

    def _create_site_token(self) -> str | None:
        site_url = self._get_site_url()
        if not site_url or not self._device_id:
            return None
        try:
            resp = httpx.post(
                f"{site_url}/api/pc/token",
                json={"device_id": self._device_id},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("token")
        except Exception:
            pass
        return None

    def _build_pair_url(self) -> str:
        site_url = self._get_site_url()
        if site_url and self._device_id:
            token = self._create_site_token() or token_manager.create_token()
            return f"{site_url}/qrcode?token={quote(token, safe='')}"

        token = token_manager.create_token()
        remote_base = self._get_configured_public_base()
        if not remote_base:
            remote_base = self._ensure_tunnel_started()

        return f"{remote_base}/mobile/pair?token={quote(token, safe='')}"

    def _download_apk(self) -> None:
        site_url = self._get_site_url()
        if site_url:
            import webbrowser
            webbrowser.open(f"{site_url}/apps")

    def _show_qr(self) -> None:
        try:
            self.qr_window.show_loading("Guvenli baglanti linki olusturuluyor...")
            url = self._build_pair_url()
            self.qr_window.show(url)
            self._notify("GameMode1", "QR kod olusturuldu.")
        except Exception as exc:
            error_text = str(exc) or "Bilinmeyen hata"
            self.qr_window.show_error(error_text)
            self._notify("GameMode1", f"QR kod olusturulamadi: {error_text}")

    def _start_tunnel(self) -> None:
        try:
            url = self._ensure_tunnel_started()
            self.tunnel.start_auto_reconnect()
            self._notify("GameMode1", "Remote tunnel baslatildi.")
        except Exception as exc:
            self._notify("GameMode1", f"Remote tunnel baslatilamadi: {exc}")

    def _stop_tunnel(self) -> None:
        self.tunnel.stop()
        self._notify("GameMode1", "Remote tunnel durduruldu.")

    def _toggle_startup(self) -> None:
        current = is_startup_enabled(self.settings.startup_registry_name)
        new_value = not current
        set_startup_enabled(self.settings.startup_registry_name, new_value)
        self._notify("GameMode1", "Baslangicta Calistir: Acik" if new_value else "Baslangicta Calistir: Kapali")

    def _restart(self) -> None:
        root = self._repo_root
        self.process_manager.restart_backend(
            root,
            self.settings.backend_host,
            self.settings.backend_port,
        )

    def _exit(self) -> None:
        self.tunnel.stop()
        self.process_manager.stop()
        if self.tray:
            self.tray.stop()
        os._exit(0)

    def run(self) -> None:
        self._register_with_site()
        self._check_apk_update()
        if self.tunnel.is_running:
            self.tunnel.start_auto_reconnect()

        icon = Path(self.settings.icon_path)
        if not icon.is_absolute():
            icon = Path(__file__).resolve().parent.parent / icon
        self.tray = TrayController(
            icon_path=icon,
            on_show_qr=self._show_qr,
            on_toggle_startup=self._toggle_startup,
            startup_enabled_getter=lambda: is_startup_enabled(self.settings.startup_registry_name),
            notify=self._notify,
            on_restart=self._restart,
            on_exit=self._exit,
            on_download_apk=self._download_apk,
        )
        self.tray.run_async()

        first_run = not self._first_run_marker.exists()
        if first_run:
            self._notify("GameMode1", "Uygulama acildi. Sistem tepsisinde gorebilirsiniz.")
            startup_image = Path(r"C:\Users\xmemo\OneDrive\Resimler\Screenshots\Ekran görüntüsü 2026-05-18 180151.png")
            if startup_image.exists():
                self.qr_window.show_startup_info(
                    str(startup_image),
                    "Uygulama Acildi",
                    "Kullanmadan once League of Legends istemcisi arka planda acik olmalidir.",
                )
            try:
                self._first_run_marker.parent.mkdir(parents=True, exist_ok=True)
                self._first_run_marker.write_text("shown=1\n", encoding="utf-8")
            except Exception:
                pass

        uvicorn.run(
            "live_server:app",
            host=self.settings.backend_host,
            port=self.settings.backend_port,
            reload=False,
            log_level="info",
        )


def run() -> None:
    DesktopBridgeApp(AppSettings()).run()