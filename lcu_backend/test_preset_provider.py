"""
Unit tests for PresetProvider component
Tests database loading, validation, and preset retrieval
"""

import json
import tempfile
from pathlib import Path

import pytest

from .preset_provider import (
    PresetDatabase,
    PresetProvider,
    RuneContext,
    RuneMetadata,
    RunePage,
    StyleMetadata,
)


class TestPresetDatabase:
    """Test PresetDatabase in-memory storage"""
    
    def test_generate_lookup_key(self):
        """Test lookup key generation"""
        key = PresetDatabase._generate_lookup_key(1, 420, "middle")
        assert key == "1_420_middle"
    
    def test_add_and_get_preset(self):
        """Test adding and retrieving presets"""
        db = PresetDatabase()
        
        page = RunePage(
            name="Test Page",
            primaryStyleId=8200,
            subStyleId=8100,
            selectedPerkIds=[8214, 8226, 8210, 8237, 8139, 8135],
            statShards=[5008, 5008, 5002],
        )
        
        db.add_preset(1, 420, "middle", page)
        
        context = RuneContext(championId=1, queueId=420, role="middle")
        presets = db.get_presets(context)
        
        assert len(presets) == 1
        assert presets[0].name == "Test Page"
    
    def test_get_presets_returns_max_three(self):
        """Test that get_presets returns at most 3 presets"""
        db = PresetDatabase()
        
        # Add 5 presets
        for i in range(5):
            page = RunePage(
                name=f"Page {i}",
                primaryStyleId=8200,
                subStyleId=8100,
                selectedPerkIds=[8214, 8226, 8210, 8237, 8139, 8135],
                statShards=[5008, 5008, 5002],
            )
            db.add_preset(1, 420, "middle", page)
        
        context = RuneContext(championId=1, queueId=420, role="middle")
        presets = db.get_presets(context)
        
        assert len(presets) == 3
    
    def test_get_presets_empty_when_not_found(self):
        """Test that get_presets returns empty list when no match"""
        db = PresetDatabase()
        
        context = RuneContext(championId=999, queueId=420, role="middle")
        presets = db.get_presets(context)
        
        assert len(presets) == 0
    
    def test_get_fallback_presets(self):
        """Test fallback preset retrieval"""
        db = PresetDatabase()
        
        page = RunePage(
            name="Fallback Page",
            primaryStyleId=8200,
            subStyleId=8100,
            selectedPerkIds=[8214, 8226, 8210, 8237, 8139, 8135],
            statShards=[5008, 5008, 5002],
        )
        
        db.add_preset(1, 420, "top", page)
        
        # Get fallback for different role
        fallback = db.get_fallback_presets(1)
        
        assert len(fallback) == 1
        assert fallback[0].name == "Fallback Page"
    
    def test_rune_metadata_storage(self):
        """Test rune metadata storage and retrieval"""
        db = PresetDatabase()
        
        metadata = RuneMetadata(
            id=8214,
            key="SummonAery",
            name="Summon Aery",
            shortDesc="Test description",
            icon="test.png",
            styleId=8200,
            slot=0,
        )
        
        db.add_rune_metadata(metadata)
        
        retrieved = db.get_rune_metadata(8214)
        assert retrieved is not None
        assert retrieved.name == "Summon Aery"
        assert retrieved.styleId == 8200
    
    def test_style_metadata_storage(self):
        """Test style metadata storage and retrieval"""
        db = PresetDatabase()
        
        metadata = StyleMetadata(
            id=8200,
            key="Sorcery",
            name="Sorcery",
            icon="sorcery.png",
            slots=[[8214, 8229], [8226, 8275]],
        )
        
        db.add_style_metadata(metadata)
        
        retrieved = db.get_style_metadata(8200)
        assert retrieved is not None
        assert retrieved.name == "Sorcery"
        assert len(retrieved.slots) == 2
    
    def test_version_info(self):
        """Test version information storage"""
        db = PresetDatabase()
        
        db.set_version_info("1.0.0", "2024-01-01")
        
        assert db.version == "1.0.0"
        assert db.last_updated == "2024-01-01"
    
    def test_counts(self):
        """Test database count properties"""
        db = PresetDatabase()
        
        page = RunePage(
            name="Test",
            primaryStyleId=8200,
            subStyleId=8100,
            selectedPerkIds=[8214, 8226, 8210, 8237, 8139, 8135],
            statShards=[5008, 5008, 5002],
        )
        db.add_preset(1, 420, "middle", page)
        
        rune_meta = RuneMetadata(
            id=8214, key="Test", name="Test", shortDesc="", icon="", styleId=8200, slot=0
        )
        db.add_rune_metadata(rune_meta)
        
        style_meta = StyleMetadata(
            id=8200, key="Test", name="Test", icon="", slots=[]
        )
        db.add_style_metadata(style_meta)
        
        assert db.preset_count == 1
        assert db.rune_metadata_count == 1
        assert db.style_metadata_count == 1
    
    def test_preset_with_recommended_spells(self):
        """Test adding and retrieving preset with recommended spells"""
        db = PresetDatabase()
        
        page = RunePage(
            name="Test with Spells",
            primaryStyleId=8200,
            subStyleId=8100,
            selectedPerkIds=[8214, 8226, 8210, 8237, 8139, 8135],
            statShards=[5008, 5008, 5002],
            recommendedSpells=[4, 14],  # Flash + Ignite
        )
        db.add_preset(1, 420, "middle", page)
        
        context = RuneContext(championId=1, queueId=420, role="middle")
        presets = db.get_presets(context)
        
        assert len(presets) == 1
        assert presets[0].recommendedSpells == [4, 14]
    
    def test_preset_without_recommended_spells(self):
        """Test preset without recommended spells (None)"""
        db = PresetDatabase()
        
        page = RunePage(
            name="Test without Spells",
            primaryStyleId=8200,
            subStyleId=8100,
            selectedPerkIds=[8214, 8226, 8210, 8237, 8139, 8135],
            statShards=[5008, 5008, 5002],
            recommendedSpells=None,
        )
        db.add_preset(1, 420, "middle", page)
        
        context = RuneContext(championId=1, queueId=420, role="middle")
        presets = db.get_presets(context)
        
        assert len(presets) == 1
        assert presets[0].recommendedSpells is None



