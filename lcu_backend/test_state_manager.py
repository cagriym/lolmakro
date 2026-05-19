# Unit tests for State Manager component

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from .state_manager import StateManager, AppState
from .lcu_monitor import LCUMonitor, GameflowPhase, ChampSelectSession
from .context_extractor import ChampSelectContext
from .preset_provider import PresetProvider, RunePage, RuneContext
from .rune_page_controller import RunePageController, AppSlot, RuneSlotType


@pytest.fixture
def mock_lcu_monitor():
    """Create a mock LCU Monitor"""
    monitor = Mock(spec=LCUMonitor)
    monitor.start = AsyncMock()
    monitor.stop = AsyncMock()
    monitor.on_gameflow_change = Mock()
    monitor.on_champ_select_change = Mock()
    monitor.get_gameflow_phase = AsyncMock(return_value=None)
    return monitor


@pytest.fixture
def mock_preset_provider():
    """Create a mock Preset Provider"""
    provider = Mock(spec=PresetProvider)
    provider.get_presets = Mock(return_value=[])
    provider.get_rune_metadata = Mock(return_value=None)
    return provider


@pytest.fixture
def mock_rune_page_controller():
    """Create a mock Rune Page Controller"""
    controller = Mock(spec=RunePageController)
    controller.initialize = AsyncMock()
    controller.get_app_slots = Mock(return_value=[
        AppSlot(slotIndex=0, pageId=1, name="App Slot 1", currentPage=None, isActive=False),
        AppSlot(slotIndex=1, pageId=2, name="App Slot 2", currentPage=None, isActive=False),
        AppSlot(slotIndex=2, pageId=3, name="App Slot 3", currentPage=None, isActive=False),
    ])
    controller.get_active_slot = Mock(return_value=None)
    controller.apply_preset_to_slot = AsyncMock()
    controller.update_rune_in_active_slot = AsyncMock()
    return controller


@pytest.fixture
def state_manager(mock_lcu_monitor, mock_preset_provider, mock_rune_page_controller):
    """Create a State Manager instance with mocked dependencies"""
    return StateManager(
        lcu_monitor=mock_lcu_monitor,
        preset_provider=mock_preset_provider,
        rune_page_controller=mock_rune_page_controller
    )


class TestStateManagerInitialization:
    """Test State Manager initialization"""
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, state_manager, mock_rune_page_controller, mock_lcu_monitor):
        """Test successful initialization"""
        await state_manager.initialize()
        
        # Verify components initialized
        mock_rune_page_controller.initialize.assert_called_once()
        mock_lcu_monitor.start.assert_called_once()
        
        # Verify event handlers registered
        assert mock_lcu_monitor.on_gameflow_change.called
        assert mock_lcu_monitor.on_champ_select_change.called
        
        # Verify state manager is initialized
        assert state_manager.is_initialized()
    
    @pytest.mark.asyncio
    async def test_initialize_loads_app_slots(self, state_manager, mock_rune_page_controller):
        """Test that initialization loads app slots into state"""
        await state_manager.initialize()
        
        state = state_manager.get_current_state()
        assert len(state.app_slots) == 3
        assert state.app_slots[0].name == "App Slot 1"
        assert state.app_slots[1].name == "App Slot 2"
        assert state.app_slots[2].name == "App Slot 3"
    
    @pytest.mark.asyncio
    async def test_initialize_detects_active_slot(self, state_manager, mock_rune_page_controller):
        """Test that initialization detects active slot"""
        active_slot = AppSlot(slotIndex=1, pageId=2, name="App Slot 2", currentPage=None, isActive=True)
        mock_rune_page_controller.get_active_slot.return_value = active_slot
        
        await state_manager.initialize()
        
        state = state_manager.get_current_state()
        assert state.active_slot_index == 1
    
    @pytest.mark.asyncio
    async def test_shutdown_stops_monitoring(self, state_manager, mock_lcu_monitor):
        """Test that shutdown stops monitoring"""
        await state_manager.initialize()
        await state_manager.shutdown()
        
        mock_lcu_monitor.stop.assert_called_once()
        assert not state_manager.is_initialized()


