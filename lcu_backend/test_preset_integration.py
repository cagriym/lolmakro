"""
Integration test for task 3.2: Preset query and retrieval
Demonstrates the complete workflow of querying presets with metadata
"""

import pytest

from .preset_provider import PresetProvider, RuneContext


class TestPresetQueryAndRetrieval:
    """Integration tests for preset query and retrieval (Task 3.2)"""
    
    def test_complete_preset_query_workflow(self):
        """
        Test complete workflow:
        1. Load preset database
        2. Query presets with context
        3. Retrieve rune metadata
        4. Retrieve style metadata
        
        Validates Requirements 4.1, 4.2, 4.3, 4.4, 4.5
        """
        provider = PresetProvider()
        
        # Load from actual preset database file
        provider.load_from_file("lcu_backend/preset_database.json")
        
        assert provider.is_initialized
        
        # Requirement 4.1: Query presets with valid context
        context = RuneContext(championId=1, queueId=420, role="middle")
        
        # Requirement 4.2: Use championId, queueId, role as lookup keys
        presets = provider.get_presets(context)
        
        # Requirement 4.3: Return between 1 and 3 presets
        assert len(presets) >= 1
        assert len(presets) <= 3
        
        # Requirement 4.5: Include preset name, styles, runes, and stat shards
        for preset in presets:
            assert preset.name
            assert preset.primaryStyleId in [8000, 8100, 8200, 8300, 8400]
            assert preset.subStyleId in [8000, 8100, 8200, 8300, 8400]
            assert preset.primaryStyleId != preset.subStyleId
            assert len(preset.selectedPerkIds) == 6
            assert len(preset.statShards) == 3
        
        # Requirement 4.5: Include rune metadata in responses
        first_preset = presets[0]
        for rune_id in first_preset.selectedPerkIds:
            rune_metadata = provider.get_rune_metadata(rune_id)
            assert rune_metadata is not None
            assert rune_metadata.id == rune_id
            assert rune_metadata.name
            assert rune_metadata.icon
        
        # Requirement 4.5: Include style metadata in responses
        primary_style = provider.get_style_metadata(first_preset.primaryStyleId)
        assert primary_style is not None
        assert primary_style.id == first_preset.primaryStyleId
        assert primary_style.name
        assert primary_style.icon
        assert len(primary_style.slots) > 0
        
        sub_style = provider.get_style_metadata(first_preset.subStyleId)
        assert sub_style is not None
        assert sub_style.id == first_preset.subStyleId
    
    def test_context_based_lookup_key_generation(self):
        """
        Test context-based lookup key generation
        Validates that championId_queueId_role format is used
        
        Validates Requirement 4.2
        """
        provider = PresetProvider()
        provider.load_from_file("lcu_backend/preset_database.json")
        
        # Test exact match with context
        context = RuneContext(championId=1, queueId=420, role="middle")
        presets = provider.get_presets(context)
        
        assert len(presets) > 0
        # Verify we got Annie middle presets
        assert all("Annie" in p.name for p in presets)
    
    def test_fallback_logic_for_missing_presets(self):
        """
        Test fallback logic when exact context not found
        Should return generic champion presets ignoring role
        
        Validates Requirement 4.4
        """
        provider = PresetProvider()
        provider.load_from_file("lcu_backend/preset_database.json")
        
        # Request a role that doesn't exist for Annie
        context = RuneContext(championId=1, queueId=420, role="jungle")
        presets = provider.get_presets(context)
        
        # Should get fallback presets for Annie (ignoring role)
        assert len(presets) > 0
        assert all("Annie" in p.name for p in presets)
    
    def test_returns_up_to_three_presets(self):
        """
        Test that query returns at most 3 presets
        
        Validates Requirement 4.3
        """
        provider = PresetProvider()
        provider.load_from_file("lcu_backend/preset_database.json")
        
        context = RuneContext(championId=1, queueId=420, role="middle")
        presets = provider.get_presets(context)
        
        # Should return between 1 and 3 presets
        assert 1 <= len(presets) <= 3
    
    def test_metadata_availability_for_all_runes(self):
        """
        Test that metadata is available for all runes in presets
        
        Validates Requirement 4.5
        """
        provider = PresetProvider()
        provider.load_from_file("lcu_backend/preset_database.json")
        
        context = RuneContext(championId=1, queueId=420, role="middle")
        presets = provider.get_presets(context)
        
        # Check all runes have metadata
        for preset in presets:
            for rune_id in preset.selectedPerkIds:
                metadata = provider.get_rune_metadata(rune_id)
                assert metadata is not None, f"Missing metadata for rune {rune_id}"
                assert metadata.name
                assert metadata.shortDesc
                assert metadata.icon
                assert metadata.styleId >= 0
                assert metadata.slot >= 0
    
    def test_style_metadata_for_all_styles(self):
        """
        Test that style metadata is available for all styles in presets
        
        Validates Requirement 4.5
        """
        provider = PresetProvider()
        provider.load_from_file("lcu_backend/preset_database.json")
        
        context = RuneContext(championId=1, queueId=420, role="middle")
        presets = provider.get_presets(context)
        
        # Check all styles have metadata
        for preset in presets:
            primary_meta = provider.get_style_metadata(preset.primaryStyleId)
            assert primary_meta is not None
            assert primary_meta.name
            assert primary_meta.icon
            assert len(primary_meta.slots) > 0
            
            sub_meta = provider.get_style_metadata(preset.subStyleId)
            assert sub_meta is not None
            assert sub_meta.name
            assert sub_meta.icon
            assert len(sub_meta.slots) > 0
    
    def test_no_presets_for_unknown_champion(self):
        """
        Test behavior when no presets exist for a champion
        Should return empty list
        """
        provider = PresetProvider()
        provider.load_from_file("lcu_backend/preset_database.json")
        
        # Request presets for non-existent champion
        context = RuneContext(championId=99999, queueId=420, role="middle")
        presets = provider.get_presets(context)
        
        # Should return empty list
        assert len(presets) == 0
