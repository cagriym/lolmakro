# LCU Monitor component
# Monitors League Client state changes and extracts champion select context

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Awaitable

from .lcu_connection import LCUConnection
from .config import ENDPOINTS, POLLING


class GameflowPhase(str, Enum):
    """Gameflow phase enumeration"""
    NONE = "None"
    LOBBY = "Lobby"
    CHAMP_SELECT = "ChampSelect"
    IN_PROGRESS = "InProgress"
    END_OF_GAME = "EndOfGame"
    READY_CHECK = "ReadyCheck"
    MATCHMAKING = "Matchmaking"
    WAITING_FOR_STATS = "WaitingForStats"
    PRE_END_OF_GAME = "PreEndOfGame"
    RECONNECT = "Reconnect"


@dataclass
class ChampSelectSession:
    """Champion select session data"""
    local_player_cell_id: int
    my_team: list[dict[str, Any]]
    timer: dict[str, Any]
    actions: list[list[dict[str, Any]]]
    raw_data: dict[str, Any]  # Store full session data for additional fields


class LCUMonitor:
    """Monitors League Client state changes and extracts champion select context"""
    
    def __init__(self, connection: LCUConnection) -> None:
        self._connection = connection
        self._current_phase: GameflowPhase | None = None
        self._polling_task: asyncio.Task | None = None
        self._running = False
        
        # Callbacks for state changes
        self._gameflow_callbacks: list[Callable[[GameflowPhase], Awaitable[None] | None]] = []
        self._champ_select_callbacks: list[Callable[[ChampSelectSession | None], Awaitable[None] | None]] = []
    
    async def start(self) -> None:
        """Start monitoring gameflow phase"""
        if self._running:
            return
        
        self._running = True
        self._polling_task = asyncio.create_task(self._poll_gameflow())
    
    async def stop(self) -> None:
        """Stop monitoring gameflow phase"""
        self._running = False
        
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
    
    async def _poll_gameflow(self) -> None:
        """Poll gameflow phase endpoint at regular intervals"""
        while self._running:
            try:
                # Get current gameflow phase
                phase_str = await self._connection.get(ENDPOINTS.GAMEFLOW_PHASE)
                
                if phase_str is None:
                    # Connection lost or endpoint unavailable
                    if self._current_phase is not None:
                        self._current_phase = None
                        await self._notify_gameflow_change(None)
                else:
                    # Parse phase
                    try:
                        new_phase = GameflowPhase(phase_str)
                    except ValueError:
                        # Unknown phase, treat as None
                        new_phase = None
                    
                    # Detect phase change
                    if new_phase != self._current_phase:
                        old_phase = self._current_phase
                        self._current_phase = new_phase
                        await self._notify_gameflow_change(new_phase)
                        
                        # If entering ChampSelect, start monitoring session
                        if new_phase == GameflowPhase.CHAMP_SELECT:
                            asyncio.create_task(self._monitor_champ_select())
                        
                        # If leaving ChampSelect, notify with None to clear context
                        if old_phase == GameflowPhase.CHAMP_SELECT and new_phase != GameflowPhase.CHAMP_SELECT:
                            await self._notify_champ_select_change(None)
                
            except Exception:
                # Silently handle errors and continue polling
                pass
            
            # Wait before next poll
            await asyncio.sleep(POLLING.GAMEFLOW_POLL_INTERVAL)
    
    async def _monitor_champ_select(self) -> None:
        """Monitor champion select session while in ChampSelect phase"""
        last_session_data = None
        
        while self._running and self._current_phase == GameflowPhase.CHAMP_SELECT:
            try:
                # Fetch champion select session
                session_data = await self._connection.get(ENDPOINTS.CHAMP_SELECT_SESSION)
                
                if session_data is None:
                    # Session not available
                    if last_session_data is not None:
                        last_session_data = None
                        await self._notify_champ_select_change(None)
                else:
                    # Check if session data changed
                    if session_data != last_session_data:
                        last_session_data = session_data
                        session = self._parse_champ_select_session(session_data)
                        await self._notify_champ_select_change(session)
                
            except Exception:
                # Silently handle errors and continue monitoring
                pass
            
            # Wait before next poll
            await asyncio.sleep(POLLING.CHAMP_SELECT_POLL_INTERVAL)
    
    def _parse_champ_select_session(self, data: dict[str, Any]) -> ChampSelectSession | None:
        """Parse champion select session data"""
        try:
            return ChampSelectSession(
                local_player_cell_id=data.get("localPlayerCellId", -1),
                my_team=data.get("myTeam", []),
                timer=data.get("timer", {}),
                actions=data.get("actions", []),
                raw_data=data,
            )
        except Exception:
            return None
    
    async def _notify_gameflow_change(self, phase: GameflowPhase | None) -> None:
        """Notify all registered gameflow callbacks"""
        for callback in self._gameflow_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(phase)
                else:
                    callback(phase)
            except Exception:
                # Silently handle callback errors
                pass
    
    async def _notify_champ_select_change(self, session: ChampSelectSession | None) -> None:
        """Notify all registered champion select callbacks"""
        for callback in self._champ_select_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(session)
                else:
                    callback(session)
            except Exception:
                # Silently handle callback errors
                pass
    
    def on_gameflow_change(self, callback: Callable[[GameflowPhase | None], Awaitable[None] | None]) -> None:
        """Register callback for gameflow phase changes"""
        self._gameflow_callbacks.append(callback)
    
    def on_champ_select_change(self, callback: Callable[[ChampSelectSession | None], Awaitable[None] | None]) -> None:
        """Register callback for champion select session changes"""
        self._champ_select_callbacks.append(callback)
    
    async def get_gameflow_phase(self) -> GameflowPhase | None:
        """Get current gameflow phase"""
        return self._current_phase
    
    async def get_champ_select_session(self) -> ChampSelectSession | None:
        """Get current champion select session (only valid during ChampSelect phase)"""
        if self._current_phase != GameflowPhase.CHAMP_SELECT:
            return None
        
        session_data = await self._connection.get(ENDPOINTS.CHAMP_SELECT_SESSION)
        if session_data is None:
            return None
        
        return self._parse_champ_select_session(session_data)
