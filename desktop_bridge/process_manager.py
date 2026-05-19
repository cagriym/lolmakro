from __future__ import annotations

import subprocess
from pathlib import Path


class ProcessManager:
    def __init__(self) -> None:
        self.backend_proc: subprocess.Popen[str] | None = None

    def start_backend(self, cwd: Path, host: str, port: int) -> None:
        if self.backend_proc and self.backend_proc.poll() is None:
            return
        self.backend_proc = subprocess.Popen(
            [
                "python",
                "-m",
                "uvicorn",
                "live_server:app",
                "--host",
                host,
                "--port",
                str(port),
            ],
            cwd=str(cwd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )

    def stop(self) -> None:
        if self.backend_proc and self.backend_proc.poll() is None:
            self.backend_proc.terminate()
            try:
                self.backend_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_proc.kill()
        self.backend_proc = None

    def restart_backend(self, cwd: Path, host: str, port: int) -> None:
        self.stop()
        self.start_backend(cwd, host, port)
