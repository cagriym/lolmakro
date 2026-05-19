# LCU connection and authentication module
# Handles lockfile parsing, HTTPS client setup, and connection management

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import POLLING


@dataclass
class LockfileAuth:
    """LCU lockfile authentication data"""
    name: str
    pid: int
    port: int
    password: str
    protocol: str
    lockfile_path: str


class LCUConnection:
    """Manages connection to League Client Update (LCU) API"""
    
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._auth: LockfileAuth | None = None
        self._connection_callbacks: list[callable] = []
        self._disconnection_callbacks: list[callable] = []
    
    @staticmethod
    def _get_lockfile_candidates() -> list[Path]:
        """Get list of possible lockfile locations"""
        import os
        
        candidates = []
        
        # Check environment variable first
        env_path = os.environ.get("LOL_LOCKFILE_PATH")
        if env_path:
            candidates.append(Path(env_path))
        
        # Common Windows locations
        candidates.extend([
            Path(r"C:\Riot Games\League of Legends\lockfile"),
            Path(r"C:\Riot Games\League of Legends\Game\lockfile"),
            Path.home() / "AppData/Local/Riot Games/League of Legends/lockfile",
        ])
        
        return candidates
    
    @staticmethod
    def _parse_lockfile(path: Path) -> LockfileAuth | None:
        """Parse lockfile and extract authentication data"""
        if not path.exists():
            return None
        
        try:
            content = path.read_text(encoding="utf-8").strip()
            parts = content.split(":")
            
            if len(parts) != 5:
                return None
            
            name, pid, port, password, protocol = parts
            
            return LockfileAuth(
                name=name,
                pid=int(pid),
                port=int(port),
                password=password,
                protocol=protocol,
                lockfile_path=str(path),
            )
        except Exception:
            return None
    
    def _find_lockfile_auth(self) -> LockfileAuth | None:
        """Find and parse lockfile from candidate locations"""
        for candidate in self._get_lockfile_candidates():
            auth = self._parse_lockfile(candidate)
            if auth:
                return auth
        return None
    
    async def _ensure_client(self) -> LockfileAuth | None:
        """Ensure HTTP client is initialized with current lockfile auth"""
        auth = self._find_lockfile_auth()
        
        if not auth:
            # Lockfile not found, close existing connection
            await self.close()
            return None
        
        # Check if auth changed
        if self._auth and self._client:
            unchanged = (
                self._auth.port == auth.port
                and self._auth.password == auth.password
                and self._auth.protocol == auth.protocol
                and self._auth.lockfile_path == auth.lockfile_path
            )
            if unchanged:
                return self._auth
        
        # Auth changed or no client, recreate
        was_connected = self._client is not None
        await self.close()
        
        self._auth = auth
        self._client = httpx.AsyncClient(
            base_url=f"{auth.protocol}://127.0.0.1:{auth.port}",
            auth=("riot", auth.password),
            verify=False,  # Accept self-signed certificate
            timeout=httpx.Timeout(5.0, connect=2.0),
        )
        
        # Notify connection callbacks if this is a new connection
        if not was_connected:
            for callback in self._connection_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception:
                    pass
        
        return auth
    
    async def close(self) -> None:
        """Close HTTP client and clear auth"""
        was_connected = self._client is not None
        
        if self._client:
            await self._client.aclose()
        
        self._client = None
        self._auth = None
        
        # Notify disconnection callbacks
        if was_connected:
            for callback in self._disconnection_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception:
                    pass
    
    async def get(self, path: str) -> Any:
        """
        Perform GET request to LCU API
        Returns None if connection fails or endpoint returns error
        """
        auth = await self._ensure_client()
        if not auth or not self._client:
            return None
        
        try:
            response = await self._client.get(path)
            response.raise_for_status()
            
            if not response.text:
                return None
            
            return response.json()
        except Exception:
            return None
    
    async def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        """Perform POST request to LCU API"""
        return await self._request("POST", path, payload)
    
    async def patch(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        """Perform PATCH request to LCU API"""
        return await self._request("PATCH", path, payload)
    
    async def put(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        """Perform PUT request to LCU API"""
        return await self._request("PUT", path, payload)
    
    async def delete(self, path: str) -> Any:
        """Perform DELETE request to LCU API"""
        return await self._request("DELETE", path)
    
    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        """Perform HTTP request to LCU API with error handling"""
        auth = await self._ensure_client()
        if not auth or not self._client:
            raise ConnectionError("League Client not connected")
        
        try:
            response = await self._client.request(
                method=method,
                url=path,
                json=payload
            )
            response.raise_for_status()
            
            if not response.text:
                return None
            
            return response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"LCU API error: {e.response.status_code} - {e.response.text}") from e
        except Exception as e:
            raise RuntimeError(f"LCU request failed: {e}") from e
    
    async def is_connected(self) -> bool:
        """Check if LCU connection is active"""
        auth = await self._ensure_client()
        return auth is not None
    
    async def get_lockfile_info(self) -> dict[str, Any]:
        """Get lockfile information for debugging"""
        auth = await self._ensure_client()
        if not auth:
            return {"connected": False, "lockfilePath": None}
        
        return {
            "connected": True,
            "lockfilePath": auth.lockfile_path,
            "port": auth.port,
            "protocol": auth.protocol,
        }
    
    def on_connect(self, callback: callable) -> None:
        """Register callback for connection events"""
        self._connection_callbacks.append(callback)
    
    def on_disconnect(self, callback: callable) -> None:
        """Register callback for disconnection events"""
        self._disconnection_callbacks.append(callback)
    
    async def retry_until_connected(self, max_retries: int = -1) -> bool:
        """
        Retry connection until successful or max_retries reached
        max_retries=-1 means infinite retries
        Returns True if connected, False if max_retries reached
        """
        retries = 0
        while max_retries < 0 or retries < max_retries:
            if await self.is_connected():
                return True
            
            retries += 1
            await asyncio.sleep(POLLING.CONNECTION_RETRY_INTERVAL)
        
        return False