class TestStateManagerGameflowHandling:
    """Test gameflow phase change handling"""
    
    @pytest.mark.asyncio
    async def test_gameflow_change_updates_state(self, state_manager):
        """Test that gameflow changes update state"""
        await state_manager.initialize()
        
        # Simulate gameflow change
        await state_manager._handle_gameflow_change(GameflowPhase.CHAMP_SELECT)
        
        state = state_manager.get_current_state()
        assert state.gameflow_phase == GameflowPhase.CHAMP_SELECT
    
    @pytest.mark.asyncio
    async def test_leaving_champ_select_clears_context(self, state_manager):
        """Test that leaving ChampSelect clears context and presets"""
        await state_manager.initialize()
        
        # Set up state with context and presets
        state_manager._state.champ_select_context = ChampSelectContext(
            champion_id=1, queue_id=420, role="middle", phase="BAN_PICK"
        )
        state_manager._state.available_presets = [Mock(spec=RunePage)]
        state_manager._state.selected_preset_index = 0
        
        # Simulate leaving ChampSelect
        await state_manager._handle_gameflow_change(GameflowPhase.LOBBY)
        
        state = state_manager.get_current_state()
        assert state.champ_select_context is None
        assert state.available_presets == []
        assert state.selected_preset_index is None
    
    @pytest.mark.asyncio
    async def test_gameflow_change_notifies_callbacks(self, state_manager):
        """Test that gameflow changes trigger state change callbacks"""
        await state_manager.initialize()
        
        callback = Mock()
        state_manager.on_state_change(callback)
        
        await state_manager._handle_gameflow_change(GameflowPhase.LOBBY)
        
        # Should be called twice: once during initialize, once for gameflow change
        assert callback.call_count >= 1


class TestStateManagerChampSelectHandling:
    """Test champion select session change handling"""
    
    @pytest.mark.asyncio
    async def test_champ_select_change_with_no_session(self, state_manager):
        """Test handling champion select change with None session"""
        await state_manager.initialize()
        
        # Set up state with context
        state_manager._state.champ_select_context = ChampSelectContext(
            champion_id=1, queue_id=420, role="middle", phase="BAN_PICK"
        )
        state_manager._state.available_presets = [Mock(spec=RunePage)]
        
        # Simulate session ending
        await state_manager._handle_champ_select_change(None)
        
        state = state_manager.get_current_state()
        assert state.champ_select_context is None
        assert state.available_presets == []
    
    @pytest.mark.asyncio
    async def test_champ_select_change_with_no_champion(self, state_manager):
        """Test handling champion select when no champion selected"""
        await state_manager.initialize()
        
        # Create session with no champion selected
        session = ChampSelectSession(
            local_player_cell_id=0,
            my_team=[{"cellId": 0, "championId": 0, "assignedPosition": ""}],
            timer={"phase": "PLANNING"},
            actions=[],
            raw_data={}
        )
        
        await state_manager._handle_champ_select_change(session)
        
        state = state_manager.get_current_state()
        assert state.champ_select_context is None
        assert state.available_presets == []
    
    @pytest.mark.asyncio
    async def test_champ_select_change_queries_presets(self, state_manager, mock_preset_provider):
        """Test that champion select change queries presets"""
        await state_manager.initialize()
        
        # Create session with champion selected
        session = ChampSelectSession(
            local_player_cell_id=0,
            my_team=[{"cellId": 0, "championId": 157, "assignedPosition": "middle"}],
            timer={"phase": "BAN_PICK"},
            actions=[],
            raw_data={"queueId": 420}
        )
        
        # Mock preset provider to return presets
        preset1 = RunePage(
            name="Preset 1",
            primaryStyleId=8100,
            subStyleId=8200,
            selectedPerkIds=[8112, 8126, 8138, 8106, 8210, 8236],
            statShards=[5008, 5008, 5002]
        )
        mock_preset_provider.get_presets.return_value = [preset1]
        
        await state_manager._handle_champ_select_change(session)
        
        # Verify preset provider was called
        mock_preset_provider.get_presets.assert_called_once()
        call_args = mock_preset_provider.get_presets.call_args[0][0]
        assert call_args.championId == 157
        assert call_args.role == "middle"
        
        # Verify state updated
        state = state_manager.get_current_state()
        assert state.champ_select_context is not None
        assert state.champ_select_context.champion_id == 157
        assert len(state.available_presets) == 1
    
    @pytest.mark.asyncio
    async def test_champ_select_change_only_updates_on_context_change(
        self, state_manager, mock_preset_provider
    ):
        """Test that presets are only queried when context changes"""
        await state_manager.initialize()
        
        # Create session
        session = ChampSelectSession(
            local_player_cell_id=0,
            my_team=[{"cellId": 0, "championId": 157, "assignedPosition": "middle"}],
            timer={"phase": "BAN_PICK"},
            actions=[],
            raw_data={"queueId": 420}
        )
        
        # First change
        await state_manager._handle_champ_select_change(session)
        assert mock_preset_provider.get_presets.call_count == 1
        
        # Same session again (no context change)
        await state_manager._handle_champ_select_change(session)
        # Should not query presets again
        assert mock_preset_provider.get_presets.call_count == 1


