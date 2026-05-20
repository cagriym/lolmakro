from __future__ import annotations

import re
import socket
import subprocess
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path


CF_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


class TunnelManager:
    def __init__(self, cloudflared_path: str, target_url: str, tunnel_name: str | None = None) -> None:
        self.cloudflared_path = cloudflared_path
        self.target_url = target_url
        self.tunnel_name = tunnel_name
        self._proc: subprocess.Popen[str] | None = None
        self._public_url: str | None = None
        self._lock = threading.Lock()
        self._reader_thread: threading.Thread | None = None
        self._last_error: str | None = None
        local_appdata = Path(Path.home(), "AppData", "Local")
        self._log_path = local_appdata / "LolMakroBridge" / "tunnel.log"

    @property
    def public_url(self) -> str | None:
        return self._public_url

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def _build_args(self) -> list[str]:
        exe = str(Path(self.cloudflared_path))
        if self.tunnel_name:
            return [exe, "tunnel", "run", self.tunnel_name]
        return [exe, "tunnel", "--url", self.target_url, "--no-autoupdate"]

    def start(self, timeout_seconds: int = 20) -> str:
        with self._lock:
            self._log("start requested")
            if self.is_running and self._public_url:
                self._log(f"reusing running tunnel url={self._public_url}")
                return self._public_url

            exe = Path(self.cloudflared_path)
            if not exe.exists():
                self._log(f"cloudflared missing, downloading to {exe}")
                self._download_cloudflared(exe)
            self._log(f"cloudflared path={exe} target={self.target_url} tunnel_name={self.tunnel_name}")

            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                self._log(f"attempt {attempt}/{max_attempts} starting process")
                self._stop_locked()
                self._public_url = None
                self._last_error = None

                self._proc = subprocess.Popen(
                    self._build_args(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
                self._reader_thread.start()

                deadline = time.time() + timeout_seconds
                while time.time() < deadline:
                    if self._public_url and self._is_public_url_usable(self._public_url):
                        self._log(f"attempt {attempt} success url={self._public_url}")
                        return self._public_url
                    if not self.is_running:
                        self._log(f"attempt {attempt} process exited early")
                        break
                    time.sleep(0.2)

                if attempt < max_attempts and self._is_transient_quicktunnel_error():
                    self._log(f"attempt {attempt} transient error: {self._last_error}")
                    time.sleep(1.0)
                    continue
                self._log(f"attempt {attempt} failed: {self._last_error}")
                self.stop()
                raise RuntimeError(self._last_error or "Tunnel URL alinamadi.")

        raise RuntimeError(self._last_error or "Tunnel URL alinamadi.")

    def _is_transient_quicktunnel_error(self) -> bool:
        text = (self._last_error or "").lower()
        return (
            "error unmarshaling quicktunnel response" in text
            or "status_code=\"500 internal server error\"" in text
            or "invalid character 'e' looking for beginning of value" in text
        )

    def _is_public_url_usable(self, url: str) -> bool:
        try:
            host = url.split("://", 1)[1].split("/", 1)[0]
            socket.getaddrinfo(host, 443)
            with urllib.request.urlopen(f"{url}/api/health", timeout=4) as resp:
                return 200 <= getattr(resp, "status", 0) < 500
        except Exception as exc:
            self._last_error = f"Tunnel URL dogrulama hatasi: {exc}"
            self._log(self._last_error)
            return False

    def _download_cloudflared(self, exe_path: Path) -> None:
        exe_path.parent.mkdir(parents=True, exist_ok=True)
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        try:
            urllib.request.urlretrieve(url, str(exe_path))
        except Exception as exc:
            raise FileNotFoundError(f"cloudflared indirilemedi: {exc}") from exc

    def start_auto_reconnect(self, check_interval: int = 15) -> None:
        def _monitor() -> None:
            while True:
                time.sleep(check_interval)
                try:
                    if not self.is_running:
                        self._log("tunnel not running, attempting auto-reconnect")
                        with self._lock:
                            if not self.is_running:
                                self._proc = None
                                self._public_url = None
                        try:
                            self.start(timeout_seconds=20)
                            self._log(f"auto-reconnect success url={self._public_url}")
                        except Exception as e:
                            self._log(f"auto-reconnect failed: {e}")
                except Exception:
                    pass

        t = threading.Thread(target=_monitor, daemon=True)
        t.start()
        self._log("auto-reconnect monitor started")

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def _stop_locked(self) -> None:
        proc = self._proc
        self._proc = None
        self._public_url = None
        if not proc:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        self._log("tunnel process stopped")

    def _read_output(self) -> None:
        proc = self._proc
        if not proc or not proc.stdout:
            return
        for line in proc.stdout:
            self._log(f"cloudflared: {line.rstrip()}")
            matched = CF_URL_RE.search(line)
            if matched:
                self._public_url = matched.group(0)
                self._log(f"url discovered: {self._public_url}")
            if self.tunnel_name and "connection" in line.lower() and "registered" in line.lower():
                self._public_url = f"https://{self.tunnel_name}"
                self._log(f"named tunnel url: {self._public_url}")
            if "ERR" in line.upper():
                self._last_error = line.strip()

    def _log(self, message: str) -> None:
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(f"[{stamp}] {message}\n")
        except Exception:
            pass
