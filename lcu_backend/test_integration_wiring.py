"""
Integration tests for Task 24.1: Wire backend components together

Tests verify that:
- LCU Monitor connects to State Manager
- Preset Provider connects to State Manager
- Rune Page Controller connects to State Manager
- HTTP API server connects to State Manager
- All event handlers are properly registered
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from .state_manager import StateManager
from .lcu_monitor import LCUMonitor
from .preset_provider import PresetProvider
from .rune_page_controller import RunePageController
from .api_server import APIServer, WebSocketManager


class TestBackendComponentWiring:
    """Test that all backend components are properly wired together"""

    @pytest.fixture
    def mock_lcu_connection(self):
        """Mock LCU connection"""
        with patch('lcu_connection.LCUConnection') as mock:
            conn = Mock()
            conn.is_connected.return_value = True
            conn.get.return_value = {"phase": "None"}
            conn.post.return_value = {"id": 1}
            conn.patch.return_value = {}
            conn.put.return_value = {}
            mock.return_value = conn
            yield conn

    @pytest.fixture
    def preset_provider(self):
        """Create a preset provider with test data"""
        provider = PresetProvider()
        # Initialize with minimal test data
        test_data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [],
            "runeMetadata": [],
            "styleMetadata": []
        }
        provider.initialize(test_data)
        return provider

    @pytest.fixture
    def state_manager(self, mock_lcu_connection, preset_provider):
        """Create a state manager with mocked dependencies"""
        monitor = LCUMonitor(mock_lcu_connection)
        controller = RunePageController(mock_lcu_connection, preset_provider)
        manager = StateManager(monitor, preset_provider, controller)
        return manager

    def test_lcu_monitor_connected_to_state_manager(self, state_manager):
        """Verify LCU Monitor is connected to State Manager"""
        assert state_manager.monitor is not None
        assert isinstance(state_manager.monitor, LCUMonitor)

    def test_preset_provider_connected_to_state_manager(self, state_manager):
        """Verify Preset Provider is connected to State Manager"""
        assert state_manager.preset_provider is not None
        assert isinstance(state_manager.preset_provider, PresetProvider)

    def test_rune_page_controller_connected_to_state_manager(self, state_manager):
        """Verify Rune Page Controller is connected to State Manager"""
        assert state_manager.controller is not None
        assert isinstance(state_manager.controller, RunePageController)

    def test_gameflow_event_handler_registered(self, state_manager):
        """Verify gameflow change event handler is registered"""
        # Check that monitor has callbacks registered
        assert len(state_manager.monitor._gameflow_callbacks) > 0

    def test_champ_select_event_handler_registered(self, state_manager):
        """Verify champion select event handler is registered"""
        # Check that monitor has callbacks registered
        assert len(state_manager.monitor._champ_select_callbacks) > 0

    @pytest.mark.asyncio
    async def test_gameflow_change_propagates_to_state_manager(self, state_manager):
        """Verify gameflow changes propagate from monitor to state manager"""
        # Trigger gameflow change
        await state_manager.monitor._notify_gameflow_change("ChampSelect")
        
        # Verify state manager received the update
        state = state_manager.get_current_state()
        assert state["gameflow_phase"] == "ChampSelect"

    @pytest.mark.asyncio
    async def test_champ_select_change_queries_presets(self, state_manager, mock_lcu_connection):
        """Verify champion select changes trigger preset queries"""
        # Mock champion select session
        session = {
            "localPlayerCellId": 0,
            "myTeam": [{
                "cellId": 0,
                "championId": 157,  # Yasuo
                "assignedPosition": "middle"
            }],
            "timer": {"phase": "BAN_PICK"}
        }
        
        # Add a test preset for Yasuo
        state_manager.preset_provider.database.add_preset(
            champion_id=157,
            queue_id=420,
            role="middle",
            preset={
                "name": "Test Preset",
                "primaryStyleId": 8000,
                "subStyleId": 8100,
                "selectedPerkIds": [8005, 8008, 8021, 8010, 8139, 8135],
                "statShards": [5008, 5008, 5002]
            }
        )
        
        # Trigger champion select change
        await state_manager.monitor._notify_champ_select_change(session)
        
        # Verify presets were queried
        state = state_manager.get_current_state()
        assert state["champ_select_context"] is not None
        assert state["champ_select_context"]["champion_id"] == 157
        assert len(state["available_presets"]) > 0

    @pytest.mark.asyncio
    async def test_preset_selection_updates_controller(self, state_manager, mock_lcu_connection):
        """Verify preset selection updates rune page controller"""
        # Initialize controller
        mock_lcu_connection.get.return_value = []
        await state_manager.controller.initialize()
        
        # Add test preset
        test_preset = {
            "name": "Test Preset",
            "primaryStyleId": 8000,
            "subStyleId": 8100,
            "selectedPerkIds": [8005, 8008, 8021, 8010, 8139, 8135],
            "statShards": [5008, 5008, 5002]
        }
        state_manager._state["available_presets"] = [test_preset]
        
        # Select preset
        await state_manager.select_preset(0)
        
        # Verify controller was called
        assert mock_lcu_connection.patch.called or mock_lcu_connection.post.called

    def test_state_change_callbacks_registered(self, state_manager):
        """Verify state change callbacks can be registered"""
        callback_called = False
        
        def test_callback(state):
            nonlocal callback_called
            callback_called = True
        
        state_manager.on_state_change(test_callback)
        
        # Trigger state change
        state_manager._notify_state_change()
        
        assert callback_called

    @pytest.mark.asyncio
    async def test_api_server_can_access_state_manager(self):
        """Verify API server can access state manager"""
        # Create mock state manager
        mock_manager = Mock()
        mock_manager.get_current_state.return_value = {
            "connected": True,
            "gameflow_phase": "None",
            "champ_select_context": None,
            "available_presets": [],
            "app_slots": [],
            "active_slot_index": None,
            "is_edit_mode": False
        }
        mock_manager.is_initialized.return_value = True
        
        # Create API server with mock manager
        api_server = APIServer(mock_manager)
        
        # Verify API server has access to state manager
        assert api_server.state_manager is mock_manager

    @pytest.mark.asyncio
    async def test_websocket_manager_broadcasts_state_changes(self):
        """Verify WebSocket manager can broadcast state changes"""
        ws_manager = WebSocketManager()
        
        # Create mock websocket
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        
        # Add connection
        await ws_manager.connect(mock_ws)
        
        # Broadcast state
        test_state = {"connected": True, "phase": "ChampSelect"}
        await ws_manager.broadcast(test_state)
        
        # Verify websocket received broadcast
        assert mock_ws.send.called

    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self, state_manager, mock_lcu_connection):
        """Test complete workflow from gameflow change to preset application"""
        # Step 1: Initialize
        mock_lcu_connection.get.return_value = []
        await state_manager.initialize()
        
        # Step 2: Enter champion select
        await state_manager.handle_gameflow_change("ChampSelect")
        assert state_manager.get_current_state()["gameflow_phase"] == "ChampSelect"
        
        # Step 3: Select champion
        session = {
            "localPlayerCellId": 0,
            "myTeam": [{
                "cellId": 0,
                "championId": 157,
                "assignedPosition": "middle"
            }],
            "timer": {"phase": "BAN_PICK"}
        }
        
        # Add preset
        state_manager.preset_provider.database.add_preset(
            champion_id=157,
            queue_id=420,
            role="middle",
            preset={
                "name": "Test Preset",
                "primaryStyleId": 8000,
                "subStyleId": 8100,
                "selectedPerkIds": [8005, 8008, 8021, 8010, 8139, 8135],
                "statShards": [5008, 5008, 5002]
            }
        )
        
        await state_manager.handle_champ_select_change(session)
        
        # Verify presets loaded
        state = state_manager.get_current_state()
        assert len(state["available_presets"]) > 0
        
        # Step 4: Select preset
        await state_manager.select_preset(0)
        
        # Verify preset applied
        assert state_manager.get_current_state()["active_slot_index"] is not None


class TestComponentInitializationOrder:
    """Test that components initialize in the correct order"""

    @pytest.mark.asyncio
    async def test_state_manager_initializes_all_components(self, mock_lcu_connection):
        """Verify state manager initializes all components in correct order"""
        with patch('lcu_connection.LCUConnection', return_value=mock_lcu_connection):
            # Create components
            monitor = LCUMonitor(mock_lcu_connection)
            provider = PresetProvider()
            controller = RunePageController(mock_lcu_connection, provider)
            manager = StateManager(monitor, provider, controller)
            
            # Initialize with test data
            test_data = {
                "version": "1.0.0",
                "lastUpdated": "2024-01-01",
                "presets": [],
                "runeMetadata": [],
                "styleMetadata": []
            }
            provider.initialize(test_data)
            
            # Mock controller initialization
            mock_lcu_connection.get.return_value = []
            
            # Initialize state manager
            await manager.initialize()
            
            # Verify all components are initialized
            assert provider.is_initialized()
            assert controller.is_initialized()
            assert manager._initialized


class TestErrorPropagation:
    """Test that errors propagate correctly between components"""

    @pytest.mark.asyncio
    async def test_controller_error_propagates_to_state_manager(self, mock_lcu_connection):
        """Verify controller errors propagate to state manager"""
        monitor = LCUMonitor(mock_lcu_connection)
        provider = PresetProvider()
        controller = RunePageController(mock_lcu_connection, provider)
        manager = StateManager(monitor, provider, controller)
        
        # Initialize
        test_data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [],
            "runeMetadata": [],
            "styleMetadata": []
        }
        provider.initialize(test_data)
        mock_lcu_connection.get.return_value = []
        await manager.initialize()
        
        # Cause controller error by selecting invalid preset
        with pytest.raises(Exception):
            await manager.select_preset(999)

    @pytest.mark.asyncio
    async def test_monitor_connection_loss_updates_state(self, mock_lcu_connection):
        """Verify monitor connection loss updates state manager"""
        monitor = LCUMonitor(mock_lcu_connection)
        provider = PresetProvider()
        controller = RunePageController(mock_lcu_connection, provider)
        manager = StateManager(monitor, provider, controller)
        
        # Simulate connection loss
        mock_lcu_connection.is_connected.return_value = False
        
        # Verify state reflects disconnection
        state = manager.get_current_state()
        assert state["connected"] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
