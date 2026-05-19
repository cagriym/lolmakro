# State Manager component
# Coordinates component interactions and maintains application state

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Optional

from .lcu_monitor import LCUMonitor, GameflowPhase, ChampSelectSession
from .context_extractor import extract_champ_select_context, ChampSelectContext
from .preset_provider import PresetProvider, RunePage, RuneContext
from .rune_page_controller import RunePageController, AppSlot, RuneSlotType


@dataclass
class AppState:
    """Application state model"""
    gameflow_phase: Optional[GameflowPhase] = None
    champ_select_context: Optional[ChampSelectContext] = None
    available_presets: list[RunePage] = field(default_factory=list)
    selected_preset_index: Optional[int] = None
    app_slots: list[AppSlot] = field(default_factory=list)
    active_slot_index: Optional[int] = None
    is_edit_mode: bool = False


class StateManager:
    """Coordinates component interactions and maintains application state"""
    
    def __init__(
        self,
        lcu_monitor: LCUMonitor,
        preset_provider: PresetProvider,
        rune_page_controller: RunePageController
    ) -> None:
        """
        Initialize State Manager
        
        Args:
            lcu_monitor: LCU Monitor instance for gameflow and session monitoring
            preset_provider: Preset Provider instance for rune page lookups
            rune_page_controller: Rune Page Controller instance for slot management
        """
        self._lcu_monitor = lcu_monitor
        self._preset_provider = preset_provider
        self._rune_page_controller = rune_page_controller
        
        self._state = AppState()
        self._state_change_callbacks: list[Callable[[AppState], Awaitable[None] | None]] = []
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize all components and register event handlers
        
        Raises:
            RuntimeError: If any component fails to initialize
        """
        # Initialize rune page controller (creates app slots)
        await self._rune_page_controller.initialize()
        
        # Update state with app slots
        self._state.app_slots = self._rune_page_controller.get_app_slots()
        
        # Find active slot if any
        active_slot = self._rune_page_controller.get_active_slot()
        if active_slot:
            self._state.active_slot_index = active_slot.slotIndex
        
        # Register event handlers
        self._lcu_monitor.on_gameflow_change(self._handle_gameflow_change)
        self._lcu_monitor.on_champ_select_change(self._handle_champ_select_change)
        
        # Start monitoring
        await self._lcu_monitor.start()
        
        self._initialized = True
        
        # Notify initial state
        await self._notify_state_change()
    
    async def shutdown(self) -> None:
        """Shutdown the state manager and stop monitoring"""
        await self._lcu_monitor.stop()
        self._initialized = False
    
    def get_current_state(self) -> AppState:
        """
        Get current application state
        
        Returns:
            Copy of current AppState
        """
        # Return a copy to prevent external modifications
        return AppState(
            gameflow_phase=self._state.gameflow_phase,
            champ_select_context=self._state.champ_select_context,
            available_presets=self._state.available_presets.copy(),
            selected_preset_index=self._state.selected_preset_index,
            app_slots=self._state.app_slots.copy(),
            active_slot_index=self._state.active_slot_index,
            is_edit_mode=self._state.is_edit_mode,
        )
    
    def on_state_change(self, callback: Callable[[AppState], Awaitable[None] | None]) -> None:
        """
        Register callback for state changes
        
        Args:
            callback: Function to call when state changes (can be sync or async)
        """
        self._state_change_callbacks.append(callback)
    
    async def _notify_state_change(self) -> None:
        """Notify all registered callbacks of state change"""
        state_copy = self.get_current_state()
        
        for callback in self._state_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(state_copy)
                else:
                    callback(state_copy)
            except Exception:
                # Silently handle callback errors to prevent one bad callback from breaking others
                pass
    
    async def _handle_gameflow_change(self, phase: Optional[GameflowPhase]) -> None:
        """
        Handle gameflow phase changes
        
        Args:
            phase: New gameflow phase (None if disconnected)
        """
        self._state.gameflow_phase = phase
        
        # Clear champion select context if leaving ChampSelect phase
        if phase != GameflowPhase.CHAMP_SELECT:
            self._state.champ_select_context = None
            self._state.available_presets = []
            self._state.selected_preset_index = None
        
        await self._notify_state_change()
    
    async def _handle_champ_select_change(self, session: Optional[ChampSelectSession]) -> None:
        """
        Handle champion select session changes
        
        Args:
            session: Champion select session data (None if session ended)
        """
        if session is None:
            # Clear context and presets
            self._state.champ_select_context = None
            self._state.available_presets = []
            self._state.selected_preset_index = None
            await self._notify_state_change()
            return
        
        # Extract context from session
        context = extract_champ_select_context(session)
        
        if context is None:
            # Champion not selected yet
            self._state.champ_select_context = None
            self._state.available_presets = []
            self._state.selected_preset_index = None
            await self._notify_state_change()
            return
        
        # Check if context changed
        if self._state.champ_select_context != context:
            self._state.champ_select_context = context
            
            # Query presets for new context
            rune_context = RuneContext(
                championId=context.champion_id,
                queueId=context.queue_id,
                role=context.role
            )
            
            presets = self._preset_provider.get_presets(rune_context)
            self._state.available_presets = presets
            self._state.selected_preset_index = None
            
            await self._notify_state_change()
    
    async def select_preset(self, preset_index: int) -> None:
        """
        Select and apply a preset to an app slot
        
        Args:
            preset_index: Index of the preset to select (0-2)
        
        Raises:
            RuntimeError: If not initialized
            ValueError: If preset_index is invalid
            ConnectionError: If LCU API call fails
        """
        if not self._initialized:
            raise RuntimeError("StateManager not initialized. Call initialize() first.")
        
        if preset_index < 0 or preset_index >= len(self._state.available_presets):
            raise ValueError(
                f"Invalid preset_index: {preset_index}. "
                f"Must be between 0 and {len(self._state.available_presets) - 1}"
            )
        
        preset = self._state.available_presets[preset_index]
        
        # Apply preset to the corresponding slot (use preset_index as slot_index)
        # This ensures preset 0 -> slot 0, preset 1 -> slot 1, preset 2 -> slot 2
        slot_index = preset_index
        
        await self._rune_page_controller.apply_preset_to_slot(preset, slot_index)
        
        # Update state
        self._state.selected_preset_index = preset_index
        self._state.active_slot_index = slot_index
        self._state.app_slots = self._rune_page_controller.get_app_slots()
        
        await self._notify_state_change()
    
    async def edit_rune(self, rune_id: int, slot_type: RuneSlotType) -> None:
        """
        Edit a rune in the active slot
        
        Args:
            rune_id: ID of the rune to set
            slot_type: Type of slot to update
        
        Raises:
            RuntimeError: If not initialized or no active slot
            ValueError: If rune is incompatible with slot
            ConnectionError: If LCU API call fails
        """
        if not self._initialized:
            raise RuntimeError("StateManager not initialized. Call initialize() first.")
        
        # Get rune metadata for validation
        rune_metadata = self._preset_provider.get_rune_metadata(rune_id)
        
        # Update rune in active slot
        await self._rune_page_controller.update_rune_in_active_slot(
            rune_id, 
            slot_type, 
            rune_metadata
        )
        
        # Update state with latest slot data
        self._state.app_slots = self._rune_page_controller.get_app_slots()
        
        await self._notify_state_change()
    
    async def set_edit_mode(self, enabled: bool) -> None:
        """
        Set edit mode state
        
        Args:
            enabled: Whether edit mode is enabled
        """
        if self._state.is_edit_mode != enabled:
            self._state.is_edit_mode = enabled
            await self._notify_state_change()
    
    def is_initialized(self) -> bool:
        """Check if state manager is initialized"""
        return self._initialized


# Import asyncio at the top level for use in _notify_state_change
import asyncio
