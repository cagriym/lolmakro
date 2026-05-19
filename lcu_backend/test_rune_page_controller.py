# Tests for Rune Page Controller component

import pytest
from unittest.mock import AsyncMock, MagicMock

from lcu_backend.rune_page_controller import RunePageController, AppSlot
from lcu_backend.lcu_connection import LCUConnection
from lcu_backend.preset_provider import RunePage


@pytest.fixture
def mock_lcu():
    """Create a mock LCU connection"""
    lcu = MagicMock(spec=LCUConnection)
    lcu.is_connected = AsyncMock(return_value=True)
    lcu.get = AsyncMock()
    lcu.post = AsyncMock()
    lcu.patch = AsyncMock()
    lcu.put = AsyncMock()
    return lcu


@pytest.fixture
def controller(mock_lcu):
    """Create a RunePageController instance"""
    return RunePageController(mock_lcu)


class TestAppSlotInitialization:
    """Tests for app slot initialization (Task 4.1)"""
    
    @pytest.mark.asyncio
    async def test_initialize_creates_three_slots_when_none_exist(self, controller, mock_lcu):
        """Test that initialize creates three new slots when none exist"""
        # Mock: No existing pages
        mock_lcu.get.return_value = []
        
        # Mock: POST requests return page IDs
        mock_lcu.post.side_effect = [
            {"id": 1},
            {"id": 2},
            {"id": 3}
        ]
        
        await controller.initialize()
        
        # Verify three slots created
        slots = controller.get_app_slots()
        assert len(slots) == 3
        
        # Verify slot properties
        for i, slot in enumerate(slots):
            assert slot.slotIndex == i
            assert slot.name == f"App Slot {i + 1}"
            assert slot.pageId == i + 1
            assert slot.currentPage is None
            assert slot.isActive is False
        
        # Verify POST was called three times
        assert mock_lcu.post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_initialize_reuses_existing_slots(self, controller, mock_lcu):
        """Test that initialize reuses existing app slots instead of creating duplicates"""
        # Mock: Existing app slots already present
        existing_pages = [
            {"id": 10, "name": "App Slot 1", "current": False},
            {"id": 11, "name": "App Slot 2", "current": True},
            {"id": 12, "name": "App Slot 3", "current": False},
        ]
        mock_lcu.get.return_value = existing_pages
        
        await controller.initialize()
        
        # Verify three slots reused
        slots = controller.get_app_slots()
        assert len(slots) == 3
        
        # Verify slot properties match existing pages
        assert slots[0].pageId == 10
        assert slots[0].isActive is False
        assert slots[1].pageId == 11
        assert slots[1].isActive is True
        assert slots[2].pageId == 12
        assert slots[2].isActive is False
        
        # Verify POST was never called (reused existing)
        assert mock_lcu.post.call_count == 0
    
    @pytest.mark.asyncio
    async def test_initialize_creates_missing_slots(self, controller, mock_lcu):
        """Test that initialize creates only missing slots"""
        # Mock: Only App Slot 1 exists
        existing_pages = [
            {"id": 10, "name": "App Slot 1", "current": False},
            {"id": 20, "name": "User Page 1", "current": False},
        ]
        mock_lcu.get.return_value = existing_pages
        
        # Mock: POST for new slots
        mock_lcu.post.side_effect = [
            {"id": 30},  # App Slot 2
            {"id": 31}   # App Slot 3
        ]
        
        await controller.initialize()
        
        slots = controller.get_app_slots()
        assert len(slots) == 3
        
        # Verify slot 1 was reused
        assert slots[0].pageId == 10
        
        # Verify slots 2 and 3 were created
        assert slots[1].pageId == 30
        assert slots[2].pageId == 31
        
        # Verify POST was called twice
        assert mock_lcu.post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_initialize_handles_slots_in_any_order(self, controller, mock_lcu):
        """Test that initialize correctly identifies slots regardless of order"""
        # Mock: Slots exist but in different order
        existing_pages = [
            {"id": 100, "name": "User Page", "current": False},
            {"id": 30, "name": "App Slot 3", "current": False},
            {"id": 10, "name": "App Slot 1", "current": True},
            {"id": 20, "name": "App Slot 2", "current": False},
        ]
        mock_lcu.get.return_value = existing_pages
        
        await controller.initialize()
        
        slots = controller.get_app_slots()
        
        # Verify correct mapping
        assert slots[0].pageId == 10  # App Slot 1
        assert slots[1].pageId == 20  # App Slot 2
        assert slots[2].pageId == 30  # App Slot 3
    
    @pytest.mark.asyncio
    async def test_initialize_raises_error_when_page_limit_reached(self, controller, mock_lcu):
        """Test that initialize raises error when user has 25 pages and no app slots"""
        # Mock: 25 pages, none are app slots
        existing_pages = [
            {"id": i, "name": f"User Page {i}", "current": False}
            for i in range(25)
        ]
        mock_lcu.get.return_value = existing_pages
        
        with pytest.raises(RuntimeError, match="Page limit reached"):
            await controller.initialize()
    
    @pytest.mark.asyncio
    async def test_initialize_succeeds_when_page_limit_reached_but_slots_exist(self, controller, mock_lcu):
        """Test that initialize succeeds when at page limit but app slots already exist"""
        # Mock: 25 pages including app slots
        existing_pages = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False},
        ]
        existing_pages.extend([
            {"id": i, "name": f"User Page {i}", "current": False}
            for i in range(4, 26)
        ])
        mock_lcu.get.return_value = existing_pages
        
        # Should not raise error
        await controller.initialize()
        
        slots = controller.get_app_slots()
        assert len(slots) == 3
    
    @pytest.mark.asyncio
    async def test_initialize_raises_error_when_not_connected(self, controller, mock_lcu):
        """Test that initialize raises error when LCU not connected"""
        mock_lcu.is_connected.return_value = False
        
        with pytest.raises(ConnectionError, match="League Client not connected"):
            await controller.initialize()
    
    @pytest.mark.asyncio
    async def test_initialize_raises_error_when_get_pages_fails(self, controller, mock_lcu):
        """Test that initialize raises error when fetching pages fails"""
        mock_lcu.get.return_value = None
        
        with pytest.raises(RuntimeError, match="Failed to fetch rune pages"):
            await controller.initialize()
    
    @pytest.mark.asyncio
    async def test_initialize_raises_error_when_post_fails(self, controller, mock_lcu):
        """Test that initialize raises error when creating page fails"""
        mock_lcu.get.return_value = []
        mock_lcu.post.return_value = None  # POST fails
        
        with pytest.raises(RuntimeError, match="Failed to create app slot"):
            await controller.initialize()
    
    @pytest.mark.asyncio
    async def test_default_page_has_valid_structure(self, controller, mock_lcu):
        """Test that default page created has valid structure"""
        mock_lcu.get.return_value = []
        
        # Capture POST payload
        post_payloads = []
        async def capture_post(path, payload):
            post_payloads.append(payload)
            return {"id": len(post_payloads)}
        
        mock_lcu.post.side_effect = capture_post
        
        await controller.initialize()
        
        # Verify default page structure
        assert len(post_payloads) == 3
        
        for i, payload in enumerate(post_payloads):
            assert payload["name"] == f"App Slot {i + 1}"
            assert payload["primaryStyleId"] == 8000  # Precision
            assert payload["subStyleId"] == 8100  # Domination
            assert len(payload["selectedPerkIds"]) == 6
            assert len(payload["selectedPerkIds"]) == 6
            assert payload["isDeletable"] is True
            assert payload["isEditable"] is True
            assert payload["isValid"] is True
    
    @pytest.mark.asyncio
    async def test_get_app_slots_returns_copy(self, controller, mock_lcu):
        """Test that get_app_slots returns a copy to prevent external modification"""
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False},
        ]
        
        await controller.initialize()
        
        slots1 = controller.get_app_slots()
        slots2 = controller.get_app_slots()
        
        # Verify they are different list objects
        assert slots1 is not slots2
        
        # But contain the same data
        assert len(slots1) == len(slots2) == 3
    
    @pytest.mark.asyncio
    async def test_get_app_slots_raises_error_when_not_initialized(self, controller):
        """Test that get_app_slots raises error when not initialized"""
        with pytest.raises(RuntimeError, match="not initialized"):
            controller.get_app_slots()
    
    @pytest.mark.asyncio
    async def test_is_initialized_returns_correct_state(self, controller, mock_lcu):
        """Test that is_initialized returns correct state"""
        assert controller.is_initialized() is False
        
        mock_lcu.get.return_value = []
        mock_lcu.post.side_effect = [
            {"id": 1}, {"id": 2}, {"id": 3}
        ]
        
        await controller.initialize()
        
        assert controller.is_initialized() is True
    
    @pytest.mark.asyncio
    async def test_slot_names_are_correct(self, controller, mock_lcu):
        """Test that slot names follow the required format"""
        mock_lcu.get.return_value = []
        mock_lcu.post.side_effect = [
            {"id": 1}, {"id": 2}, {"id": 3}
        ]
        
        await controller.initialize()
        
        slots = controller.get_app_slots()
        assert slots[0].name == "App Slot 1"
        assert slots[1].name == "App Slot 2"
        assert slots[2].name == "App Slot 3"
    
    @pytest.mark.asyncio
    async def test_initialize_preserves_user_pages(self, controller, mock_lcu):
        """Test that initialize does not modify user-created pages"""
        # Mock: Mix of user pages and app slots
        user_pages = [
            {"id": 100, "name": "My Custom Page", "current": False},
            {"id": 101, "name": "ADC Build", "current": False},
        ]
        app_slots = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False},
        ]
        
        existing_pages = user_pages + app_slots
        mock_lcu.get.return_value = existing_pages
        
        await controller.initialize()
        
        # Verify no POST calls (all slots reused)
        assert mock_lcu.post.call_count == 0
        
        # Verify only app slots are tracked
        slots = controller.get_app_slots()
        assert len(slots) == 3
        assert all(slot.pageId in [1, 2, 3] for slot in slots)


