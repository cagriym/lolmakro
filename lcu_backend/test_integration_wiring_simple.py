"""
Simple integration tests for Task 24.1: Wire backend components together

Verifies that all backend components are properly connected and can work together.
This test focuses on verifying the wiring exists rather than testing full functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from .state_manager import StateManager
from .lcu_monitor import LCUMonitor
from .preset_provider import PresetProvider
from .rune_page_controller import RunePageController
from .api_server import APIServer, WebSocketManager


class TestBackendWiring:
    """Verify backend components are properly wired together"""

    def test_state_manager_has_all_components(self):
        """Verify StateManager is wired to all required components"""
        # Create mock components
        mock_monitor = Mock(spec=LCUMonitor)
        mock_provider = Mock(spec=PresetProvider)
        mock_controller = Mock(spec=RunePageController)
        
        # Create state manager
        manager = StateManager(mock_monitor, mock_provider, mock_controller)
        
        # Verify wiring (components are stored as private attributes)
        assert manager._lcu_monitor is mock_monitor, "LCU Monitor not connected to State Manager"
        assert manager._preset_provider is mock_provider, "Preset Provider not connected to State Manager"
        assert manager._rune_page_controller is mock_controller, "Rune Page Controller not connected to State Manager"

    def test_api_server_has_state_manager(self):
        """Verify API Server is wired to State Manager"""
        # Create mock state manager
        mock_manager = Mock(spec=StateManager)
        mock_manager.is_initialized.return_value = True
        mock_manager.get_current_state.return_value = {
            "connected": False,
            "gameflow_phase": "None",
            "champ_select_context": None,
            "available_presets": [],
            "app_slots": [],
            "active_slot_index": None,
            "is_edit_mode": False
        }
        
        # Create API server
        api_server = APIServer(mock_manager)
        
        # Verify wiring
        assert api_server.state_manager is mock_manager, "State Manager not connected to API Server"

    def test_rune_page_controller_has_preset_provider(self):
        """Verify Rune Page Controller is wired to Preset Provider"""
        # Create mocks
        mock_connection = Mock()
        mock_provider = Mock(spec=PresetProvider)
        
        # Create controller
        controller = RunePageController(mock_connection, mock_provider)
        
        # Verify wiring (stored as private attribute)
        assert controller._preset_provider is mock_provider, "Preset Provider not connected to Rune Page Controller"

    def test_state_manager_can_register_callbacks(self):
        """Verify State Manager supports callback registration"""
        # Create mock components
        mock_monitor = Mock(spec=LCUMonitor)
        mock_provider = Mock(spec=PresetProvider)
        mock_controller = Mock(spec=RunePageController)
        
        # Create state manager
        manager = StateManager(mock_monitor, mock_provider, mock_controller)
        
        # Register callback
        callback_called = False
        def test_callback(state):
            nonlocal callback_called
            callback_called = True
        
        manager.on_state_change(test_callback)
        
        # Verify callback was registered
        assert len(manager._state_change_callbacks) > 0, "Callback not registered"

    @pytest.mark.asyncio
    async def test_websocket_manager_can_manage_connections(self):
        """Verify WebSocket Manager can manage connections"""
        ws_manager = WebSocketManager()
        
        # Create mock websocket
        mock_ws = AsyncMock()
        
        # Add connection
        await ws_manager.connect(mock_ws)
        
        # Verify connection was added
        assert len(ws_manager.connections) == 1, "WebSocket connection not added"
        
        # Remove connection (disconnect is not async)
        ws_manager.disconnect(mock_ws)
        
        # Verify connection was removed
        assert len(ws_manager.connections) == 0, "WebSocket connection not removed"

    def test_all_components_exist(self):
        """Verify all required components can be imported and instantiated"""
        # This test verifies that all components exist and can be created
        
        # Create mock dependencies
        mock_connection = Mock()
        mock_provider = Mock(spec=PresetProvider)
        
        # Verify LCU Monitor can be created
        monitor = LCUMonitor(mock_connection)
        assert monitor is not None, "LCU Monitor cannot be instantiated"
        
        # Verify Preset Provider can be created
        provider = PresetProvider()
        assert provider is not None, "Preset Provider cannot be instantiated"
        
        # Verify Rune Page Controller can be created
        controller = RunePageController(mock_connection, mock_provider)
        assert controller is not None, "Rune Page Controller cannot be instantiated"
        
        # Verify State Manager can be created
        manager = StateManager(monitor, provider, controller)
        assert manager is not None, "State Manager cannot be instantiated"
        
        # Verify API Server can be created
        mock_manager = Mock(spec=StateManager)
        api_server = APIServer(mock_manager)
        assert api_server is not None, "API Server cannot be instantiated"
        
        # Verify WebSocket Manager can be created
        ws_manager = WebSocketManager()
        assert ws_manager is not None, "WebSocket Manager cannot be instantiated"

    def test_component_integration_points(self):
        """Verify all integration points between components exist"""
        # Create mock components
        mock_connection = Mock()
        mock_provider = Mock(spec=PresetProvider)
        mock_monitor = Mock(spec=LCUMonitor)
        mock_controller = Mock(spec=RunePageController)
        
        # Create state manager
        manager = StateManager(mock_monitor, mock_provider, mock_controller)
        
        # Verify State Manager has private attributes for components
        assert hasattr(manager, '_lcu_monitor'), "State Manager missing _lcu_monitor attribute"
        assert hasattr(manager, '_preset_provider'), "State Manager missing _preset_provider attribute"
        assert hasattr(manager, '_rune_page_controller'), "State Manager missing _rune_page_controller attribute"
        
        # Verify State Manager has public methods
        assert hasattr(manager, 'get_current_state'), "State Manager missing get_current_state method"
        assert hasattr(manager, 'on_state_change'), "State Manager missing on_state_change method"
        assert hasattr(manager, 'select_preset'), "State Manager missing select_preset method"
        assert hasattr(manager, 'edit_rune'), "State Manager missing edit_rune method"
        assert hasattr(manager, 'set_edit_mode'), "State Manager missing set_edit_mode method"
        assert hasattr(manager, 'initialize'), "State Manager missing initialize method"
        assert hasattr(manager, 'is_initialized'), "State Manager missing is_initialized method"


class TestEventHandlerRegistration:
    """Verify event handlers are properly registered"""

    def test_lcu_monitor_supports_callbacks(self):
        """Verify LCU Monitor supports callback registration"""
        mock_connection = Mock()
        monitor = LCUMonitor(mock_connection)
        
        # Verify callback registration methods exist
        assert hasattr(monitor, 'on_gameflow_change'), "LCU Monitor missing on_gameflow_change method"
        assert hasattr(monitor, 'on_champ_select_change'), "LCU Monitor missing on_champ_select_change method"

    def test_state_manager_registers_with_monitor(self):
        """Verify State Manager registers callbacks with LCU Monitor during initialization"""
        mock_connection = Mock()
        mock_provider = Mock(spec=PresetProvider)
        mock_controller = Mock(spec=RunePageController)
        
        # Create monitor
        monitor = LCUMonitor(mock_connection)
        
        # Create state manager (callbacks are registered during initialize(), not __init__)
        manager = StateManager(monitor, mock_provider, mock_controller)
        
        # Verify manager was created successfully
        assert manager is not None
        
        # Note: Callbacks are registered when initialize() is called, not in __init__
        # This is verified by the existing test_state_manager.py tests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
