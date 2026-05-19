"""
Integration tests for rune metadata management
Tests PresetProvider with AssetManager integration
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from .asset_manager import AssetManager
from .preset_provider import PresetProvider, RuneContext


class TestMetadataIntegration:
    """Test integrated metadata management functionality"""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def sample_preset_data(self):
        """Sample preset database with metadata"""
        return {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [
                {
                    "championId": 1,
                    "queueId": 420,
                    "role": "middle",
                    "pages": [
                        {
                            "name": "Annie - Burst",
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
                    "shortDesc": "Your attacks send Aery",
                    "icon": "perk-images/Styles/Sorcery/SummonAery/SummonAery.png",
                    "styleId": 8200,
                    "slot": 0,
                },
                {
                    "id": 8226,
                    "key": "ManaflowBand",
                    "name": "Manaflow Band",
                    "shortDesc": "Increases max mana",
                    "icon": "perk-images/Styles/Sorcery/ManaflowBand/ManaflowBand.png",
                    "styleId": 8200,
                    "slot": 1,
                },
            ],
            "styleMetadata": [
                {
                    "id": 8200,
                    "key": "Sorcery",
                    "name": "Sorcery",
                    "icon": "perk-images/Styles/7202_Sorcery.png",
                    "slots": [[8214, 8229], [8226, 8275]],
                },
                {
                    "id": 8100,
                    "key": "Domination",
                    "name": "Domination",
                    "icon": "perk-images/Styles/7200_Domination.png",
                    "slots": [[8112, 8124], [8139, 8143]],
                },
            ],
        }
    
    def test_preset_provider_with_asset_manager(self, temp_cache_dir, sample_preset_data):
        """Test PresetProvider initialized with AssetManager"""
        asset_manager = AssetManager(cache_dir=temp_cache_dir)
        provider = PresetProvider(asset_manager=asset_manager)
        
        provider.initialize(sample_preset_data)
        
        assert provider.is_initialized
        
        # Verify database info includes asset cache stats
        info = provider.database_info
        assert "assetCache" in info
        assert "runes" in info["assetCache"]
    
    def test_get_rune_metadata(self, temp_cache_dir, sample_preset_data):
        """Test retrieving rune metadata"""
        asset_manager = AssetManager(cache_dir=temp_cache_dir)
        provider = PresetProvider(asset_manager=asset_manager)
        provider.initialize(sample_preset_data)
        
        metadata = provider.get_rune_metadata(8214)
        
        assert metadata is not None
        assert metadata.name == "Summon Aery"
        assert metadata.styleId == 8200
        assert metadata.icon == "perk-images/Styles/Sorcery/SummonAery/SummonAery.png"
    
    def test_get_style_metadata(self, temp_cache_dir, sample_preset_data):
        """Test retrieving style metadata"""
        asset_manager = AssetManager(cache_dir=temp_cache_dir)
        provider = PresetProvider(asset_manager=asset_manager)
        provider.initialize(sample_preset_data)
        
        metadata = provider.get_style_metadata(8200)
        
        assert metadata is not None
        assert metadata.name == "Sorcery"
        assert metadata.key == "Sorcery"
        assert len(metadata.slots) == 2
    
    @patch("urllib.request.urlopen")
    def test_get_rune_icon_path(self, mock_urlopen, temp_cache_dir, sample_preset_data):
        """Test getting rune icon path with caching"""
        # Mock successful download
        mock_response = Mock()
        mock_response.read.return_value = b"rune icon data"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        asset_manager = AssetManager(cache_dir=temp_cache_dir)
        provider = PresetProvider(asset_manager=asset_manager)
        provider.initialize(sample_preset_data)
        
        icon_path = provider.get_rune_icon_path(8214)
        
        assert icon_path is not None
        assert icon_path.exists()
        assert icon_path.read_bytes() == b"rune icon data"
    
    @patch("urllib.request.urlopen")
    def test_get_style_icon_path(self, mock_urlopen, temp_cache_dir, sample_preset_data):
        """Test getting style icon path with caching"""
        # Mock successful download
        mock_response = Mock()
        mock_response.read.return_value = b"style icon data"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        asset_manager = AssetManager(cache_dir=temp_cache_dir)
        provider = PresetProvider(asset_manager=asset_manager)
        provider.initialize(sample_preset_data)
        
        icon_path = provider.get_style_icon_path(8200)
        
        assert icon_path is not None
        assert icon_path.exists()
        assert icon_path.read_bytes() == b"style icon data"
    
    def test_get_rune_icon_path_without_asset_manager(self, sample_preset_data):
        """Test get_rune_icon_path returns None without asset manager"""
        provider = PresetProvider()  # No asset manager
        provider.initialize(sample_preset_data)
        
        icon_path = provider.get_rune_icon_path(8214)
        
        assert icon_path is None
    
    @patch("urllib.request.urlopen")
    def test_preload_common_assets(self, mock_urlopen, temp_cache_dir, sample_preset_data):
        """Test preloading common assets"""
        # Mock successful downloads
        mock_response = Mock()
        mock_response.read.return_value = b"asset data"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        asset_manager = AssetManager(cache_dir=temp_cache_dir)
        provider = PresetProvider(asset_manager=asset_manager)
        provider.initialize(sample_preset_data)
        
        # Preload assets
        provider.preload_common_assets()
        
        # Verify assets were cached
        stats = asset_manager.get_cache_stats()
        assert stats["runes"] > 0  # Rune icons preloaded
        assert stats["spells"] > 0  # Common spells preloaded
    
    def test_preload_without_asset_manager(self, sample_preset_data):
        """Test preload_common_assets does nothing without asset manager"""
        provider = PresetProvider()  # No asset manager
        provider.initialize(sample_preset_data)
        
        # Should not raise error
        provider.preload_common_assets()
    
    def test_preload_before_initialization(self, temp_cache_dir):
        """Test preload_common_assets raises error before initialization"""
        asset_manager = AssetManager(cache_dir=temp_cache_dir)
        provider = PresetProvider(asset_manager=asset_manager)
        
        with pytest.raises(RuntimeError, match="not initialized"):
            provider.preload_common_assets()
    
    @patch("urllib.request.urlopen")
    def test_complete_workflow(self, mock_urlopen, temp_cache_dir, sample_preset_data):
        """Test complete metadata management workflow"""
        # Mock successful downloads
        mock_response = Mock()
        mock_response.read.return_value = b"asset data"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        # 1. Create asset manager and provider
        asset_manager = AssetManager(cache_dir=temp_cache_dir, version="14.1.1")
        provider = PresetProvider(asset_manager=asset_manager)
        
        # 2. Initialize with preset data
        provider.initialize(sample_preset_data)
        
        # 3. Preload common assets
        provider.preload_common_assets()
        
        # 4. Get presets for context
        context = RuneContext(championId=1, queueId=420, role="middle")
        presets = provider.get_presets(context)
        
        assert len(presets) == 1
        assert presets[0].name == "Annie - Burst"
        
        # 5. Get metadata for runes in preset
        for rune_id in presets[0].selectedPerkIds:
            metadata = provider.get_rune_metadata(rune_id)
            if metadata:  # Some IDs might not have metadata in sample data
                assert metadata.id == rune_id
                
                # Get icon path
                icon_path = provider.get_rune_icon_path(rune_id)
                # Icon path might be None if metadata not in sample data
        
        # 6. Get style metadata
        primary_style = provider.get_style_metadata(presets[0].primaryStyleId)
        assert primary_style is not None
        assert primary_style.id == 8200
        
        # 7. Verify cache stats
        info = provider.database_info
        assert info["initialized"]
        assert info["runeMetadataCount"] == 2
        assert info["styleMetadataCount"] == 2
        assert "assetCache" in info