class TestStateManagerPresetSelection:
    """Test preset selection workflow"""
    
    @pytest.mark.asyncio
    async def test_select_preset_applies_to_slot(
        self, state_manager, mock_rune_page_controller, mock_preset_provider
    ):
        """Test that selecting a preset applies it to the correct slot"""
        await state_manager.initialize()
        
        # Set up presets
        preset1 = RunePage(
            name="Preset 1",
            primaryStyleId=8100,
            subStyleId=8200,
            selectedPerkIds=[8112, 8126, 8138, 8106, 8210, 8236],
            statShards=[5008, 5008, 5002]
        )
        state_manager._state.available_presets = [preset1]
        
        # Select preset
        await state_manager.select_preset(0)
        
        # Verify controller was called
        mock_rune_page_controller.apply_preset_to_slot.assert_called_once_with(preset1, 0)
        
        # Verify state updated
        state = state_manager.get_current_state()
        assert state.selected_preset_index == 0
        assert state.active_slot_index == 0
    
    @pytest.mark.asyncio
    async def test_select_preset_invalid_index(self, state_manager):
        """Test that selecting invalid preset index raises error"""
        await state_manager.initialize()
        
        state_manager._state.available_presets = [Mock(spec=RunePage)]
        
        with pytest.raises(ValueError, match="Invalid preset_index"):
            await state_manager.select_preset(5)
    
    @pytest.mark.asyncio
    async def test_select_preset_not_initialized(self, state_manager):
        """Test that selecting preset before initialization raises error"""
        with pytest.raises(RuntimeError, match="not initialized"):
            await state_manager.select_preset(0)
    
    @pytest.mark.asyncio
    async def test_select_preset_notifies_callbacks(
        self, state_manager, mock_rune_page_controller
    ):
        """Test that selecting a preset triggers state change callbacks"""
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
        
        # Register callback
        callback_called = False
        callback_state = None
        
        def callback(state: AppState):
            nonlocal callback_called, callback_state
            callback_called = True
            callback_state = state
        
        state_manager.on_state_change(callback)
        
        # Select preset
        await state_manager.select_preset(0)
        
        # Verify callback was called
        assert callback_called
        assert callback_state is not None
        assert callback_state.selected_preset_index == 0
        assert callback_state.active_slot_index == 0
    
    @pytest.mark.asyncio
    async def test_select_preset_updates_app_slots(
        self, state_manager, mock_rune_page_controller
    ):
        """Test that selecting a preset updates app slots from controller"""
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
        
        # Mock updated slots from controller
        updated_slots = [
            AppSlot(slotIndex=0, pageId=1, name="App Slot 1", currentPage=preset, isActive=True),
            AppSlot(slotIndex=1, pageId=2, name="App Slot 2", currentPage=None, isActive=False),
            AppSlot(slotIndex=2, pageId=3, name="App Slot 3", currentPage=None, isActive=False),
        ]
        mock_rune_page_controller.get_app_slots.return_value = updated_slots
        
        # Select preset
        await state_manager.select_preset(0)
        
        # Verify app slots were updated from controller
        state = state_manager.get_current_state()
        assert len(state.app_slots) == 3
        assert state.app_slots[0].isActive is True
        assert state.app_slots[0].currentPage == preset
        assert state.app_slots[1].isActive is False
        assert state.app_slots[2].isActive is False
    
    @pytest.mark.asyncio
    async def test_select_multiple_presets_to_different_slots(
        self, state_manager, mock_rune_page_controller
    ):
        """Test that multiple presets can be selected to different slots"""
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
        
        # Select preset 1 to slot 0
        await state_manager.select_preset(0)
        mock_rune_page_controller.apply_preset_to_slot.assert_called_with(preset1, 0)
        assert state_manager.get_current_state().selected_preset_index == 0
        assert state_manager.get_current_state().active_slot_index == 0
        
        # Select preset 2 to slot 1
        await state_manager.select_preset(1)
        mock_rune_page_controller.apply_preset_to_slot.assert_called_with(preset2, 1)
        assert state_manager.get_current_state().selected_preset_index == 1
        assert state_manager.get_current_state().active_slot_index == 1
        
        # Select preset 3 to slot 2
        await state_manager.select_preset(2)
        mock_rune_page_controller.apply_preset_to_slot.assert_called_with(preset3, 2)
        assert state_manager.get_current_state().selected_preset_index == 2
        assert state_manager.get_current_state().active_slot_index == 2
    
    @pytest.mark.asyncio
    async def test_select_preset_handles_controller_error(
        self, state_manager, mock_rune_page_controller
    ):
        """Test that controller errors are propagated when selecting preset"""
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
        
        # Mock controller to raise error
        mock_rune_page_controller.apply_preset_to_slot.side_effect = ConnectionError("LCU API failed")
        
        # Attempt to select preset should raise error
        with pytest.raises(ConnectionError, match="LCU API failed"):
            await state_manager.select_preset(0)


