from __future__ import annotations

import socket


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass

    try:
        host = socket.gethostname()
        ip = socket.gethostbyname(host)
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass

    raise RuntimeError("Yerel IP adresi bulunamadı.")


def is_tcp_port_open(host: str, port: int, timeout_seconds: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False
