"""
Integration test for the preset selection workflow

This test demonstrates the complete workflow:
1. User enters champion select
2. System detects champion selection
3. System fetches presets for the champion
4. User selects a preset
5. System applies preset to app slot
6. System broadcasts state changes
"""

import pytest
from unittest.mock import AsyncMock, Mock
from lcu_backend.state_manager import StateManager, AppState
from lcu_backend.lcu_monitor import GameflowPhase, ChampSelectSession
from lcu_backend.preset_provider import RunePage
from lcu_backend.rune_page_controller import AppSlot


@pytest.fixture
def mock_lcu_monitor():
    """Create a mock LCU monitor"""
    monitor = Mock()
    monitor.start = AsyncMock()
    monitor.start_monitoring = AsyncMock()
    monitor.stop_monitoring = AsyncMock()
    monitor.on_gameflow_change = Mock()
    monitor.on_champ_select_change = Mock()
    return monitor


@pytest.fixture
def mock_preset_provider():
    """Create a mock preset provider"""
    provider = Mock()
    return provider


@pytest.fixture
def mock_rune_page_controller():
    """Create a mock rune page controller"""
    controller = Mock()
    controller.initialize = AsyncMock()
    controller.apply_preset_to_slot = AsyncMock()
    controller.update_rune_in_active_slot = AsyncMock()
    controller.get_active_slot = Mock(return_value=None)
    controller.get_app_slots = Mock(return_value=[
        AppSlot(slotIndex=0, pageId=1, name="App Slot 1", currentPage=None, isActive=False),
        AppSlot(slotIndex=1, pageId=2, name="App Slot 2", currentPage=None, isActive=False),
        AppSlot(slotIndex=2, pageId=3, name="App Slot 3", currentPage=None, isActive=False),
    ])
    return controller


@pytest.fixture
def state_manager(mock_lcu_monitor, mock_preset_provider, mock_rune_page_controller):
    """Create a state manager with mocked dependencies"""
    return StateManager(
        lcu_monitor=mock_lcu_monitor,
        preset_provider=mock_preset_provider,
        rune_page_controller=mock_rune_page_controller
    )