class TestStateManagerRuneEditing:
    """Test rune editing workflow"""
    
    @pytest.mark.asyncio
    async def test_edit_rune_updates_active_slot(
        self, state_manager, mock_rune_page_controller, mock_preset_provider
    ):
        """Test that editing a rune updates the active slot"""
        await state_manager.initialize()
        
        # Mock rune metadata
        from .preset_provider import RuneMetadata
        rune_metadata = RuneMetadata(
            id=8128, key="DarkHarvest", name="Dark Harvest",
            shortDesc="Test", icon="test.png", styleId=8100, slot=0
        )
        mock_preset_provider.get_rune_metadata.return_value = rune_metadata
        
        # Edit rune
        await state_manager.edit_rune(8128, RuneSlotType.KEYSTONE)
        
        # Verify controller was called
        mock_rune_page_controller.update_rune_in_active_slot.assert_called_once_with(
            8128, RuneSlotType.KEYSTONE, rune_metadata
        )
    
    @pytest.mark.asyncio
    async def test_edit_rune_not_initialized(self, state_manager):
        """Test that editing rune before initialization raises error"""
        with pytest.raises(RuntimeError, match="not initialized"):
            await state_manager.edit_rune(8128, RuneSlotType.KEYSTONE)
    
    @pytest.mark.asyncio
    async def test_edit_rune_validates_compatibility(
        self, state_manager, mock_rune_page_controller, mock_preset_provider
    ):
        """Test that editing a rune validates compatibility through metadata"""
        await state_manager.initialize()
        
        # Mock rune metadata
        from .preset_provider import RuneMetadata
        rune_metadata = RuneMetadata(
            id=8112, key="Electrocute", name="Electrocute",
            shortDesc="Test", icon="test.png", styleId=8100, slot=0
        )
        mock_preset_provider.get_rune_metadata.return_value = rune_metadata
        
        # Edit rune
        await state_manager.edit_rune(8112, RuneSlotType.PRIMARY1)
        
        # Verify metadata was fetched for validation
        mock_preset_provider.get_rune_metadata.assert_called_once_with(8112)
        
        # Verify controller received metadata for validation
        mock_rune_page_controller.update_rune_in_active_slot.assert_called_once_with(
            8112, RuneSlotType.PRIMARY1, rune_metadata
        )
    
    @pytest.mark.asyncio
    async def test_edit_rune_updates_app_slots_state(
        self, state_manager, mock_rune_page_controller, mock_preset_provider
    ):
        """Test that editing a rune updates app slots in state"""
        await state_manager.initialize()
        
        # Mock rune metadata
        from .preset_provider import RuneMetadata
        rune_metadata = RuneMetadata(
            id=8128, key="DarkHarvest", name="Dark Harvest",
            shortDesc="Test", icon="test.png", styleId=8100, slot=0
        )
        mock_preset_provider.get_rune_metadata.return_value = rune_metadata
        
        # Mock updated slots from controller
        updated_preset = RunePage(
            name="Updated Preset",
            primaryStyleId=8100,
            subStyleId=8200,
            selectedPerkIds=[8128, 8126, 8138, 8106, 8210, 8236],  # Updated keystone
            statShards=[5008, 5008, 5002]
        )
        updated_slots = [
            AppSlot(slotIndex=0, pageId=1, name="App Slot 1", currentPage=updated_preset, isActive=True),
            AppSlot(slotIndex=1, pageId=2, name="App Slot 2", currentPage=None, isActive=False),
            AppSlot(slotIndex=2, pageId=3, name="App Slot 3", currentPage=None, isActive=False),
        ]
        mock_rune_page_controller.get_app_slots.return_value = updated_slots
        
        # Edit rune
        await state_manager.edit_rune(8128, RuneSlotType.KEYSTONE)
        
        # Verify app slots were updated from controller
        state = state_manager.get_current_state()
        assert len(state.app_slots) == 3
        assert state.app_slots[0].currentPage.selectedPerkIds[0] == 8128
    
    @pytest.mark.asyncio
    async def test_edit_rune_notifies_callbacks(
        self, state_manager, mock_rune_page_controller, mock_preset_provider
    ):
        """Test that editing a rune triggers state change callbacks"""
        await state_manager.initialize()
        
        # Mock rune metadata
        from .preset_provider import RuneMetadata
        rune_metadata = RuneMetadata(
            id=8128, key="DarkHarvest", name="Dark Harvest",
            shortDesc="Test", icon="test.png", styleId=8100, slot=0
        )
        mock_preset_provider.get_rune_metadata.return_value = rune_metadata
        
        # Register callback
        callback_called = False
        callback_state = None
        
        def callback(state: AppState):
            nonlocal callback_called, callback_state
            callback_called = True
            callback_state = state
        
        state_manager.on_state_change(callback)
        
        # Edit rune
        await state_manager.edit_rune(8128, RuneSlotType.KEYSTONE)
        
        # Verify callback was called
        assert callback_called
        assert callback_state is not None
    
    @pytest.mark.asyncio
    async def test_edit_rune_handles_controller_error(
        self, state_manager, mock_rune_page_controller, mock_preset_provider
    ):
        """Test that controller errors are propagated when editing rune"""
        await state_manager.initialize()
        
        # Mock rune metadata
        from .preset_provider import RuneMetadata
        rune_metadata = RuneMetadata(
            id=8128, key="DarkHarvest", name="Dark Harvest",
            shortDesc="Test", icon="test.png", styleId=8100, slot=0
        )
        mock_preset_provider.get_rune_metadata.return_value = rune_metadata
        
        # Mock controller to raise error
        mock_rune_page_controller.update_rune_in_active_slot.side_effect = ValueError(
            "Rune incompatible with slot"
        )
        
        # Attempt to edit rune should raise error
        with pytest.raises(ValueError, match="incompatible"):
            await state_manager.edit_rune(8128, RuneSlotType.KEYSTONE)
    
    @pytest.mark.asyncio
    async def test_edit_rune_with_different_slot_types(
        self, state_manager, mock_rune_page_controller, mock_preset_provider
    ):
        """Test editing runes in different slot types"""
        await state_manager.initialize()
        
        # Mock rune metadata
        from .preset_provider import RuneMetadata
        
        # Test keystone
        keystone_metadata = RuneMetadata(
            id=8128, key="DarkHarvest", name="Dark Harvest",
            shortDesc="Test", icon="test.png", styleId=8100, slot=0
        )
        mock_preset_provider.get_rune_metadata.return_value = keystone_metadata
        await state_manager.edit_rune(8128, RuneSlotType.KEYSTONE)
        mock_rune_page_controller.update_rune_in_active_slot.assert_called_with(
            8128, RuneSlotType.KEYSTONE, keystone_metadata
        )
        
        # Test primary slot
        primary_metadata = RuneMetadata(
            id=8126, key="CheapShot", name="Cheap Shot",
            shortDesc="Test", icon="test.png", styleId=8100, slot=1
        )
        mock_preset_provider.get_rune_metadata.return_value = primary_metadata
        await state_manager.edit_rune(8126, RuneSlotType.PRIMARY1)
        mock_rune_page_controller.update_rune_in_active_slot.assert_called_with(
            8126, RuneSlotType.PRIMARY1, primary_metadata
        )
        
        # Test secondary slot
        secondary_metadata = RuneMetadata(
            id=8210, key="Transcendence", name="Transcendence",
            shortDesc="Test", icon="test.png", styleId=8200, slot=1
        )
        mock_preset_provider.get_rune_metadata.return_value = secondary_metadata
        await state_manager.edit_rune(8210, RuneSlotType.SECONDARY1)
        mock_rune_page_controller.update_rune_in_active_slot.assert_called_with(
            8210, RuneSlotType.SECONDARY1, secondary_metadata
        )
        
        # Test stat shard
        stat_shard_metadata = RuneMetadata(
            id=5008, key="StatModsAdaptiveForceIcon", name="Adaptive Force",
            shortDesc="Test", icon="test.png", styleId=0, slot=0
        )
        mock_preset_provider.get_rune_metadata.return_value = stat_shard_metadata
        await state_manager.edit_rune(5008, RuneSlotType.STAT_SHARD1)
        mock_rune_page_controller.update_rune_in_active_slot.assert_called_with(
            5008, RuneSlotType.STAT_SHARD1, stat_shard_metadata
        )
    
    @pytest.mark.asyncio
    async def test_edit_rune_coordinates_through_controller(
        self, state_manager, mock_rune_page_controller, mock_preset_provider
    ):
        """Test that rune editing is coordinated through the controller"""
        await state_manager.initialize()
        
        # Mock rune metadata
        from .preset_provider import RuneMetadata
        rune_metadata = RuneMetadata(
            id=8112, key="Electrocute", name="Electrocute",
            shortDesc="Test", icon="test.png", styleId=8100, slot=0
        )
        mock_preset_provider.get_rune_metadata.return_value = rune_metadata
        
        # Edit rune
        await state_manager.edit_rune(8112, RuneSlotType.KEYSTONE)
        
        # Verify state manager doesn't directly modify state
        # but delegates to controller
        mock_rune_page_controller.update_rune_in_active_slot.assert_called_once()
        
        # Verify state manager fetches updated state from controller
        assert mock_rune_page_controller.get_app_slots.called


