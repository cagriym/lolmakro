# Preset Provider component
# Manages embedded rune page presets and provides lookups by context

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class RunePage:
    """Rune page configuration"""
    name: str
    primaryStyleId: int
    subStyleId: int
    selectedPerkIds: list[int]  # 6 perks: 4 primary + 2 secondary
    statShards: list[int]  # 3 stat shards
    recommendedSpells: list[int] | None = None  # Optional: [spell1_id, spell2_id]


@dataclass
class RuneContext:
    """Context for rune page lookup"""
    championId: int
    queueId: int
    role: str


@dataclass
class RuneMetadata:
    """Metadata for a single rune"""
    id: int
    key: str
    name: str
    shortDesc: str
    icon: str
    styleId: int
    slot: int


@dataclass
class StyleMetadata:
    """Metadata for a rune style (tree)"""
    id: int
    key: str
    name: str
    icon: str
    slots: list[list[int]]  # Rune IDs organized by slot


class PresetDatabase:
    """In-memory storage for preset rune pages with O(1) lookups"""
    
    def __init__(self) -> None:
        # Map: "championId_queueId_role" -> list of RunePage
        self._presets: dict[str, list[RunePage]] = {}
        
        # Map: runeId -> RuneMetadata
        self._rune_metadata: dict[int, RuneMetadata] = {}
        
        # Map: styleId -> StyleMetadata
        self._style_metadata: dict[int, StyleMetadata] = {}
        
        self._version: str = ""
        self._last_updated: str = ""
    
    @staticmethod
    def _generate_lookup_key(championId: int, queueId: int, role: str) -> str:
        """Generate lookup key from context parameters"""
        return f"{championId}_{queueId}_{role}"
    
    def add_preset(self, championId: int, queueId: int, role: str, page: RunePage) -> None:
        """Add a preset rune page to the database"""
        key = self._generate_lookup_key(championId, queueId, role)
        
        if key not in self._presets:
            self._presets[key] = []
        
        self._presets[key].append(page)
    
    def get_presets(self, context: RuneContext) -> list[RunePage]:
        """
        Get preset rune pages for the given context
        Returns up to 3 presets, or empty list if none found
        """
        key = self._generate_lookup_key(context.championId, context.queueId, context.role)
        presets = self._presets.get(key, [])
        
        # Return up to 3 presets
        return presets[:3]
    
    def get_fallback_presets(self, championId: int) -> list[RunePage]:
        """
        Get fallback presets for a champion (ignoring queue and role)
        Returns up to 3 presets from any queue/role combination
        """
        # Find any presets for this champion
        for key, presets in self._presets.items():
            if key.startswith(f"{championId}_"):
                return presets[:3]
        
        return []
    
    def add_rune_metadata(self, metadata: RuneMetadata) -> None:
        """Add rune metadata to the database"""
        self._rune_metadata[metadata.id] = metadata
    
    def get_rune_metadata(self, runeId: int) -> RuneMetadata | None:
        """Get rune metadata by ID"""
        return self._rune_metadata.get(runeId)
    
    def add_style_metadata(self, metadata: StyleMetadata) -> None:
        """Add style metadata to the database"""
        self._style_metadata[metadata.id] = metadata
    
    def get_style_metadata(self, styleId: int) -> StyleMetadata | None:
        """Get style metadata by ID"""
        return self._style_metadata.get(styleId)
    
    def set_version_info(self, version: str, last_updated: str) -> None:
        """Set version information for the database"""
        self._version = version
        self._last_updated = last_updated
    
    @property
    def version(self) -> str:
        """Get database version"""
        return self._version
    
    @property
    def last_updated(self) -> str:
        """Get last updated timestamp"""
        return self._last_updated
    
    @property
    def preset_count(self) -> int:
        """Get total number of preset entries"""
        return len(self._presets)
    
    @property
    def rune_metadata_count(self) -> int:
        """Get total number of rune metadata entries"""
        return len(self._rune_metadata)
    
    @property
    def style_metadata_count(self) -> int:
        """Get total number of style metadata entries"""
        return len(self._style_metadata)