class TestRunePageControllerProperties:
    """Tests for controller properties and constants"""
    
    def test_valid_style_ids_constant(self):
        """Test that VALID_STYLE_IDS contains correct values"""
        assert RunePageController.VALID_STYLE_IDS == {8000, 8100, 8200, 8300, 8400}
    
    def test_max_pages_constant(self):
        """Test that MAX_PAGES is set to 25"""
        assert RunePageController.MAX_PAGES == 25
    
    def test_slot_names_constant(self):
        """Test that SLOT_NAMES contains correct values"""
        assert RunePageController.SLOT_NAMES == ["App Slot 1", "App Slot 2", "App Slot 3"]


class TestPresetApplication:
    """Test preset application to slots"""
    
    @pytest.fixture
    def sample_preset(self):
        """Create a sample preset for testing"""
        return RunePage(
            name="Test Preset",
            primaryStyleId=8000,  # Precision
            subStyleId=8100,  # Domination
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
    
    @pytest.mark.asyncio
    async def test_apply_preset_to_slot_updates_existing_page(self, controller, mock_lcu, sample_preset):
        """Test applying preset to slot with existing page"""
        # Initialize controller
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        # Mock PATCH and PUT responses
        mock_lcu.patch.return_value = {"id": 1, "name": "App Slot 1"}
        mock_lcu.put.return_value = None
        
        # Apply preset to slot 0
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Verify PATCH was called with correct data
        mock_lcu.patch.assert_called_once()
        call_args = mock_lcu.patch.call_args
        assert call_args[0][0] == "/lol-perks/v1/pages/1"
        page_data = call_args[0][1]
        assert page_data["name"] == "App Slot 1"
        assert page_data["primaryStyleId"] == 8000
        assert page_data["subStyleId"] == 8100
        assert page_data["selectedPerkIds"] == [8005, 9111, 9104, 8014, 8126, 8106]
        assert page_data["id"] == 1
        
        # Verify PUT was called to set active page
        mock_lcu.put.assert_called_once_with("/lol-perks/v1/currentpage", 1)
        
        # Verify local state updated
        slots = controller.get_app_slots()
        assert slots[0].currentPage == sample_preset
        assert slots[0].isActive is True
        assert slots[1].isActive is False
        assert slots[2].isActive is False
    
    @pytest.mark.asyncio
    async def test_apply_preset_to_slot_creates_new_page(self, controller, mock_lcu, sample_preset):
        """Test applying preset to slot without existing page"""
        # Initialize controller with no existing pages
        mock_lcu.get.return_value = []
        mock_lcu.post.side_effect = [
            {"id": 1, "name": "App Slot 1"},
            {"id": 2, "name": "App Slot 2"},
            {"id": 3, "name": "App Slot 3"}
        ]
        await controller.initialize()
        
        # Set pageId to None to simulate missing page
        controller._slots[0].pageId = None
        
        # Configure mock for apply_preset_to_slot
        mock_lcu.post.side_effect = None  # Clear side_effect
        mock_lcu.post.return_value = {"id": 10, "name": "App Slot 1"}
        mock_lcu.put.return_value = None
        
        # Apply preset
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Verify POST was called to create page
        call_args = mock_lcu.post.call_args
        assert call_args[0][0] == "/lol-perks/v1/pages"
        page_data = call_args[0][1]
        assert page_data["name"] == "App Slot 1"
        assert page_data["primaryStyleId"] == 8000
        assert "id" not in page_data  # No ID for POST
        
        # Verify PUT was called
        mock_lcu.put.assert_called_once_with("/lol-perks/v1/currentpage", 10)
        
        # Verify pageId was updated
        assert controller._slots[0].pageId == 10
    
    @pytest.mark.asyncio
    async def test_apply_preset_deactivates_other_slots(self, controller, mock_lcu, sample_preset):
        """Test that applying preset deactivates other slots"""
        # Initialize with all slots active
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": True},
            {"id": 2, "name": "App Slot 2", "current": True},
            {"id": 3, "name": "App Slot 3", "current": True}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 2}
        mock_lcu.put.return_value = None
        
        # Apply preset to slot 1
        await controller.apply_preset_to_slot(sample_preset, 1)
        
        # Verify only slot 1 is active
        slots = controller.get_app_slots()
        assert slots[0].isActive is False
        assert slots[1].isActive is True
        assert slots[2].isActive is False
    
    @pytest.mark.asyncio
    async def test_apply_preset_raises_error_when_not_initialized(self, controller, sample_preset):
        """Test that apply_preset_to_slot raises error when not initialized"""
        with pytest.raises(RuntimeError, match="not initialized"):
            await controller.apply_preset_to_slot(sample_preset, 0)
    
    @pytest.mark.asyncio
    async def test_apply_preset_raises_error_for_invalid_slot_index(self, controller, mock_lcu, sample_preset):
        """Test that apply_preset_to_slot raises error for invalid slot index"""
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        with pytest.raises(ValueError, match="Invalid slot_index"):
            await controller.apply_preset_to_slot(sample_preset, 3)
        
        with pytest.raises(ValueError, match="Invalid slot_index"):
            await controller.apply_preset_to_slot(sample_preset, -1)
    
    @pytest.mark.asyncio
    async def test_apply_preset_raises_error_when_patch_fails(self, controller, mock_lcu, sample_preset):
        """Test that apply_preset_to_slot raises error when PATCH fails"""
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = None
        
        with pytest.raises(ConnectionError, match="Failed to update page"):
            await controller.apply_preset_to_slot(sample_preset, 0)
    
    @pytest.mark.asyncio
    async def test_apply_preset_raises_error_when_post_fails(self, controller, mock_lcu, sample_preset):
        """Test that apply_preset_to_slot raises error when POST fails"""
        mock_lcu.get.return_value = []
        mock_lcu.post.side_effect = [
            {"id": 1, "name": "App Slot 1"},
            {"id": 2, "name": "App Slot 2"},
            {"id": 3, "name": "App Slot 3"}
        ]
        await controller.initialize()
        
        # Set pageId to None and make POST fail
        controller._slots[0].pageId = None
        mock_lcu.post.side_effect = None  # Clear side_effect
        mock_lcu.post.return_value = None
        
        with pytest.raises(ConnectionError, match="Failed to create page"):
            await controller.apply_preset_to_slot(sample_preset, 0)


