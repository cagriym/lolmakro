"""
Unit tests for AssetManager component
Tests Data Dragon integration, caching, and asset preloading
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from .asset_manager import AssetManager


class TestAssetManager:
    """Test AssetManager functionality"""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_initialization_creates_directories(self, temp_cache_dir):
        """Test that initialization creates cache directories"""
        manager = AssetManager(cache_dir=temp_cache_dir)
        
        assert (temp_cache_dir / "runes").exists()
        assert (temp_cache_dir / "spells").exists()
        assert (temp_cache_dir / "champions").exists()
    
    def test_initialization_saves_version_info(self, temp_cache_dir):
        """Test that initialization saves version information"""
        manager = AssetManager(cache_dir=temp_cache_dir, version="14.1.1")
        
        version_file = temp_cache_dir / "version.json"
        assert version_file.exists()
        
        with open(version_file, "r") as f:
            data = json.load(f)
            assert data["version"] == "14.1.1"
    
    def test_version_change_clears_cache(self, temp_cache_dir):
        """Test that changing version clears the cache"""
        # Create manager with version 1
        manager1 = AssetManager(cache_dir=temp_cache_dir, version="14.1.1")
        
        # Create a dummy cached file
        dummy_file = temp_cache_dir / "runes" / "test.png"
        dummy_file.write_bytes(b"test data")
        
        assert dummy_file.exists()
        
        # Create new manager with different version
        manager2 = AssetManager(cache_dir=temp_cache_dir, version="14.2.1")
        
        # Cache should be cleared
        assert not dummy_file.exists()
    
    def test_get_cache_path(self, temp_cache_dir):
        """Test cache path generation"""
        manager = AssetManager(cache_dir=temp_cache_dir)
        
        path = manager._get_cache_path("runes", "test/icon.png")
        
        assert path.parent == temp_cache_dir / "runes"
        assert path.suffix == ".png"
    
    @patch("urllib.request.urlopen")
    def test_download_asset_success(self, mock_urlopen, temp_cache_dir):
        """Test successful asset download"""
        manager = AssetManager(cache_dir=temp_cache_dir)
        
        # Mock successful download
        mock_response = Mock()
        mock_response.read.return_value = b"fake image data"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        cache_path = temp_cache_dir / "test.png"
        result = manager._download_asset("http://test.com/icon.png", cache_path)
        
        assert result is True
        assert cache_path.exists()
        assert cache_path.read_bytes() == b"fake image data"
    
    @patch("urllib.request.urlopen")
    def test_download_asset_failure(self, mock_urlopen, temp_cache_dir):
        """Test failed asset download"""
        manager = AssetManager(cache_dir=temp_cache_dir)
        
        # Mock failed download
        mock_urlopen.side_effect = Exception("Network error")
        
        cache_path = temp_cache_dir / "test.png"
        result = manager._download_asset("http://test.com/icon.png", cache_path)
        
        assert result is False
        assert not cache_path.exists()
    
    @patch("urllib.request.urlopen")
    def test_get_rune_icon_downloads_if_not_cached(self, mock_urlopen, temp_cache_dir):
        """Test that get_rune_icon downloads if not in cache"""
        manager = AssetManager(cache_dir=temp_cache_dir, version="14.1.1")
        
        # Mock successful download
        mock_response = Mock()
        mock_response.read.return_value = b"rune icon data"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        icon_path = "perk-images/Styles/Sorcery/SummonAery/SummonAery.png"
        result = manager.get_rune_icon(icon_path)
        
        assert result is not None
        assert result.exists()
        assert result.read_bytes() == b"rune icon data"
        
        # Verify correct URL was called
        expected_url = f"{AssetManager.DDRAGON_BASE_URL}/img/{icon_path}"
        mock_urlopen.assert_called_once()
        assert mock_urlopen.call_args[0][0] == expected_url
    
    def test_get_rune_icon_returns_cached(self, temp_cache_dir):
        """Test that get_rune_icon returns cached file without downloading"""
        manager = AssetManager(cache_dir=temp_cache_dir)
        
        # Pre-populate cache
        icon_path = "perk-images/Styles/Sorcery/SummonAery/SummonAery.png"
        cache_path = manager._get_cache_path("runes", icon_path)
        cache_path.write_bytes(b"cached data")
        
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = manager.get_rune_icon(icon_path)
            
            # Should return cached file without downloading
            assert result == cache_path
            assert result.read_bytes() == b"cached data"
            mock_urlopen.assert_not_called()
    
    @patch("urllib.request.urlopen")
    def test_get_rune_icon_returns_none_on_failure(self, mock_urlopen, temp_cache_dir):
        """Test that get_rune_icon returns None if download fails"""
        manager = AssetManager(cache_dir=temp_cache_dir)
        
        # Mock failed download
        mock_urlopen.side_effect = Exception("Network error")
        
        result = manager.get_rune_icon("test/icon.png")
        
        assert result is None
    
    @patch("urllib.request.urlopen")
    def test_get_spell_icon(self, mock_urlopen, temp_cache_dir):
        """Test summoner spell icon fetching"""
        manager = AssetManager(cache_dir=temp_cache_dir, version="14.1.1")
        
        # Mock successful download
        mock_response = Mock()
        mock_response.read.return_value = b"spell icon data"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = manager.get_spell_icon("SummonerFlash")
        
        assert result is not None
        assert result.exists()
        
        # Verify correct URL
        expected_url = f"{AssetManager.DDRAGON_BASE_URL}/14.1.1/img/spell/SummonerFlash.png"
        mock_urlopen.assert_called_once()
        assert mock_urlopen.call_args[0][0] == expected_url
    
    @patch("urllib.request.urlopen")
    def test_get_champion_icon(self, mock_urlopen, temp_cache_dir):
        """Test champion icon fetching"""
        manager = AssetManager(cache_dir=temp_cache_dir, version="14.1.1")
        
        # Mock successful download
        mock_response = Mock()
        mock_response.read.return_value = b"champion icon data"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = manager.get_champion_icon("Annie")
        
        assert result is not None
        assert result.exists()
        
        # Verify correct URL
        expected_url = f"{AssetManager.DDRAGON_BASE_URL}/14.1.1/img/champion/Annie.png"
        mock_urlopen.assert_called_once()
        assert mock_urlopen.call_args[0][0] == expected_url
    
    @patch("urllib.request.urlopen")
    def test_preload_rune_icons(self, mock_urlopen, temp_cache_dir):
        """Test preloading multiple rune icons"""
        manager = AssetManager(cache_dir=temp_cache_dir)
        
        # Mock successful downloads
        mock_response = Mock()
        mock_response.read.return_value = b"icon data"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        icon_paths = [
            "perk-images/Styles/Sorcery/SummonAery/SummonAery.png",
            "perk-images/Styles/Domination/Electrocute/Electrocute.png",
        ]
        
        results = manager.preload_rune_icons(icon_paths)
        
        assert len(results) == 2
        assert all(path is not None for path in results.values())
        assert all(path.exists() for path in results.values())
    
    @patch("urllib.request.urlopen")
    def test_preload_spell_icons(self, mock_urlopen, temp_cache_dir):
        """Test preloading multiple summoner spell icons"""
        manager = AssetManager(cache_dir=temp_cache_dir)
        
        # Mock successful downloads
        mock_response = Mock()
        mock_response.read.return_value = b"spell data"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        spell_names = ["SummonerFlash", "SummonerIgnite", "SummonerTeleport"]
        
        results = manager.preload_spell_icons(spell_names)
        
        assert len(results) == 3
        assert all(path is not None for path in results.values())
        assert all(path.exists() for path in results.values())
    
    def test_get_cache_stats(self, temp_cache_dir):
        """Test cache statistics"""
        manager = AssetManager(cache_dir=temp_cache_dir)
        
        # Create some dummy cached files
        (temp_cache_dir / "runes" / "rune1.png").write_bytes(b"data")
        (temp_cache_dir / "runes" / "rune2.png").write_bytes(b"data")
        (temp_cache_dir / "spells" / "spell1.png").write_bytes(b"data")
        
        stats = manager.get_cache_stats()
        
        assert stats["runes"] == 2
        assert stats["spells"] == 1
        assert stats["champions"] == 0
    
    def test_set_version_clears_cache_if_changed(self, temp_cache_dir):
        """Test that set_version clears cache when version changes"""
        manager = AssetManager(cache_dir=temp_cache_dir, version="14.1.1")
        
        # Create dummy cached file
        dummy_file = temp_cache_dir / "runes" / "test.png"
        dummy_file.write_bytes(b"test data")
        
        assert dummy_file.exists()
        
        # Change version
        manager.set_version("14.2.1")
        
        # Cache should be cleared
        assert not dummy_file.exists()
        assert manager.version == "14.2.1"
    
    def test_set_version_does_not_clear_if_same(self, temp_cache_dir):
        """Test that set_version doesn't clear cache if version is same"""
        manager = AssetManager(cache_dir=temp_cache_dir, version="14.1.1")
        
        # Create dummy cached file
        dummy_file = temp_cache_dir / "runes" / "test.png"
        dummy_file.write_bytes(b"test data")
        
        assert dummy_file.exists()
        
        # Set same version
        manager.set_version("14.1.1")
        
        # Cache should not be cleared
        assert dummy_file.exists()
