from __future__ import annotations

import sys
import winreg
from pathlib import Path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _open_run_key(access: int):
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, access)


def is_startup_enabled(name: str) -> bool:
    try:
        with _open_run_key(winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, name)
            return True
    except OSError:
        return False


def set_startup_enabled(name: str, enabled: bool) -> None:
    with _open_run_key(winreg.KEY_SET_VALUE) as key:
        if enabled:
            exe = Path(sys.executable).resolve()
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, f'"{exe}" --tray')
        else:
            try:
                winreg.DeleteValue(key, name)
            except OSError:
                pass
