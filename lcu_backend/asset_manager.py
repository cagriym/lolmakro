# Asset Manager component
# Handles Data Dragon asset fetching and local caching

import hashlib
import json
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error


class AssetManager:
    """Manages rune and spell icon assets with Data Dragon integration and local caching"""
    
    # Data Dragon CDN base URL
    DDRAGON_BASE_URL = "https://ddragon.leagueoflegends.com/cdn"
    
    # Default version (can be updated dynamically)
    DEFAULT_VERSION = "14.1.1"
    
    def __init__(self, cache_dir: Optional[Path] = None, version: Optional[str] = None):
        """
        Initialize asset manager
        
        Args:
            cache_dir: Directory for cached assets (defaults to ./asset_cache)
            version: League of Legends patch version (defaults to DEFAULT_VERSION)
        """
        self.cache_dir = cache_dir or Path("asset_cache")
        self.version = version or self.DEFAULT_VERSION
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different asset types
        (self.cache_dir / "runes").mkdir(exist_ok=True)
        (self.cache_dir / "spells").mkdir(exist_ok=True)
        (self.cache_dir / "champions").mkdir(exist_ok=True)
        
        # Track version info
        self._version_file = self.cache_dir / "version.json"
        self._load_version_info()
    
    def _load_version_info(self) -> None:
        """Load cached version information"""
        if self._version_file.exists():
            try:
                with open(self._version_file, "r") as f:
                    data = json.load(f)
                    cached_version = data.get("version")
                    
                    # If version changed, clear cache
                    if cached_version and cached_version != self.version:
                        self._clear_cache()
            except (json.JSONDecodeError, IOError):
                pass
        
        # Save current version
        self._save_version_info()
    
    def _save_version_info(self) -> None:
        """Save current version information"""
        try:
            with open(self._version_file, "w") as f:
                json.dump({"version": self.version}, f)
        except IOError:
            pass
    
    def _clear_cache(self) -> None:
        """Clear all cached assets"""
        for subdir in ["runes", "spells", "champions"]:
            cache_subdir = self.cache_dir / subdir
            if cache_subdir.exists():
                for file in cache_subdir.iterdir():
                    if file.is_file():
                        file.unlink()
    
    def _get_cache_path(self, asset_type: str, asset_key: str) -> Path:
        """
        Get cache file path for an asset
        
        Args:
            asset_type: Type of asset (runes, spells, champions)
            asset_key: Unique identifier for the asset
        
        Returns:
            Path to cached file
        """
        # Use hash of key to avoid filesystem issues with special characters
        key_hash = hashlib.md5(asset_key.encode()).hexdigest()
        extension = Path(asset_key).suffix or ".png"
        return self.cache_dir / asset_type / f"{key_hash}{extension}"
    
    def _download_asset(self, url: str, cache_path: Path) -> bool:
        """
        Download asset from URL and save to cache
        
        Args:
            url: URL to download from
            cache_path: Path to save downloaded file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = response.read()
                
                # Save to cache
                with open(cache_path, "wb") as f:
                    f.write(data)
                
                return True
        except Exception:
            # Catch all exceptions (network errors, IO errors, etc.)
            return False
    
    def get_rune_icon(self, icon_path: str) -> Optional[Path]:
        """
        Get rune icon, downloading from Data Dragon if not cached
        
        Args:
            icon_path: Icon path from rune metadata (e.g., "perk-images/Styles/Sorcery/SummonAery/SummonAery.png")
        
        Returns:
            Path to cached icon file, or None if download failed
        """
        cache_path = self._get_cache_path("runes", icon_path)
        
        # Return cached file if exists
        if cache_path.exists():
            return cache_path
        
        # Download from Data Dragon
        url = f"{self.DDRAGON_BASE_URL}/img/{icon_path}"
        
        if self._download_asset(url, cache_path):
            return cache_path
        
        return None
    
    def get_spell_icon(self, spell_name: str) -> Optional[Path]:
        """
        Get summoner spell icon, downloading from Data Dragon if not cached
        
        Args:
            spell_name: Spell name (e.g., "SummonerFlash")
        
        Returns:
            Path to cached icon file, or None if download failed
        """
        icon_path = f"{spell_name}.png"
        cache_path = self._get_cache_path("spells", icon_path)
        
        # Return cached file if exists
        if cache_path.exists():
            return cache_path
        
        # Download from Data Dragon
        url = f"{self.DDRAGON_BASE_URL}/{self.version}/img/spell/{icon_path}"
        
        if self._download_asset(url, cache_path):
            return cache_path
        
        return None
    
    def get_champion_icon(self, champion_name: str) -> Optional[Path]:
        """
        Get champion icon, downloading from Data Dragon if not cached
        
        Args:
            champion_name: Champion name (e.g., "Annie")
        
        Returns:
            Path to cached icon file, or None if download failed
        """
        icon_path = f"{champion_name}.png"
        cache_path = self._get_cache_path("champions", icon_path)
        
        # Return cached file if exists
        if cache_path.exists():
            return cache_path
        
        # Download from Data Dragon
        url = f"{self.DDRAGON_BASE_URL}/{self.version}/img/champion/{icon_path}"
        
        if self._download_asset(url, cache_path):
            return cache_path
        
        return None
    
    def preload_rune_icons(self, icon_paths: list[str]) -> dict[str, Optional[Path]]:
        """
        Preload multiple rune icons
        
        Args:
            icon_paths: List of icon paths to preload
        
        Returns:
            Dictionary mapping icon paths to cached file paths (or None if failed)
        """
        results = {}
        for icon_path in icon_paths:
            results[icon_path] = self.get_rune_icon(icon_path)
        return results
    
    def preload_spell_icons(self, spell_names: list[str]) -> dict[str, Optional[Path]]:
        """
        Preload multiple summoner spell icons
        
        Args:
            spell_names: List of spell names to preload
        
        Returns:
            Dictionary mapping spell names to cached file paths (or None if failed)
        """
        results = {}
        for spell_name in spell_names:
            results[spell_name] = self.get_spell_icon(spell_name)
        return results
    
    def get_cache_stats(self) -> dict[str, int]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with counts of cached assets by type
        """
        stats = {}
        for asset_type in ["runes", "spells", "champions"]:
            cache_subdir = self.cache_dir / asset_type
            if cache_subdir.exists():
                stats[asset_type] = len(list(cache_subdir.iterdir()))
            else:
                stats[asset_type] = 0
        return stats
    
    def set_version(self, version: str) -> None:
        """
        Update League of Legends patch version and clear cache if changed
        
        Args:
            version: New patch version (e.g., "14.1.1")
        """
        if version != self.version:
            self.version = version
            self._clear_cache()
            self._save_version_info()