class TestStateManagerEditMode:
    """Test edit mode management"""
    
    @pytest.mark.asyncio
    async def test_set_edit_mode_updates_state(self, state_manager):
        """Test that setting edit mode updates state"""
        await state_manager.initialize()
        
        await state_manager.set_edit_mode(True)
        
        state = state_manager.get_current_state()
        assert state.is_edit_mode is True
    
    @pytest.mark.asyncio
    async def test_set_edit_mode_notifies_callbacks(self, state_manager):
        """Test that setting edit mode triggers callbacks"""
        await state_manager.initialize()
        
        callback = Mock()
        state_manager.on_state_change(callback)
        
        await state_manager.set_edit_mode(True)
        
        assert callback.called


class TestStateManagerCallbacks:
    """Test state change callback system"""
    
    @pytest.mark.asyncio
    async def test_sync_callback_called(self, state_manager):
        """Test that synchronous callbacks are called"""
        await state_manager.initialize()
        
        callback = Mock()
        state_manager.on_state_change(callback)
        
        await state_manager._handle_gameflow_change(GameflowPhase.LOBBY)
        
        assert callback.called
        # Verify callback received AppState
        call_args = callback.call_args[0][0]
        assert isinstance(call_args, AppState)
    
    @pytest.mark.asyncio
    async def test_async_callback_called(self, state_manager):
        """Test that asynchronous callbacks are called"""
        await state_manager.initialize()
        
        callback = AsyncMock()
        state_manager.on_state_change(callback)
        
        await state_manager._handle_gameflow_change(GameflowPhase.LOBBY)
        
        assert callback.called
    
    @pytest.mark.asyncio
    async def test_callback_error_does_not_break_others(self, state_manager):
        """Test that callback errors don't prevent other callbacks from running"""
        await state_manager.initialize()
        
        # Create callbacks: one that raises, one that succeeds
        bad_callback = Mock(side_effect=Exception("Test error"))
        good_callback = Mock()
        
        state_manager.on_state_change(bad_callback)
        state_manager.on_state_change(good_callback)
        
        # Should not raise
        await state_manager._handle_gameflow_change(GameflowPhase.LOBBY)
        
        # Both should be called
        assert bad_callback.called
        assert good_callback.called


class TestStateManagerGetState:
    """Test getting current state"""
    
    @pytest.mark.asyncio
    async def test_get_current_state_returns_copy(self, state_manager):
        """Test that get_current_state returns a copy"""
        await state_manager.initialize()
        
        state1 = state_manager.get_current_state()
        state2 = state_manager.get_current_state()
        
        # Should be different objects
        assert state1 is not state2
        
        # But with same values
        assert state1.gameflow_phase == state2.gameflow_phase
    
    @pytest.mark.asyncio
    async def test_get_current_state_prevents_external_modification(self, state_manager):
        """Test that external modifications don't affect internal state"""
        await state_manager.initialize()
        
        state = state_manager.get_current_state()
        state.gameflow_phase = GameflowPhase.IN_PROGRESS
        
        # Internal state should not be affected
        internal_state = state_manager.get_current_state()
        assert internal_state.gameflow_phase != GameflowPhase.IN_PROGRESS
