from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AppSettings:
    backend_host: str = os.environ.get("LOL_BRIDGE_BACKEND_HOST", "127.0.0.1")
    backend_port: int = int(os.environ.get("LOL_BRIDGE_BACKEND_PORT", "8765"))
    icon_path: str = os.environ.get("LOL_BRIDGE_ICON_PATH", "assets/logo.ico")
    startup_registry_name: str = "GameMode1"