class TestPresetProvider:
    """Test PresetProvider component"""
    
    def test_initialize_with_valid_data(self):
        """Test initialization with valid preset data"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [
                        {
                            "name": "Test Page",
                            "primaryStyleId": 8200,
                            "subStyleId": 8100,
                            "selectedPerkIds": [8214, 8226, 8210, 8237, 8139, 8135],
                            "statShards": [5008, 5008, 5002],
                        }
                    ],
                }
            ],
            "runeMetadata": [
                {
                    "id": 8214,
                    "key": "SummonAery",
                    "name": "Summon Aery",
                    "shortDesc": "Test",
                    "icon": "test.png",
                    "styleId": 8200,
                    "slot": 0,
                }
            ],
            "styleMetadata": [
                {
                    "id": 8200,
                    "key": "Sorcery",
                    "name": "Sorcery",
                    "icon": "sorcery.png",
                    "slots": [[8214]],
                }
            ],
        }
        
        provider.initialize(data)
        
        assert provider.is_initialized
        assert provider.database_info["version"] == "1.0.0"
    
    def test_initialize_missing_field(self):
        """Test initialization fails with missing required field"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            # Missing other required fields
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            provider.initialize(data)
    
    def test_validate_invalid_version(self):
        """Test validation fails with invalid version"""
        provider = PresetProvider()
        
        data = {
            "version": "",  # Empty version
            "lastUpdated": "2024-01-01",
            "presets": [],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        with pytest.raises(ValueError, match="Invalid version"):
            provider.initialize(data)
    
    def test_validate_preset_entry_missing_field(self):
        """Test validation fails when preset entry missing field"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    # Missing queueId, role, pages
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        with pytest.raises(ValueError, match="missing required field"):
            provider.initialize(data)
    
    def test_validate_invalid_champion_id(self):
        """Test validation fails with invalid championId"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 0,  # Invalid
                    "queueId": 420,
                    "role": "middle",
                    "pages": [],
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        with pytest.raises(ValueError, match="invalid championId"):
            provider.initialize(data)
    
    def test_validate_pages_count(self):
        """Test validation fails with invalid pages count"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [],  # Must have 1-3 pages
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        with pytest.raises(ValueError, match="must have 1-3 pages"):
            provider.initialize(data)
    
    def test_validate_rune_page_invalid_style(self):
        """Test validation fails with invalid style ID"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [
                        {
                            "name": "Test",
                            "primaryStyleId": 9999,  # Invalid
                            "subStyleId": 8100,
                            "selectedPerkIds": [1, 2, 3, 4, 5, 6],
                            "statShards": [1, 2, 3],
                        }
                    ],
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        with pytest.raises(ValueError, match="invalid primaryStyleId"):
            provider.initialize(data)
    
    def test_validate_same_primary_and_sub_style(self):
        """Test validation fails when primary and sub style are same"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [
                        {
                            "name": "Test",
                            "primaryStyleId": 8200,
                            "subStyleId": 8200,  # Same as primary
                            "selectedPerkIds": [1, 2, 3, 4, 5, 6],
                            "statShards": [1, 2, 3],
                        }
                    ],
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        with pytest.raises(ValueError, match="same primary and sub style"):
            provider.initialize(data)
    
    def test_validate_perk_count(self):
        """Test validation fails with wrong perk count"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [
                        {
                            "name": "Test",
                            "primaryStyleId": 8200,
                            "subStyleId": 8100,
                            "selectedPerkIds": [1, 2, 3],  # Must be 6
                            "statShards": [1, 2, 3],
                        }
                    ],
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        with pytest.raises(ValueError, match="exactly 6 selectedPerkIds"):
            provider.initialize(data)
    
    def test_validate_stat_shard_count(self):
        """Test validation fails with wrong stat shard count"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [
                        {
                            "name": "Test",
                            "primaryStyleId": 8200,
                            "subStyleId": 8100,
                            "selectedPerkIds": [1, 2, 3, 4, 5, 6],
                            "statShards": [1, 2],  # Must be 3
                        }
                    ],
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        with pytest.raises(ValueError, match="exactly 3 statShards"):
            provider.initialize(data)
    
    def test_validate_recommended_spells_valid(self):
        """Test validation accepts valid recommendedSpells"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [
                        {
                            "name": "Test",
                            "primaryStyleId": 8200,
                            "subStyleId": 8100,
                            "selectedPerkIds": [1, 2, 3, 4, 5, 6],
                            "statShards": [1, 2, 3],
                            "recommendedSpells": [4, 14],  # Flash + Ignite
                        }
                    ],
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        # Should not raise
        provider.initialize(data)
        assert provider.is_initialized
    
    def test_validate_recommended_spells_wrong_count(self):
        """Test validation fails with wrong recommendedSpells count"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [
                        {
                            "name": "Test",
                            "primaryStyleId": 8200,
                            "subStyleId": 8100,
                            "selectedPerkIds": [1, 2, 3, 4, 5, 6],
                            "statShards": [1, 2, 3],
                            "recommendedSpells": [4],  # Must be 2
                        }
                    ],
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        with pytest.raises(ValueError, match="exactly 2 spell IDs"):
            provider.initialize(data)
    
    def test_validate_recommended_spells_invalid_id(self):
        """Test validation fails with invalid spell ID"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [
                        {
                            "name": "Test",
                            "primaryStyleId": 8200,
                            "subStyleId": 8100,
                            "selectedPerkIds": [1, 2, 3, 4, 5, 6],
                            "statShards": [1, 2, 3],
                            "recommendedSpells": [4, -1],  # Invalid negative ID
                        }
                    ],
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        with pytest.raises(ValueError, match="invalid recommended spell ID"):
            provider.initialize(data)
    
    def test_validate_recommended_spells_none(self):
        """Test validation accepts None for recommendedSpells"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [
                        {
                            "name": "Test",
                            "primaryStyleId": 8200,
                            "subStyleId": 8100,
                            "selectedPerkIds": [1, 2, 3, 4, 5, 6],
                            "statShards": [1, 2, 3],
                            "recommendedSpells": None,
                        }
                    ],
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        # Should not raise
        provider.initialize(data)
        assert provider.is_initialized
    
    def test_validate_recommended_spells_omitted(self):
        """Test validation accepts omitted recommendedSpells field"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [
                        {
                            "name": "Test",
                            "primaryStyleId": 8200,
                            "subStyleId": 8100,
                            "selectedPerkIds": [1, 2, 3, 4, 5, 6],
                            "statShards": [1, 2, 3],
                            # recommendedSpells field omitted
                        }
                    ],
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        # Should not raise
        provider.initialize(data)
        assert provider.is_initialized

    
    def test_load_from_file(self):
        """Test loading preset database from JSON file"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        
        try:
            provider.load_from_file(temp_path)
            assert provider.is_initialized
        finally:
            Path(temp_path).unlink()
    
    def test_load_from_file_not_found(self):
        """Test loading from non-existent file raises error"""
        provider = PresetProvider()
        
        with pytest.raises(FileNotFoundError):
            provider.load_from_file("/nonexistent/file.json")
    
    def test_load_from_file_invalid_json(self):
        """Test loading invalid JSON raises error"""
        provider = PresetProvider()
        
        # Create temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                provider.load_from_file(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_get_presets_before_initialization(self):
        """Test get_presets raises error before initialization"""
        provider = PresetProvider()
        
        context = RuneContext(championId=1, queueId=420, role="middle")
        
        with pytest.raises(RuntimeError, match="not initialized"):
            provider.get_presets(context)
    
    def test_get_presets_with_fallback(self):
        """Test get_presets returns fallback when exact match not found"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "top",  # Different role
                    "pages": [
                        {
                            "name": "Fallback Page",
                            "primaryStyleId": 8200,
                            "subStyleId": 8100,
                            "selectedPerkIds": [8214, 8226, 8210, 8237, 8139, 8135],
                            "statShards": [5008, 5008, 5002],
                        }
                    ],
                }
            ],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        
        provider.initialize(data)
        
        # Request different role
        context = RuneContext(championId=1, queueId=420, role="middle")
        presets = provider.get_presets(context)
        
        assert len(presets) == 1
        assert presets[0].name == "Fallback Page"
    
    def test_get_rune_metadata(self):
        """Test get_rune_metadata retrieval"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [],
            "runeMetadata": [
                {
                    "id": 8214,
                    "key": "SummonAery",
                    "name": "Summon Aery",
                    "shortDesc": "Test",
                    "icon": "test.png",
                    "styleId": 8200,
                    "slot": 0,
                }
            ],
            "styleMetadata": [],
        }
        
        provider.initialize(data)
        
        metadata = provider.get_rune_metadata(8214)
        assert metadata is not None
        assert metadata.name == "Summon Aery"
    
    def test_get_style_metadata(self):
        """Test get_style_metadata retrieval"""
        provider = PresetProvider()
        
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [],
            "runeMetadata": [],
            "styleMetadata": [
                {
                    "id": 8200,
                    "key": "Sorcery",
                    "name": "Sorcery",
                    "icon": "sorcery.png",
                    "slots": [[8214]],
                }
            ],
        }
        
        provider.initialize(data)
        
        metadata = provider.get_style_metadata(8200)
        assert metadata is not None
        assert metadata.name == "Sorcery"
    
    def test_database_info(self):
        """Test database_info property"""
        provider = PresetProvider()
        
        # Before initialization
        info = provider.database_info
        assert info["initialized"] is False
        
        # After initialization
        data = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [],
            "runeMetadata": [],
            "styleMetadata": [],
        }
        provider.initialize(data)
        
        info = provider.database_info
        assert info["initialized"] is True
        assert info["version"] == "1.0.0"
        assert info["presetCount"] == 0

    def test_load_presets_with_recommended_spells_from_database(self):
        """Test loading presets with recommended spells from actual database file"""
        provider = PresetProvider()
        
        # Load from actual preset database file
        provider.load_from_file("lcu_backend/preset_database.json")
        
        # Query presets for Annie middle lane
        context = RuneContext(championId=1, queueId=420, role="middle")
        presets = provider.get_presets(context)
        
        # Should have presets with recommended spells
        assert len(presets) > 0
        
        # Check first preset has recommended spells
        burst_preset = next((p for p in presets if "Burst" in p.name), None)
        assert burst_preset is not None
        assert burst_preset.recommendedSpells is not None
        assert len(burst_preset.recommendedSpells) == 2
        assert burst_preset.recommendedSpells == [4, 14]  # Flash + Ignite
        
        # Check second preset has recommended spells
        sustain_preset = next((p for p in presets if "Sustain" in p.name), None)
        assert sustain_preset is not None
        assert sustain_preset.recommendedSpells is not None
        assert len(sustain_preset.recommendedSpells) == 2
        assert sustain_preset.recommendedSpells == [4, 12]  # Flash + Teleport