class TestSetActiveSlot:
    """Test setting active slot"""
    
    @pytest.mark.asyncio
    async def test_set_active_slot_updates_lcu(self, controller, mock_lcu):
        """Test that set_active_slot calls LCU API"""
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.put.return_value = None
        
        await controller.set_active_slot(1)
        
        mock_lcu.put.assert_called_once_with("/lol-perks/v1/currentpage", 2)
    
    @pytest.mark.asyncio
    async def test_set_active_slot_updates_local_state(self, controller, mock_lcu):
        """Test that set_active_slot updates local state correctly"""
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": True},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.put.return_value = None
        
        await controller.set_active_slot(2)
        
        slots = controller.get_app_slots()
        assert slots[0].isActive is False
        assert slots[1].isActive is False
        assert slots[2].isActive is True
    
    @pytest.mark.asyncio
    async def test_set_active_slot_raises_error_when_not_initialized(self, controller):
        """Test that set_active_slot raises error when not initialized"""
        with pytest.raises(RuntimeError, match="not initialized"):
            await controller.set_active_slot(0)
    
    @pytest.mark.asyncio
    async def test_set_active_slot_raises_error_for_invalid_index(self, controller, mock_lcu):
        """Test that set_active_slot raises error for invalid index"""
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        with pytest.raises(ValueError, match="Invalid slot_index"):
            await controller.set_active_slot(3)
    
    @pytest.mark.asyncio
    async def test_set_active_slot_raises_error_when_no_page_id(self, controller, mock_lcu):
        """Test that set_active_slot raises error when slot has no page ID"""
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        # Set pageId to None
        controller._slots[0].pageId = None
        
        with pytest.raises(ValueError, match="has no page ID"):
            await controller.set_active_slot(0)


