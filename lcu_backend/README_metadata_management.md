# Rune Metadata Management

This document describes the rune metadata management functionality implemented for task 3.3 of the LoL Rune Page Manager spec.

## Overview

The metadata management system provides:
- **Rune metadata loading** from embedded JSON database
- **Rune metadata lookup** by rune ID with O(1) performance
- **Style metadata** with slot configurations for rune trees
- **Asset caching** for rune and spell icons from Data Dragon CDN
- **Performance optimization** through preloading and local caching

## Components

### AssetManager

Handles Data Dragon integration and local asset caching.

**Key Features:**
- Downloads rune, spell, and champion icons from Data Dragon CDN
- Caches assets locally for fast subsequent access
- Automatically clears cache when League version changes
- Provides preloading for commonly used assets
- Graceful fallback when downloads fail

**Usage:**
```python
from asset_manager import AssetManager

# Initialize with cache directory and version
manager = AssetManager(cache_dir=Path("asset_cache"), version="14.1.1")

# Get rune icon (downloads if not cached)
icon_path = manager.get_rune_icon("perk-images/Styles/Sorcery/SummonAery/SummonAery.png")

# Get summoner spell icon
spell_icon = manager.get_spell_icon("SummonerFlash")

# Preload multiple icons
manager.preload_rune_icons([icon1, icon2, icon3])

# Check cache statistics
stats = manager.get_cache_stats()
print(f"Cached runes: {stats['runes']}")
```

### PresetProvider Integration

The PresetProvider now integrates with AssetManager for complete metadata management.

**New Methods:**
- `get_rune_icon_path(runeId)` - Get cached icon path for a rune
- `get_style_icon_path(styleId)` - Get cached icon path for a style
- `preload_common_assets()` - Preload frequently used assets

**Usage:**
```python
from asset_manager import AssetManager
from preset_provider import PresetProvider, RuneContext

# Create provider with asset manager
asset_manager = AssetManager()
provider = PresetProvider(asset_manager=asset_manager)

# Load database
provider.load_from_file("preset_database.json")

# Preload assets for better performance
provider.preload_common_assets()

# Get rune metadata
metadata = provider.get_rune_metadata(8214)
print(f"Rune: {metadata.name}")

# Get cached icon path
icon_path = provider.get_rune_icon_path(8214)
if icon_path:
    print(f"Icon cached at: {icon_path}")

# Get style metadata
style = provider.get_style_metadata(8200)
print(f"Style: {style.name}")
print(f"Slots: {style.slots}")
```

## Data Structures

### RuneMetadata
```python
@dataclass
class RuneMetadata:
    id: int              # Unique rune ID
    key: str             # Internal key name
    name: str            # Display name
    shortDesc: str       # Short description
    icon: str            # Icon path for Data Dragon
    styleId: int         # Parent style ID
    slot: int            # Slot position in tree
```

### StyleMetadata
```python
@dataclass
class StyleMetadata:
    id: int              # Unique style ID
    key: str             # Internal key name
    name: str            # Display name (e.g., "Sorcery")
    icon: str            # Icon path for Data Dragon
    slots: list[list[int]]  # Rune IDs organized by slot
```

## Asset Caching

### Cache Structure
```
asset_cache/
├── version.json          # Current version info
├── runes/               # Cached rune icons
│   ├── <hash1>.png
│   └── <hash2>.png
├── spells/              # Cached spell icons
│   ├── <hash3>.png
│   └── <hash4>.png
└── champions/           # Cached champion icons
    ├── <hash5>.png
    └── <hash6>.png
```

### Cache Behavior
- **First access**: Downloads from Data Dragon and caches locally
- **Subsequent access**: Returns cached file immediately
- **Version change**: Automatically clears cache and re-downloads
- **Download failure**: Returns None, allowing graceful fallback

## Data Dragon Integration

### Base URL
```
https://ddragon.leagueoflegends.com/cdn
```

### Asset URLs
- **Rune icons**: `{base}/img/{icon_path}`
- **Spell icons**: `{base}/{version}/img/spell/{spell_name}.png`
- **Champion icons**: `{base}/{version}/img/champion/{champion_name}.png`

### Version Management
The AssetManager tracks the League of Legends patch version and automatically clears the cache when the version changes, ensuring assets stay up-to-date.

## Performance Optimization

### Preloading Strategy
The `preload_common_assets()` method preloads:
1. All rune icons from the metadata database
2. Common summoner spells (Flash, Ignite, Teleport, etc.)

This ensures frequently used assets are cached before they're needed, reducing latency during champion select.

### Caching Benefits
- **O(1) metadata lookup** using in-memory dictionaries
- **Local file caching** eliminates repeated network requests
- **Lazy loading** for less common assets
- **Automatic cache invalidation** on version changes

## Requirements Satisfied

This implementation satisfies the following requirements from the spec:

- **11.1**: ✓ Fetch rune icons from Data Dragon CDN
- **11.2**: ✓ Fetch summoner spell icons from Data Dragon CDN
- **11.3**: ✓ Cache fetched images locally for performance optimization
- **11.5**: ✓ Preload commonly used assets during initialization

Additional features:
- **Metadata lookup**: Fast O(1) lookup by rune ID
- **Style metadata**: Complete style information with slot configurations
- **Version tracking**: Automatic cache refresh on version changes
- **Error handling**: Graceful fallback when downloads fail

## Testing

### Unit Tests
- `test_asset_manager.py` - Tests AssetManager functionality
- `test_preset_provider.py` - Tests PresetProvider (updated for asset manager)
- `test_metadata_integration.py` - Integration tests for complete workflow

### Running Tests
```bash
# Test asset manager
python -m pytest lcu_backend/test_asset_manager.py -v

# Test integration
python -m pytest lcu_backend/test_metadata_integration.py -v

# Test all
python -m pytest lcu_backend/ -v
```

## Example Usage

See `example_metadata_usage.py` for a complete demonstration of the metadata management functionality.

```bash
cd lcu_backend
python example_metadata_usage.py
```

## Future Enhancements

Potential improvements for future iterations:
- Parallel asset downloads for faster preloading
- Compression for cached assets to save disk space
- CDN fallback URLs if Data Dragon is unavailable
- Asset integrity verification (checksums)
- Background asset refresh without blocking