class TestPresetSelectionWorkflow:
    """Integration tests for the complete preset selection workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_preset_selection_workflow(
        self, state_manager, mock_lcu_monitor, mock_preset_provider, mock_rune_page_controller
    ):
        """
        Test the complete workflow from champion select to preset application
        
        This test validates Requirements 4.1, 4.2, 4.3, 6.1, 6.2, 6.3, 6.4
        """
        # Initialize the system
        await state_manager.initialize()
        
        # Step 1: User enters champion select
        # Simulate gameflow change to ChampSelect
        gameflow_callback = None
        def capture_gameflow_callback(callback):
            nonlocal gameflow_callback
            gameflow_callback = callback
        
        mock_lcu_monitor.on_gameflow_change.side_effect = capture_gameflow_callback
        await state_manager.initialize()  # Re-initialize to capture callback
        
        assert gameflow_callback is not None
        await gameflow_callback(GameflowPhase.CHAMP_SELECT)
        
        # Verify state updated
        state = state_manager.get_current_state()
        assert state.gameflow_phase == GameflowPhase.CHAMP_SELECT
        
        # Step 2: System detects champion selection
        # Simulate champion select session with champion selected
        champ_select_callback = None
        def capture_champ_select_callback(callback):
            nonlocal champ_select_callback
            champ_select_callback = callback
        
        mock_lcu_monitor.on_champ_select_change.side_effect = capture_champ_select_callback
        await state_manager.initialize()  # Re-initialize to capture callback
        
        session = ChampSelectSession(
            local_player_cell_id=0,
            my_team=[{
                "cellId": 0,
                "championId": 157,  # Yasuo
                "assignedPosition": "middle"
            }],
            timer={"phase": "BAN_PICK"},
            actions=[[]],
            raw_data={}
        )
        
        # Step 3: System fetches presets for the champion
        # Mock preset provider to return 3 presets
        preset1 = RunePage(
            name="Yasuo - Lethal Tempo",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8008, 9111, 9104, 8014, 8126, 8138],
            statShards=[5005, 5008, 5001]
        )
        preset2 = RunePage(
            name="Yasuo - Conqueror",
            primaryStyleId=8000,
            subStyleId=8200,
            selectedPerkIds=[8010, 9111, 9104, 8014, 8210, 8236],
            statShards=[5005, 5008, 5001]
        )
        preset3 = RunePage(
            name="Yasuo - Fleet Footwork",
            primaryStyleId=8000,
            subStyleId=8400,
            selectedPerkIds=[8021, 9111, 9104, 8014, 8429, 8451],
            statShards=[5005, 5008, 5001]
        )
        
        mock_preset_provider.get_presets.return_value = [preset1, preset2, preset3]
        
        # Trigger champion select change
        assert champ_select_callback is not None
        await champ_select_callback(session)
        
        # Verify presets were fetched (Requirement 4.1, 4.2)
        mock_preset_provider.get_presets.assert_called_once()
        call_args = mock_preset_provider.get_presets.call_args[0][0]
        assert call_args.championId == 157
        assert call_args.role == "middle"
        
        # Verify state contains presets (Requirement 4.3, 4.5)
        state = state_manager.get_current_state()
        assert len(state.available_presets) == 3
        assert state.available_presets[0].name == "Yasuo - Lethal Tempo"
        assert state.available_presets[1].name == "Yasuo - Conqueror"
        assert state.available_presets[2].name == "Yasuo - Fleet Footwork"
        
        # Step 4: User selects preset 1 (Conqueror)
        # Register a callback to verify state change broadcast
        callback_called = False
        callback_state = None
        
        def state_change_callback(state: AppState):
            nonlocal callback_called, callback_state
            callback_called = True
            callback_state = state
        
        state_manager.on_state_change(state_change_callback)
        
        # Mock controller to return updated slots after application
        updated_slots = [
            AppSlot(slotIndex=0, pageId=1, name="App Slot 1", currentPage=None, isActive=False),
            AppSlot(slotIndex=1, pageId=2, name="App Slot 2", currentPage=preset2, isActive=True),
            AppSlot(slotIndex=2, pageId=3, name="App Slot 3", currentPage=None, isActive=False),
        ]
        mock_rune_page_controller.get_app_slots.return_value = updated_slots
        
        # Select preset 1 (index 1)
        await state_manager.select_preset(1)
        
        # Step 5: Verify preset was applied to app slot (Requirement 6.1, 6.2, 6.3)
        mock_rune_page_controller.apply_preset_to_slot.assert_called_once_with(preset2, 1)
        
        # Verify state was updated (Requirement 6.4)
        state = state_manager.get_current_state()
        assert state.selected_preset_index == 1
        assert state.active_slot_index == 1
        assert state.app_slots[1].isActive is True
        assert state.app_slots[1].currentPage == preset2
        assert state.app_slots[0].isActive is False
        assert state.app_slots[2].isActive is False
        
        # Step 6: Verify state change was broadcast
        assert callback_called
        assert callback_state is not None
        assert callback_state.selected_preset_index == 1
        assert callback_state.active_slot_index == 1
    
    @pytest.mark.asyncio
    async def test_selecting_different_presets_to_different_slots(
        self, state_manager, mock_preset_provider, mock_rune_page_controller
    ):
        """
        Test that users can select different presets to different slots
        
        This validates that the system correctly manages multiple app slots
        """
        await state_manager.initialize()
        
        # Set up three presets
        preset1 = RunePage(
            name="Preset 1",
            primaryStyleId=8100,
            subStyleId=8200,
            selectedPerkIds=[8112, 8126, 8138, 8106, 8210, 8236],
            statShards=[5008, 5008, 5002]
        )
        preset2 = RunePage(
            name="Preset 2",
            primaryStyleId=8300,
            subStyleId=8100,
            selectedPerkIds=[8351, 8304, 8345, 8347, 8112, 8126],
            statShards=[5005, 5008, 5001]
        )
        preset3 = RunePage(
            name="Preset 3",
            primaryStyleId=8000,
            subStyleId=8400,
            selectedPerkIds=[8005, 8008, 8021, 9103, 8429, 8451],
            statShards=[5008, 5002, 5003]
        )
        
        state_manager._state.available_presets = [preset1, preset2, preset3]
        
        # Track state changes
        state_changes = []
        def track_state_changes(state: AppState):
            state_changes.append({
                "selected_preset_index": state.selected_preset_index,
                "active_slot_index": state.active_slot_index
            })
        
        state_manager.on_state_change(track_state_changes)
        
        # Select preset 0 to slot 0
        mock_rune_page_controller.get_app_slots.return_value = [
            AppSlot(slotIndex=0, pageId=1, name="App Slot 1", currentPage=preset1, isActive=True),
            AppSlot(slotIndex=1, pageId=2, name="App Slot 2", currentPage=None, isActive=False),
            AppSlot(slotIndex=2, pageId=3, name="App Slot 3", currentPage=None, isActive=False),
        ]
        await state_manager.select_preset(0)
        
        # Select preset 1 to slot 1
        mock_rune_page_controller.get_app_slots.return_value = [
            AppSlot(slotIndex=0, pageId=1, name="App Slot 1", currentPage=preset1, isActive=False),
            AppSlot(slotIndex=1, pageId=2, name="App Slot 2", currentPage=preset2, isActive=True),
            AppSlot(slotIndex=2, pageId=3, name="App Slot 3", currentPage=None, isActive=False),
        ]
        await state_manager.select_preset(1)
        
        # Select preset 2 to slot 2
        mock_rune_page_controller.get_app_slots.return_value = [
            AppSlot(slotIndex=0, pageId=1, name="App Slot 1", currentPage=preset1, isActive=False),
            AppSlot(slotIndex=1, pageId=2, name="App Slot 2", currentPage=preset2, isActive=False),
            AppSlot(slotIndex=2, pageId=3, name="App Slot 3", currentPage=preset3, isActive=True),
        ]
        await state_manager.select_preset(2)
        
        # Verify all three presets were applied to their respective slots
        assert mock_rune_page_controller.apply_preset_to_slot.call_count == 3
        
        # Verify state changes were broadcast for each selection
        assert len(state_changes) == 3
        assert state_changes[0] == {"selected_preset_index": 0, "active_slot_index": 0}
        assert state_changes[1] == {"selected_preset_index": 1, "active_slot_index": 1}
        assert state_changes[2] == {"selected_preset_index": 2, "active_slot_index": 2}
        
        # Verify final state
        final_state = state_manager.get_current_state()
        assert final_state.selected_preset_index == 2
        assert final_state.active_slot_index == 2
        assert final_state.app_slots[0].currentPage == preset1
        assert final_state.app_slots[1].currentPage == preset2
        assert final_state.app_slots[2].currentPage == preset3
        assert final_state.app_slots[2].isActive is True
    
    @pytest.mark.asyncio
    async def test_preset_selection_error_handling(
        self, state_manager, mock_preset_provider, mock_rune_page_controller
    ):
        """
        Test that errors during preset application are handled correctly
        
        This validates Requirement 6.6: If LCU API call fails, throw error and don't update state
        """
        await state_manager.initialize()
        
        # Set up preset
        preset = RunePage(
            name="Test Preset",
            primaryStyleId=8100,
            subStyleId=8200,
            selectedPerkIds=[8112, 8126, 8138, 8106, 8210, 8236],
            statShards=[5008, 5008, 5002]
        )
        state_manager._state.available_presets = [preset]
        
        # Get initial state
        initial_state = state_manager.get_current_state()
        initial_selected_index = initial_state.selected_preset_index
        initial_active_slot = initial_state.active_slot_index
        
        # Mock controller to raise error
        mock_rune_page_controller.apply_preset_to_slot.side_effect = ConnectionError(
            "Failed to connect to LCU API"
        )
        
        # Attempt to select preset should raise error
        with pytest.raises(ConnectionError, match="Failed to connect to LCU API"):
            await state_manager.select_preset(0)
        
        # Verify state was NOT updated (Requirement 6.6)
        final_state = state_manager.get_current_state()
        assert final_state.selected_preset_index == initial_selected_index
        assert final_state.active_slot_index == initial_active_slot
