# Rune Page Controller component
# Manages application-owned rune page slots and synchronizes with LCU

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .lcu_connection import LCUConnection
from .preset_provider import RunePage, RuneMetadata


class RuneSlotType(str, Enum):
    """Enum for rune slot types"""
    KEYSTONE = "keystone"
    PRIMARY1 = "primary1"
    PRIMARY2 = "primary2"
    PRIMARY3 = "primary3"
    SECONDARY1 = "secondary1"
    SECONDARY2 = "secondary2"
    STAT_SHARD1 = "statShard1"
    STAT_SHARD2 = "statShard2"
    STAT_SHARD3 = "statShard3"


@dataclass
class AppSlot:
    """Represents one of three managed rune page slots"""
    slotIndex: int  # 0, 1, 2
    pageId: Optional[int]  # LCU page ID, None if not yet created
    name: str  # "App Slot 1", "App Slot 2", "App Slot 3"
    currentPage: Optional[RunePage]  # Current preset applied to this slot
    isActive: bool  # Whether this slot is the active page in LCU


class RunePageController:
    """Manages application-owned rune page slots and synchronizes with LCU"""
    
    # Valid style IDs for rune pages
    VALID_STYLE_IDS = {8000, 8100, 8200, 8300, 8400}
    
    # Maximum number of rune pages allowed by LCU
    MAX_PAGES = 25
    
    # App slot names
    SLOT_NAMES = ["App Slot 1", "App Slot 2", "App Slot 3"]
    
    def __init__(self, lcu_connection: LCUConnection, preset_provider=None) -> None:
        """
        Initialize Rune Page Controller
        
        Args:
            lcu_connection: LCU connection instance for API calls
            preset_provider: Optional PresetProvider for rune metadata validation
        """
        self._lcu = lcu_connection
        self._preset_provider = preset_provider
        self._slots: list[AppSlot] = []
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize three managed app slots
        
        Creates or identifies three dedicated app slots in the LCU client.
        Reuses existing slots if they already exist to prevent duplicates.
        
        Raises:
            ConnectionError: If LCU is not connected
            RuntimeError: If user has 25 pages and no app slots exist
        """
        if not await self._lcu.is_connected():
            raise ConnectionError("League Client not connected")
        
        # Get existing pages from LCU
        existing_pages = await self._lcu.get("/lol-perks/v1/pages")
        if existing_pages is None:
            raise RuntimeError("Failed to fetch rune pages from LCU")
        
        # Check page limit
        if len(existing_pages) >= self.MAX_PAGES:
            # Check if any app slots already exist
            app_slot_count = sum(
                1 for page in existing_pages 
                if page.get("name") in self.SLOT_NAMES
            )
            if app_slot_count == 0:
                raise RuntimeError(
                    f"Page limit reached ({self.MAX_PAGES} pages). "
                    "Please delete some rune pages in the League Client."
                )
        
        # Initialize each slot
        self._slots = []
        for i in range(3):
            slot = await self._initialize_slot(i, existing_pages)
            self._slots.append(slot)
        
        self._initialized = True
    
    async def _initialize_slot(
        self, 
        slot_index: int, 
        existing_pages: list[dict]
    ) -> AppSlot:
        """
        Initialize a single app slot
        
        Args:
            slot_index: Index of the slot (0, 1, 2)
            existing_pages: List of existing pages from LCU
        
        Returns:
            Initialized AppSlot object
        """
        slot_name = self.SLOT_NAMES[slot_index]
        
        # Check if slot already exists
        existing_page = None
        for page in existing_pages:
            if page.get("name") == slot_name:
                existing_page = page
                break
        
        if existing_page:
            # Reuse existing slot
            return AppSlot(
                slotIndex=slot_index,
                pageId=existing_page["id"],
                name=slot_name,
                currentPage=None,
                isActive=existing_page.get("current", False)
            )
        else:
            # Create new slot with default runes
            default_page = self._create_default_page_data(slot_name)
            response = await self._lcu.post("/lol-perks/v1/pages", default_page)
            
            if response is None or "id" not in response:
                raise RuntimeError(f"Failed to create app slot: {slot_name}")
            
            return AppSlot(
                slotIndex=slot_index,
                pageId=response["id"],
                name=slot_name,
                currentPage=None,
                isActive=False
            )
    
    def _create_default_page_data(self, name: str) -> dict:
        """
        Create default rune page data for a new slot
        
        Uses Precision primary with Domination secondary as default.
        
        Args:
            name: Name for the rune page
        
        Returns:
            Dictionary in LCU page format
        """
        return {
            "name": name,
            "primaryStyleId": 8000,  # Precision
            "subStyleId": 8100,  # Domination
            "selectedPerkIds": [
                8005,  # Press the Attack (Keystone)
                9111,  # Triumph
                9104,  # Legend: Alacrity
                8014,  # Coup de Grace
                8126,  # Cheap Shot
                8106   # Ultimate Hunter
            ],
            "current": False,
            "isActive": False,
            "isDeletable": True,
            "isEditable": True,
            "isValid": True,
            "order": 0
        }
    
    def get_app_slots(self) -> list[AppSlot]:
        """
        Get all app slots
        
        Returns:
            List of AppSlot objects
        
        Raises:
            RuntimeError: If controller not initialized
        """
        if not self._initialized:
            raise RuntimeError("RunePageController not initialized. Call initialize() first.")
        return self._slots.copy()
    
    def is_initialized(self) -> bool:
        """Check if controller is initialized"""
        return self._initialized
    
    def _validate_page(self, page: RunePage) -> None:
        """
        Validate RunePage structure before applying to LCU
        
        Args:
            page: RunePage to validate
        
        Raises:
            ValueError: If page structure is invalid
        """
        # Validate page name
        if not page.name or len(page.name) > 50:
            raise ValueError("Page name must be non-empty and under 50 characters")
        
        # Validate primary style ID
        if page.primaryStyleId not in self.VALID_STYLE_IDS:
            raise ValueError(f"Invalid primary style ID: {page.primaryStyleId}")
        
        # Validate sub style ID
        if page.subStyleId not in self.VALID_STYLE_IDS:
            raise ValueError(f"Invalid sub style ID: {page.subStyleId}")
        
        # Validate styles are different
        if page.primaryStyleId == page.subStyleId:
            raise ValueError("Primary and sub style IDs must be different")
        
        # Validate selectedPerkIds
        if len(page.selectedPerkIds) != 6:
            raise ValueError(f"selectedPerkIds must contain exactly 6 rune IDs, got {len(page.selectedPerkIds)}")
        
        # Validate statShards
        if len(page.statShards) != 3:
            raise ValueError(f"statShards must contain exactly 3 stat shard IDs, got {len(page.statShards)}")
        
        # Validate perk styles if metadata is available (Requirements 15.5, 15.6)
        if self._preset_provider is not None:
            # Validate first 4 perks belong to primary style
            for i in range(4):
                perk_id = page.selectedPerkIds[i]
                metadata = self._preset_provider.get_rune_metadata(perk_id)
                if metadata is not None and metadata.styleId != page.primaryStyleId:
                    raise ValueError(
                        f"Perk at position {i} (ID {perk_id}) belongs to style {metadata.styleId}, "
                        f"but primary style is {page.primaryStyleId}"
                    )
            
            # Validate last 2 perks belong to sub style
            for i in range(4, 6):
                perk_id = page.selectedPerkIds[i]
                metadata = self._preset_provider.get_rune_metadata(perk_id)
                if metadata is not None and metadata.styleId != page.subStyleId:
                    raise ValueError(
                        f"Perk at position {i} (ID {perk_id}) belongs to style {metadata.styleId}, "
                        f"but sub style is {page.subStyleId}"
                    )
    
    def _convert_to_lcu_format(self, page: RunePage, slot_name: str, page_id: Optional[int] = None) -> dict:
        """
        Convert RunePage to LCU page format
        
        Args:
            page: RunePage to convert
            slot_name: Name for the page
            page_id: Optional page ID for PATCH operations
        
        Returns:
            Dictionary in LCU page format
        
        Raises:
            ValueError: If page validation fails
        """
        # Validate page structure
        self._validate_page(page)
        
        # Build LCU format
        lcu_page = {
            "name": slot_name,
            "primaryStyleId": page.primaryStyleId,
            "subStyleId": page.subStyleId,
            "selectedPerkIds": page.selectedPerkIds.copy(),
            "current": False,
            "isActive": False,
            "isDeletable": True,
            "isEditable": True,
            "isValid": True,
            "order": 0
        }
        
        # Include statShards if present in the page
        # Note: The LCU API format for stat shards varies by version
        # Some versions include them in selectedPerkIds, others use a separate field
        # We include them as a separate field for compatibility
        if hasattr(page, 'statShards') and page.statShards:
            lcu_page["statShards"] = page.statShards.copy()
        
        # Add page ID if provided (for PATCH)
        if page_id is not None:
            lcu_page["id"] = page_id
        
        return lcu_page
    
    async def apply_preset_to_slot(self, preset: RunePage, slot_index: int) -> None:
        """
        Apply a preset to a specific app slot
        
        Updates the slot's rune page via LCU API and sets it as the active page.
        Ensures only one slot is marked active at a time.
        
        Args:
            preset: RunePage preset to apply
            slot_index: Index of the slot (0, 1, 2)
        
        Raises:
            RuntimeError: If controller not initialized
            ValueError: If slot_index is invalid or preset validation fails
            ConnectionError: If LCU API call fails
        """
        if not self._initialized:
            raise RuntimeError("RunePageController not initialized. Call initialize() first.")
        
        if slot_index not in {0, 1, 2}:
            raise ValueError(f"Invalid slot_index: {slot_index}. Must be 0, 1, or 2.")
        
        slot = self._slots[slot_index]
        
        # Convert preset to LCU format
        page_data = self._convert_to_lcu_format(preset, slot.name, slot.pageId)
        
        # Update or create page
        if slot.pageId is None:
            # Create new page
            response = await self._lcu.post("/lol-perks/v1/pages", page_data)
            if response is None or "id" not in response:
                raise ConnectionError(f"Failed to create page for slot {slot_index}")
            slot.pageId = response["id"]
        else:
            # Update existing page
            response = await self._lcu.patch(f"/lol-perks/v1/pages/{slot.pageId}", page_data)
            if response is None:
                raise ConnectionError(f"Failed to update page for slot {slot_index}")
        
        # Set as active page
        await self._lcu.put("/lol-perks/v1/currentpage", slot.pageId)
        
        # Update local state
        slot.currentPage = preset
        slot.isActive = True
        
        # Deactivate other slots
        for other_slot in self._slots:
            if other_slot.slotIndex != slot_index:
                other_slot.isActive = False
    
    async def set_active_slot(self, slot_index: int) -> None:
        """
        Set a specific slot as the active page
        
        Args:
            slot_index: Index of the slot (0, 1, 2)
        
        Raises:
            RuntimeError: If controller not initialized
            ValueError: If slot_index is invalid or slot has no page
            ConnectionError: If LCU API call fails
        """
        if not self._initialized:
            raise RuntimeError("RunePageController not initialized. Call initialize() first.")
        
        if slot_index not in {0, 1, 2}:
            raise ValueError(f"Invalid slot_index: {slot_index}. Must be 0, 1, or 2.")
        
        slot = self._slots[slot_index]
        
        if slot.pageId is None:
            raise ValueError(f"Slot {slot_index} has no page ID")
        
        # Set as active page in LCU
        await self._lcu.put("/lol-perks/v1/currentpage", slot.pageId)
        
        # Update local state
        slot.isActive = True
        
        # Deactivate other slots
        for other_slot in self._slots:
            if other_slot.slotIndex != slot_index:
                other_slot.isActive = False
    
    def get_active_slot(self) -> Optional[AppSlot]:
        """
        Get the currently active slot
        
        Returns:
            Active AppSlot if one exists, None otherwise
        
        Raises:
            RuntimeError: If controller not initialized
        """
        if not self._initialized:
            raise RuntimeError("RunePageController not initialized. Call initialize() first.")
        
        for slot in self._slots:
            if slot.isActive:
                return slot
        
        return None
    
    async def update_rune_in_active_slot(
        self, 
        rune_id: int, 
        slot_type: RuneSlotType,
        rune_metadata: Optional[RuneMetadata] = None
    ) -> None:
        """
        Update a specific rune in the active slot
        
        Validates rune compatibility with the slot's style before applying.
        Updates the LCU page and ensures it remains active.
        
        Args:
            rune_id: ID of the rune to set
            slot_type: Type of slot to update (keystone, primary1-3, secondary1-2, statShard1-3)
            rune_metadata: Optional RuneMetadata for validation. If None, validation is skipped.
        
        Raises:
            RuntimeError: If controller not initialized or no active slot
            ValueError: If rune is incompatible with slot style or rune_id is invalid
            ConnectionError: If LCU API call fails
        """
        if not self._initialized:
            raise RuntimeError("RunePageController not initialized. Call initialize() first.")
        
        if rune_id <= 0:
            raise ValueError(f"Invalid rune_id: {rune_id}. Must be positive integer.")
        
        # Get active slot
        active_slot = self.get_active_slot()
        if active_slot is None:
            raise RuntimeError("No active slot found. Apply a preset first.")
        
        if active_slot.currentPage is None:
            raise RuntimeError(f"Active slot {active_slot.slotIndex} has no current page.")
        
        current_page = active_slot.currentPage
        
        # Validate rune compatibility if metadata provided
        if rune_metadata is not None:
            self._validate_rune_compatibility(rune_metadata, slot_type, current_page)
        
        # Update rune in appropriate slot
        if slot_type == RuneSlotType.KEYSTONE:
            current_page.selectedPerkIds[0] = rune_id
        elif slot_type == RuneSlotType.PRIMARY1:
            current_page.selectedPerkIds[1] = rune_id
        elif slot_type == RuneSlotType.PRIMARY2:
            current_page.selectedPerkIds[2] = rune_id
        elif slot_type == RuneSlotType.PRIMARY3:
            current_page.selectedPerkIds[3] = rune_id
        elif slot_type == RuneSlotType.SECONDARY1:
            current_page.selectedPerkIds[4] = rune_id
        elif slot_type == RuneSlotType.SECONDARY2:
            current_page.selectedPerkIds[5] = rune_id
        elif slot_type == RuneSlotType.STAT_SHARD1:
            current_page.statShards[0] = rune_id
        elif slot_type == RuneSlotType.STAT_SHARD2:
            current_page.statShards[1] = rune_id
        elif slot_type == RuneSlotType.STAT_SHARD3:
            current_page.statShards[2] = rune_id
        else:
            raise ValueError(f"Invalid slot_type: {slot_type}")
        
        # Sync to LCU
        page_data = self._convert_to_lcu_format(current_page, active_slot.name, active_slot.pageId)
        response = await self._lcu.patch(f"/lol-perks/v1/pages/{active_slot.pageId}", page_data)
        
        if response is None:
            raise ConnectionError(f"Failed to update rune in active slot")
        
        # Ensure page remains active
        await self._lcu.put("/lol-perks/v1/currentpage", active_slot.pageId)
    
    def _validate_rune_compatibility(
        self, 
        rune_metadata: RuneMetadata, 
        slot_type: RuneSlotType, 
        current_page: RunePage
    ) -> None:
        """
        Validate that a rune is compatible with the slot's style
        
        Args:
            rune_metadata: Metadata for the rune being validated
            slot_type: Type of slot the rune will be placed in
            current_page: Current rune page configuration
        
        Raises:
            ValueError: If rune is incompatible with slot style
        """
        # Primary slots must match primary style
        if slot_type in {
            RuneSlotType.KEYSTONE, 
            RuneSlotType.PRIMARY1, 
            RuneSlotType.PRIMARY2, 
            RuneSlotType.PRIMARY3
        }:
            if rune_metadata.styleId != current_page.primaryStyleId:
                raise ValueError(
                    f"Rune {rune_metadata.name} (style {rune_metadata.styleId}) "
                    f"is incompatible with primary style {current_page.primaryStyleId}"
                )
        
        # Secondary slots must match sub style
        elif slot_type in {RuneSlotType.SECONDARY1, RuneSlotType.SECONDARY2}:
            if rune_metadata.styleId != current_page.subStyleId:
                raise ValueError(
                    f"Rune {rune_metadata.name} (style {rune_metadata.styleId}) "
                    f"is incompatible with sub style {current_page.subStyleId}"
                )
        
        # Stat shards don't have style restrictions (no validation needed)