class PresetProvider:
    """Manages embedded rune page presets and provides lookups"""
    
    def __init__(self, asset_manager=None) -> None:
        self._database = PresetDatabase()
        self._initialized = False
        self._asset_manager = asset_manager
    
    def initialize(self, preset_data: dict[str, Any]) -> None:
        """
        Initialize the preset provider with preset database data
        
        Args:
            preset_data: Dictionary containing preset database schema
        
        Raises:
            ValueError: If preset data is invalid
        """
        self._validate_preset_data(preset_data)
        self._load_preset_data(preset_data)
        self._initialized = True
    
    def load_from_file(self, file_path: str | Path) -> None:
        """
        Load preset database from JSON file
        
        Args:
            file_path: Path to JSON file containing preset database
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or data is malformed
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Preset database file not found: {file_path}")
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                preset_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in preset database: {e}") from e
        
        self.initialize(preset_data)
    
    def _validate_preset_data(self, data: dict[str, Any]) -> None:
        """Validate preset database structure"""
        # Check required top-level fields
        required_fields = ["version", "lastUpdated", "presets", "runeMetadata", "styleMetadata"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field in preset database: {field}")
        
        # Validate version format (basic check)
        if not isinstance(data["version"], str) or not data["version"]:
            raise ValueError("Invalid version format")
        
        # Validate presets is a list
        if not isinstance(data["presets"], list):
            raise ValueError("presets must be a list")
        
        # Validate runeMetadata is a list
        if not isinstance(data["runeMetadata"], list):
            raise ValueError("runeMetadata must be a list")
        
        # Validate styleMetadata is a list
        if not isinstance(data["styleMetadata"], list):
            raise ValueError("styleMetadata must be a list")
        
        # Validate each preset entry
        for i, preset_entry in enumerate(data["presets"]):
            self._validate_preset_entry(preset_entry, i)
        
        # Validate each rune metadata entry
        for i, rune_meta in enumerate(data["runeMetadata"]):
            self._validate_rune_metadata(rune_meta, i)
        
        # Validate each style metadata entry
        for i, style_meta in enumerate(data["styleMetadata"]):
            self._validate_style_metadata(style_meta, i)
    
    def _validate_preset_entry(self, entry: dict[str, Any], index: int) -> None:
        """Validate a single preset entry"""
        required_fields = ["championId", "queueId", "role", "pages"]
        for field in required_fields:
            if field not in entry:
                raise ValueError(f"Preset entry {index} missing required field: {field}")
        
        # Validate championId is positive integer
        if not isinstance(entry["championId"], int) or entry["championId"] <= 0:
            raise ValueError(f"Preset entry {index} has invalid championId")
        
        # Validate queueId is positive integer
        if not isinstance(entry["queueId"], int) or entry["queueId"] <= 0:
            raise ValueError(f"Preset entry {index} has invalid queueId")
        
        # Validate role is string
        if not isinstance(entry["role"], str):
            raise ValueError(f"Preset entry {index} has invalid role")
        
        # Validate pages is a list with 1-3 entries
        if not isinstance(entry["pages"], list) or not (1 <= len(entry["pages"]) <= 3):
            raise ValueError(f"Preset entry {index} must have 1-3 pages")
        
        # Validate each page
        for page_idx, page in enumerate(entry["pages"]):
            self._validate_rune_page(page, f"{index}.{page_idx}")
    
    def _validate_rune_page(self, page: dict[str, Any], identifier: str) -> None:
        """Validate a single rune page"""
        required_fields = ["name", "primaryStyleId", "subStyleId", "selectedPerkIds", "statShards"]
        for field in required_fields:
            if field not in page:
                raise ValueError(f"Rune page {identifier} missing required field: {field}")
        
        # Validate name
        if not isinstance(page["name"], str) or not page["name"]:
            raise ValueError(f"Rune page {identifier} has invalid name")
        
        # Validate style IDs
        valid_styles = (8000, 8100, 8200, 8300, 8400)
        if page["primaryStyleId"] not in valid_styles:
            raise ValueError(f"Rune page {identifier} has invalid primaryStyleId")
        
        if page["subStyleId"] not in valid_styles:
            raise ValueError(f"Rune page {identifier} has invalid subStyleId")
        
        if page["primaryStyleId"] == page["subStyleId"]:
            raise ValueError(f"Rune page {identifier} has same primary and sub style")
        
        # Validate selectedPerkIds
        if not isinstance(page["selectedPerkIds"], list) or len(page["selectedPerkIds"]) != 6:
            raise ValueError(f"Rune page {identifier} must have exactly 6 selectedPerkIds")
        
        for perk_id in page["selectedPerkIds"]:
            if not isinstance(perk_id, int) or perk_id <= 0:
                raise ValueError(f"Rune page {identifier} has invalid perk ID")
        
        # Validate statShards
        if not isinstance(page["statShards"], list) or len(page["statShards"]) != 3:
            raise ValueError(f"Rune page {identifier} must have exactly 3 statShards")
        
        for shard_id in page["statShards"]:
            if not isinstance(shard_id, int) or shard_id <= 0:
                raise ValueError(f"Rune page {identifier} has invalid stat shard ID")
        
        # Validate recommendedSpells (optional field)
        if "recommendedSpells" in page and page["recommendedSpells"] is not None:
            if not isinstance(page["recommendedSpells"], list) or len(page["recommendedSpells"]) != 2:
                raise ValueError(f"Rune page {identifier} recommendedSpells must be a list of exactly 2 spell IDs")
            
            for spell_id in page["recommendedSpells"]:
                if not isinstance(spell_id, int) or spell_id <= 0:
                    raise ValueError(f"Rune page {identifier} has invalid recommended spell ID")
    
    def _validate_rune_metadata(self, metadata: dict[str, Any], index: int) -> None:
        """Validate a single rune metadata entry"""
        required_fields = ["id", "key", "name", "shortDesc", "icon", "styleId", "slot"]
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Rune metadata {index} missing required field: {field}")
        
        if not isinstance(metadata["id"], int) or metadata["id"] <= 0:
            raise ValueError(f"Rune metadata {index} has invalid id")
        
        if not isinstance(metadata["styleId"], int):
            raise ValueError(f"Rune metadata {index} has invalid styleId")
        
        if not isinstance(metadata["slot"], int) or metadata["slot"] < 0:
            raise ValueError(f"Rune metadata {index} has invalid slot")
    
    def _validate_style_metadata(self, metadata: dict[str, Any], index: int) -> None:
        """Validate a single style metadata entry"""
        required_fields = ["id", "key", "name", "icon", "slots"]
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Style metadata {index} missing required field: {field}")
        
        if not isinstance(metadata["id"], int):
            raise ValueError(f"Style metadata {index} has invalid id")
        
        if not isinstance(metadata["slots"], list):
            raise ValueError(f"Style metadata {index} has invalid slots")
        
        for slot_idx, slot in enumerate(metadata["slots"]):
            if not isinstance(slot, list):
                raise ValueError(f"Style metadata {index} slot {slot_idx} must be a list")
    
    def _load_preset_data(self, data: dict[str, Any]) -> None:
        """Load validated preset data into the database"""
        # Set version info
        self._database.set_version_info(data["version"], data["lastUpdated"])
        
        # Load rune metadata
        for rune_meta in data["runeMetadata"]:
            metadata = RuneMetadata(
                id=rune_meta["id"],
                key=rune_meta["key"],
                name=rune_meta["name"],
                shortDesc=rune_meta["shortDesc"],
                icon=rune_meta["icon"],
                styleId=rune_meta["styleId"],
                slot=rune_meta["slot"],
            )
            self._database.add_rune_metadata(metadata)
        
        # Load style metadata
        for style_meta in data["styleMetadata"]:
            metadata = StyleMetadata(
                id=style_meta["id"],
                key=style_meta["key"],
                name=style_meta["name"],
                icon=style_meta["icon"],
                slots=style_meta["slots"],
            )
            self._database.add_style_metadata(metadata)
        
        # Load presets
        for preset_entry in data["presets"]:
            championId = preset_entry["championId"]
            queueId = preset_entry["queueId"]
            role = preset_entry["role"]
            
            for page_data in preset_entry["pages"]:
                page = RunePage(
                    name=page_data["name"],
                    primaryStyleId=page_data["primaryStyleId"],
                    subStyleId=page_data["subStyleId"],
                    selectedPerkIds=page_data["selectedPerkIds"],
                    statShards=page_data["statShards"],
                    recommendedSpells=page_data.get("recommendedSpells"),
                )
                self._database.add_preset(championId, queueId, role, page)
    
    def get_presets(self, context: RuneContext) -> list[RunePage]:
        """
        Get preset rune pages for the given context
        
        Args:
            context: RuneContext with championId, queueId, and role
        
        Returns:
            List of up to 3 RunePage objects, or empty list if none found
        
        Raises:
            RuntimeError: If provider not initialized
        """
        if not self._initialized:
            raise RuntimeError("PresetProvider not initialized")
        
        presets = self._database.get_presets(context)
        
        # If no exact match, try fallback (ignore role)
        if not presets:
            presets = self._database.get_fallback_presets(context.championId)
        
        return presets
    
    def get_rune_metadata(self, runeId: int) -> RuneMetadata | None:
        """
        Get rune metadata by ID
        
        Args:
            runeId: Rune ID to look up
        
        Returns:
            RuneMetadata if found, None otherwise
        
        Raises:
            RuntimeError: If provider not initialized
        """
        if not self._initialized:
            raise RuntimeError("PresetProvider not initialized")
        
        return self._database.get_rune_metadata(runeId)
    
    def get_style_metadata(self, styleId: int) -> StyleMetadata | None:
        """
        Get style metadata by ID
        
        Args:
            styleId: Style ID to look up
        
        Returns:
            StyleMetadata if found, None otherwise
        
        Raises:
            RuntimeError: If provider not initialized
        """
        if not self._initialized:
            raise RuntimeError("PresetProvider not initialized")
        
        return self._database.get_style_metadata(styleId)
    
    @property
    def is_initialized(self) -> bool:
        """Check if provider is initialized"""
        return self._initialized
    
    @property
    def database_info(self) -> dict[str, Any]:
        """Get database information for debugging"""
        if not self._initialized:
            return {"initialized": False}
        
        info = {
            "initialized": True,
            "version": self._database.version,
            "lastUpdated": self._database.last_updated,
            "presetCount": self._database.preset_count,
            "runeMetadataCount": self._database.rune_metadata_count,
            "styleMetadataCount": self._database.style_metadata_count,
        }
        
        # Add asset manager stats if available
        if self._asset_manager:
            info["assetCache"] = self._asset_manager.get_cache_stats()
        
        return info
    
    def preload_common_assets(self) -> None:
        """
        Preload commonly used rune and spell icons
        Should be called after initialization for better performance
        """
        if not self._initialized:
            raise RuntimeError("PresetProvider not initialized")
        
        if not self._asset_manager:
            return  # No asset manager configured
        
        # Collect all rune icon paths from metadata
        rune_icons = []
        for rune_id in range(8000, 9999):  # Reasonable range for rune IDs
            metadata = self._database.get_rune_metadata(rune_id)
            if metadata:
                rune_icons.append(metadata.icon)
        
        # Preload rune icons
        if rune_icons:
            self._asset_manager.preload_rune_icons(rune_icons)
        
        # Preload common summoner spells
        common_spells = [
            "SummonerFlash",
            "SummonerIgnite",
            "SummonerTeleport",
            "SummonerHeal",
            "SummonerBarrier",
            "SummonerExhaust",
            "SummonerSmite",
            "SummonerGhost",
            "SummonerCleanse",
        ]
        self._asset_manager.preload_spell_icons(common_spells)
    
    def get_rune_icon_path(self, runeId: int) -> Optional[Any]:
        """
        Get cached file path for a rune icon
        
        Args:
            runeId: Rune ID to get icon for
        
        Returns:
            Path to cached icon file, or None if not available
        """
        if not self._initialized:
            raise RuntimeError("PresetProvider not initialized")
        
        if not self._asset_manager:
            return None
        
        metadata = self._database.get_rune_metadata(runeId)
        if not metadata:
            return None
        
        return self._asset_manager.get_rune_icon(metadata.icon)
    
    def get_style_icon_path(self, styleId: int) -> Optional[Any]:
        """
        Get cached file path for a style icon
        
        Args:
            styleId: Style ID to get icon for
        
        Returns:
            Path to cached icon file, or None if not available
        """
        if not self._initialized:
            raise RuntimeError("PresetProvider not initialized")
        
        if not self._asset_manager:
            return None
        
        metadata = self._database.get_style_metadata(styleId)
        if not metadata:
            return None
        
        return self._asset_manager.get_rune_icon(metadata.icon)