class TestPageValidation:
    """Test page validation logic"""
    
    def test_validate_page_accepts_valid_page(self, controller):
        """Test that valid pages pass validation"""
        valid_page = RunePage(
            name="Valid Page",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        
        # Should not raise
        controller._validate_page(valid_page)
    
    def test_validate_page_rejects_empty_name(self, controller):
        """Test that empty name is rejected"""
        invalid_page = RunePage(
            name="",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        
        with pytest.raises(ValueError, match="Page name must be non-empty"):
            controller._validate_page(invalid_page)
    
    def test_validate_page_rejects_long_name(self, controller):
        """Test that names over 50 characters are rejected"""
        invalid_page = RunePage(
            name="A" * 51,
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        
        with pytest.raises(ValueError, match="under 50 characters"):
            controller._validate_page(invalid_page)
    
    def test_validate_page_rejects_invalid_primary_style(self, controller):
        """Test that invalid primary style ID is rejected"""
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=9999,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        
        with pytest.raises(ValueError, match="Invalid primary style ID"):
            controller._validate_page(invalid_page)
    
    def test_validate_page_rejects_invalid_sub_style(self, controller):
        """Test that invalid sub style ID is rejected"""
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=9999,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        
        with pytest.raises(ValueError, match="Invalid sub style ID"):
            controller._validate_page(invalid_page)
    
    def test_validate_page_rejects_same_styles(self, controller):
        """Test that same primary and sub style is rejected"""
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8000,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        
        with pytest.raises(ValueError, match="must be different"):
            controller._validate_page(invalid_page)
    
    def test_validate_page_rejects_wrong_perk_count(self, controller):
        """Test that wrong number of perks is rejected"""
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126],  # Only 5
            statShards=[5008, 5008, 5002]
        )
        
        with pytest.raises(ValueError, match="exactly 6 rune IDs"):
            controller._validate_page(invalid_page)
    
    def test_validate_page_rejects_wrong_stat_shard_count(self, controller):
        """Test that wrong number of stat shards is rejected"""
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008]  # Only 2
        )
        
        with pytest.raises(ValueError, match="exactly 3 stat shard IDs"):
            controller._validate_page(invalid_page)
    
    def test_validate_page_with_metadata_validates_primary_perks(self):
        """Test that validation checks primary perks belong to primary style when metadata available"""
        from lcu_backend.preset_provider import PresetProvider, RuneMetadata
        
        # Create mock preset provider with metadata
        mock_provider = MagicMock(spec=PresetProvider)
        
        # Mock metadata: perk 8005 belongs to style 8000, but 9999 belongs to style 8100
        mock_provider.get_rune_metadata.side_effect = lambda rune_id: {
            8005: RuneMetadata(id=8005, key="test", name="Test Rune", shortDesc="", icon="", styleId=8000, slot=0),
            9111: RuneMetadata(id=9111, key="test", name="Test Rune", shortDesc="", icon="", styleId=8000, slot=1),
            9104: RuneMetadata(id=9104, key="test", name="Test Rune", shortDesc="", icon="", styleId=8000, slot=2),
            9999: RuneMetadata(id=9999, key="wrong", name="Wrong Style", shortDesc="", icon="", styleId=8100, slot=3),
            8126: RuneMetadata(id=8126, key="test", name="Test Rune", shortDesc="", icon="", styleId=8100, slot=0),
            8106: RuneMetadata(id=8106, key="test", name="Test Rune", shortDesc="", icon="", styleId=8100, slot=1),
        }.get(rune_id)
        
        mock_lcu = MagicMock(spec=LCUConnection)
        controller = RunePageController(mock_lcu, preset_provider=mock_provider)
        
        # Page with wrong style perk in primary slot
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 9999, 8126, 8106],  # 9999 is wrong style
            statShards=[5008, 5008, 5002]
        )
        
        with pytest.raises(ValueError, match="belongs to style 8100.*but primary style is 8000"):
            controller._validate_page(invalid_page)
    
    def test_validate_page_with_metadata_validates_secondary_perks(self):
        """Test that validation checks secondary perks belong to sub style when metadata available"""
        from lcu_backend.preset_provider import PresetProvider, RuneMetadata
        
        # Create mock preset provider with metadata
        mock_provider = MagicMock(spec=PresetProvider)
        
        # Mock metadata: secondary perk 9999 belongs to wrong style
        mock_provider.get_rune_metadata.side_effect = lambda rune_id: {
            8005: RuneMetadata(id=8005, key="test", name="Test Rune", shortDesc="", icon="", styleId=8000, slot=0),
            9111: RuneMetadata(id=9111, key="test", name="Test Rune", shortDesc="", icon="", styleId=8000, slot=1),
            9104: RuneMetadata(id=9104, key="test", name="Test Rune", shortDesc="", icon="", styleId=8000, slot=2),
            8014: RuneMetadata(id=8014, key="test", name="Test Rune", shortDesc="", icon="", styleId=8000, slot=3),
            9999: RuneMetadata(id=9999, key="wrong", name="Wrong Style", shortDesc="", icon="", styleId=8000, slot=0),
            8106: RuneMetadata(id=8106, key="test", name="Test Rune", shortDesc="", icon="", styleId=8100, slot=1),
        }.get(rune_id)
        
        mock_lcu = MagicMock(spec=LCUConnection)
        controller = RunePageController(mock_lcu, preset_provider=mock_provider)
        
        # Page with wrong style perk in secondary slot
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 9999, 8106],  # 9999 is wrong style
            statShards=[5008, 5008, 5002]
        )
        
        with pytest.raises(ValueError, match="belongs to style 8000.*but sub style is 8100"):
            controller._validate_page(invalid_page)
    
    def test_validate_page_without_metadata_skips_style_validation(self, controller):
        """Test that validation skips style checks when no metadata provider"""
        # Controller without preset provider should skip style validation
        page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        
        # Should not raise even if we can't verify styles
        controller._validate_page(page)


class TestConvertToLCUFormat:
    """Test conversion to LCU format"""
    
    def test_convert_to_lcu_format_without_id(self, controller):
        """Test conversion without page ID (for POST)"""
        page = RunePage(
            name="Test Preset",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        
        result = controller._convert_to_lcu_format(page, "App Slot 1")
        
        assert result["name"] == "App Slot 1"
        assert result["primaryStyleId"] == 8000
        assert result["subStyleId"] == 8100
        assert result["selectedPerkIds"] == [8005, 9111, 9104, 8014, 8126, 8106]
        assert result["current"] is False
        assert result["isActive"] is False
        assert result["isDeletable"] is True
        assert result["isEditable"] is True
        assert result["isValid"] is True
        assert "id" not in result
    
    def test_convert_to_lcu_format_with_id(self, controller):
        """Test conversion with page ID (for PATCH)"""
        page = RunePage(
            name="Test Preset",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        
        result = controller._convert_to_lcu_format(page, "App Slot 2", page_id=42)
        
        assert result["name"] == "App Slot 2"
        assert result["id"] == 42
    
    def test_convert_to_lcu_format_validates_page(self, controller):
        """Test that conversion validates the page"""
        invalid_page = RunePage(
            name="",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        
        with pytest.raises(ValueError, match="Page name must be non-empty"):
            controller._convert_to_lcu_format(invalid_page, "App Slot 1")
    
    def test_convert_to_lcu_format_copies_perk_ids(self, controller):
        """Test that perk IDs are copied, not referenced"""
        page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        
        result = controller._convert_to_lcu_format(page, "App Slot 1")
        
        # Modify result
        result["selectedPerkIds"][0] = 9999
        
        # Original should be unchanged
        assert page.selectedPerkIds[0] == 8005



class TestRuneEditing:
    """Tests for rune editing in active slot (Task 4.3)"""
    
    @pytest.fixture
    def sample_preset(self):
        """Create a sample preset for testing"""
        return RunePage(
            name="Test Preset",
            primaryStyleId=8000,  # Precision
            subStyleId=8100,  # Domination
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
    
    @pytest.fixture
    def sample_rune_metadata(self):
        """Create sample rune metadata for testing"""
        from lcu_backend.preset_provider import RuneMetadata
        return RuneMetadata(
            id=8008,
            key="LethalTempo",
            name="Lethal Tempo",
            shortDesc="Gain attack speed",
            icon="perk-images/Styles/Precision/LethalTempo/LethalTempo.png",
            styleId=8000,  # Precision
            slot=0
        )
    
    @pytest.mark.asyncio
    async def test_get_active_slot_returns_active_slot(self, controller, mock_lcu, sample_preset):
        """Test that get_active_slot returns the active slot"""
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Get active slot
        active_slot = controller.get_active_slot()
        
        assert active_slot is not None
        assert active_slot.slotIndex == 0
        assert active_slot.isActive is True
    
    @pytest.mark.asyncio
    async def test_get_active_slot_returns_none_when_no_active(self, controller, mock_lcu):
        """Test that get_active_slot returns None when no slot is active"""
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        active_slot = controller.get_active_slot()
        assert active_slot is None
    
    @pytest.mark.asyncio
    async def test_update_rune_in_active_slot_updates_keystone(self, controller, mock_lcu, sample_preset, sample_rune_metadata):
        """Test updating keystone rune in active slot"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Update keystone
        await controller.update_rune_in_active_slot(8008, RuneSlotType.KEYSTONE, sample_rune_metadata)
        
        # Verify PATCH was called with updated rune
        assert mock_lcu.patch.call_count == 2  # Once for apply_preset, once for update
        last_call = mock_lcu.patch.call_args_list[-1]
        page_data = last_call[0][1]
        assert page_data["selectedPerkIds"][0] == 8008
        
        # Verify PUT was called to keep page active
        assert mock_lcu.put.call_count == 2
    
    @pytest.mark.asyncio
    async def test_update_rune_in_active_slot_updates_primary_slots(self, controller, mock_lcu, sample_preset, sample_rune_metadata):
        """Test updating primary rune slots"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Update primary1
        await controller.update_rune_in_active_slot(8008, RuneSlotType.PRIMARY1, sample_rune_metadata)
        last_call = mock_lcu.patch.call_args_list[-1]
        assert last_call[0][1]["selectedPerkIds"][1] == 8008
        
        # Update primary2
        await controller.update_rune_in_active_slot(8008, RuneSlotType.PRIMARY2, sample_rune_metadata)
        last_call = mock_lcu.patch.call_args_list[-1]
        assert last_call[0][1]["selectedPerkIds"][2] == 8008
        
        # Update primary3
        await controller.update_rune_in_active_slot(8008, RuneSlotType.PRIMARY3, sample_rune_metadata)
        last_call = mock_lcu.patch.call_args_list[-1]
        assert last_call[0][1]["selectedPerkIds"][3] == 8008
    
    @pytest.mark.asyncio
    async def test_update_rune_in_active_slot_updates_secondary_slots(self, controller, mock_lcu, sample_preset):
        """Test updating secondary rune slots"""
        from lcu_backend.rune_page_controller import RuneSlotType
        from lcu_backend.preset_provider import RuneMetadata
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Create metadata for Domination rune
        domination_rune = RuneMetadata(
            id=8120,
            key="GhostPoro",
            name="Ghost Poro",
            shortDesc="Gain vision",
            icon="perk-images/Styles/Domination/GhostPoro/GhostPoro.png",
            styleId=8100,  # Domination
            slot=2
        )
        
        # Update secondary1
        await controller.update_rune_in_active_slot(8120, RuneSlotType.SECONDARY1, domination_rune)
        last_call = mock_lcu.patch.call_args_list[-1]
        assert last_call[0][1]["selectedPerkIds"][4] == 8120
        
        # Update secondary2
        await controller.update_rune_in_active_slot(8120, RuneSlotType.SECONDARY2, domination_rune)
        last_call = mock_lcu.patch.call_args_list[-1]
        assert last_call[0][1]["selectedPerkIds"][5] == 8120
    
    @pytest.mark.asyncio
    async def test_update_rune_in_active_slot_updates_stat_shards(self, controller, mock_lcu, sample_preset):
        """Test updating stat shard slots"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Update stat shards (no metadata needed for stat shards)
        await controller.update_rune_in_active_slot(5005, RuneSlotType.STAT_SHARD1)
        last_call = mock_lcu.patch.call_args_list[-1]
        assert last_call[0][1]["statShards"][0] == 5005
        
        await controller.update_rune_in_active_slot(5007, RuneSlotType.STAT_SHARD2)
        last_call = mock_lcu.patch.call_args_list[-1]
        assert last_call[0][1]["statShards"][1] == 5007
        
        await controller.update_rune_in_active_slot(5001, RuneSlotType.STAT_SHARD3)
        last_call = mock_lcu.patch.call_args_list[-1]
        assert last_call[0][1]["statShards"][2] == 5001
    
    @pytest.mark.asyncio
    async def test_update_rune_validates_primary_style_compatibility(self, controller, mock_lcu, sample_preset):
        """Test that updating primary slot with wrong style is rejected"""
        from lcu_backend.rune_page_controller import RuneSlotType
        from lcu_backend.preset_provider import RuneMetadata
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Try to set Domination rune in Precision slot
        domination_rune = RuneMetadata(
            id=8128,
            key="DarkHarvest",
            name="Dark Harvest",
            shortDesc="Collect souls",
            icon="perk-images/Styles/Domination/DarkHarvest/DarkHarvest.png",
            styleId=8100,  # Domination
            slot=0
        )
        
        with pytest.raises(ValueError, match="incompatible with primary style"):
            await controller.update_rune_in_active_slot(8128, RuneSlotType.KEYSTONE, domination_rune)
    
    @pytest.mark.asyncio
    async def test_update_rune_validates_secondary_style_compatibility(self, controller, mock_lcu, sample_preset, sample_rune_metadata):
        """Test that updating secondary slot with wrong style is rejected"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Try to set Precision rune in Domination slot
        with pytest.raises(ValueError, match="incompatible with sub style"):
            await controller.update_rune_in_active_slot(8008, RuneSlotType.SECONDARY1, sample_rune_metadata)
    
    @pytest.mark.asyncio
    async def test_update_rune_without_metadata_skips_validation(self, controller, mock_lcu, sample_preset):
        """Test that updating without metadata skips validation"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Update without metadata (should not raise even if incompatible)
        await controller.update_rune_in_active_slot(9999, RuneSlotType.KEYSTONE)
        
        # Verify update was applied
        last_call = mock_lcu.patch.call_args_list[-1]
        assert last_call[0][1]["selectedPerkIds"][0] == 9999
    
    @pytest.mark.asyncio
    async def test_update_rune_raises_error_when_not_initialized(self, controller):
        """Test that update_rune_in_active_slot raises error when not initialized"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        with pytest.raises(RuntimeError, match="not initialized"):
            await controller.update_rune_in_active_slot(8008, RuneSlotType.KEYSTONE)
    
    @pytest.mark.asyncio
    async def test_update_rune_raises_error_when_no_active_slot(self, controller, mock_lcu):
        """Test that update_rune_in_active_slot raises error when no active slot"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        with pytest.raises(RuntimeError, match="No active slot found"):
            await controller.update_rune_in_active_slot(8008, RuneSlotType.KEYSTONE)
    
    @pytest.mark.asyncio
    async def test_update_rune_raises_error_for_invalid_rune_id(self, controller, mock_lcu, sample_preset):
        """Test that update_rune_in_active_slot raises error for invalid rune ID"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        with pytest.raises(ValueError, match="Invalid rune_id"):
            await controller.update_rune_in_active_slot(0, RuneSlotType.KEYSTONE)
        
        with pytest.raises(ValueError, match="Invalid rune_id"):
            await controller.update_rune_in_active_slot(-1, RuneSlotType.KEYSTONE)
    
    @pytest.mark.asyncio
    async def test_update_rune_raises_error_when_patch_fails(self, controller, mock_lcu, sample_preset):
        """Test that update_rune_in_active_slot raises error when PATCH fails"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Make PATCH fail
        mock_lcu.patch.return_value = None
        
        with pytest.raises(ConnectionError, match="Failed to update rune"):
            await controller.update_rune_in_active_slot(8008, RuneSlotType.KEYSTONE)
    
    @pytest.mark.asyncio
    async def test_update_rune_preserves_other_runes(self, controller, mock_lcu, sample_preset, sample_rune_metadata):
        """Test that updating one rune preserves all other runes"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Update keystone
        await controller.update_rune_in_active_slot(8008, RuneSlotType.KEYSTONE, sample_rune_metadata)
        
        # Verify other runes unchanged
        last_call = mock_lcu.patch.call_args_list[-1]
        page_data = last_call[0][1]
        assert page_data["selectedPerkIds"][0] == 8008  # Changed
        assert page_data["selectedPerkIds"][1] == 9111  # Unchanged
        assert page_data["selectedPerkIds"][2] == 9104  # Unchanged
        assert page_data["selectedPerkIds"][3] == 8014  # Unchanged
        assert page_data["selectedPerkIds"][4] == 8126  # Unchanged
        assert page_data["selectedPerkIds"][5] == 8106  # Unchanged
        assert page_data["statShards"] == [5008, 5008, 5002]  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_rune_keeps_page_active(self, controller, mock_lcu, sample_preset, sample_rune_metadata):
        """Test that updating rune keeps the page active"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Update rune
        await controller.update_rune_in_active_slot(8008, RuneSlotType.KEYSTONE, sample_rune_metadata)
        
        # Verify PUT was called to keep page active
        assert mock_lcu.put.call_count == 2  # Once for apply, once for update
        last_put_call = mock_lcu.put.call_args_list[-1]
        assert last_put_call[0][0] == "/lol-perks/v1/currentpage"
        assert last_put_call[0][1] == 1
    
    @pytest.mark.asyncio
    async def test_stat_shards_dont_require_style_validation(self, controller, mock_lcu, sample_preset):
        """Test that stat shards can be updated without style validation"""
        from lcu_backend.rune_page_controller import RuneSlotType
        from lcu_backend.preset_provider import RuneMetadata
        
        # Initialize and apply preset
        mock_lcu.get.return_value = [
            {"id": 1, "name": "App Slot 1", "current": False},
            {"id": 2, "name": "App Slot 2", "current": False},
            {"id": 3, "name": "App Slot 3", "current": False}
        ]
        await controller.initialize()
        
        mock_lcu.patch.return_value = {"id": 1}
        mock_lcu.put.return_value = None
        await controller.apply_preset_to_slot(sample_preset, 0)
        
        # Create metadata with any style (shouldn't matter for stat shards)
        stat_shard_metadata = RuneMetadata(
            id=5005,
            key="AttackSpeed",
            name="Attack Speed",
            shortDesc="+10% Attack Speed",
            icon="perk-images/StatMods/StatModsAttackSpeedIcon.png",
            styleId=9999,  # Invalid style, but shouldn't matter for stat shards
            slot=0
        )
        
        # Should not raise error even with invalid style
        await controller.update_rune_in_active_slot(5005, RuneSlotType.STAT_SHARD1, stat_shard_metadata)
        
        # Verify update was applied
        last_call = mock_lcu.patch.call_args_list[-1]
        assert last_call[0][1]["statShards"][0] == 5005


class TestRuneSlotTypeEnum:
    """Tests for RuneSlotType enum"""
    
    def test_rune_slot_type_values(self):
        """Test that RuneSlotType has all expected values"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        assert RuneSlotType.KEYSTONE.value == "keystone"
        assert RuneSlotType.PRIMARY1.value == "primary1"
        assert RuneSlotType.PRIMARY2.value == "primary2"
        assert RuneSlotType.PRIMARY3.value == "primary3"
        assert RuneSlotType.SECONDARY1.value == "secondary1"
        assert RuneSlotType.SECONDARY2.value == "secondary2"
        assert RuneSlotType.STAT_SHARD1.value == "statShard1"
        assert RuneSlotType.STAT_SHARD2.value == "statShard2"
        assert RuneSlotType.STAT_SHARD3.value == "statShard3"
    
    def test_rune_slot_type_is_string_enum(self):
        """Test that RuneSlotType is a string enum"""
        from lcu_backend.rune_page_controller import RuneSlotType
        
        assert isinstance(RuneSlotType.KEYSTONE, str)
        assert RuneSlotType.KEYSTONE == "keystone"
