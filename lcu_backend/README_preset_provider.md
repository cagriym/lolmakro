# Preset Provider Component

The Preset Provider component manages embedded rune page presets and provides fast lookups by champion, queue, and role context.

## Features

- **JSON-based preset database** with validation
- **O(1) lookup performance** using in-memory Map storage
- **Fallback preset support** when exact match not found
- **Rune and style metadata** management
- **Comprehensive validation** of preset data structure

## Architecture

### Components

1. **PresetDatabase**: In-memory storage with Map-based lookups
2. **PresetProvider**: High-level interface for loading and querying presets
3. **Data Models**: RunePage, RuneContext, RuneMetadata, StyleMetadata

### Database Schema

The preset database JSON file follows this structure:

```json
{
  "version": "1.0.0",
  "lastUpdated": "2024-01-01T00:00:00Z",
  "presets": [
    {
      "championId": 1,
      "queueId": 420,
      "role": "middle",
      "pages": [
        {
          "name": "Annie - Burst Mage",
          "primaryStyleId": 8200,
          "subStyleId": 8100,
          "selectedPerkIds": [8214, 8226, 8210, 8237, 8139, 8135],
          "statShards": [5008, 5008, 5002],
          "recommendedSpells": [4, 14]
        }
      ]
    }
  ],
  "runeMetadata": [
    {
      "id": 8214,
      "key": "SummonAery",
      "name": "Summon Aery",
      "shortDesc": "Your attacks and abilities send Aery to a target",
      "icon": "perk-images/Styles/Sorcery/SummonAery/SummonAery.png",
      "styleId": 8200,
      "slot": 0
    }
  ],
  "styleMetadata": [
    {
      "id": 8200,
      "key": "Sorcery",
      "name": "Sorcery",
      "icon": "perk-images/Styles/7202_Sorcery.png",
      "slots": [[8214, 8229, 8230], [8224, 8226, 8275]]
    }
  ]
}
```

## Usage

### Basic Usage

```python
from lcu_backend import PresetProvider, RuneContext

# Create provider
provider = PresetProvider()

# Load database from file
provider.load_from_file("preset_database.json")

# Query presets
context = RuneContext(championId=1, queueId=420, role="middle")
presets = provider.get_presets(context)

# Display presets
for preset in presets:
    print(f"{preset.name}: {preset.primaryStyleId}/{preset.subStyleId}")
```

### Loading from Dictionary

```python
preset_data = {
    "version": "1.0.0",
    "lastUpdated": "2024-01-01",
    "presets": [...],
    "runeMetadata": [...],
    "styleMetadata": [...]
}

provider.initialize(preset_data)
```

### Querying Metadata

```python
# Get rune metadata
rune_meta = provider.get_rune_metadata(8214)
print(f"{rune_meta.name}: {rune_meta.shortDesc}")

# Get style metadata
style_meta = provider.get_style_metadata(8200)
print(f"{style_meta.name} has {len(style_meta.slots)} slots")
```

### Database Information

```python
info = provider.database_info
print(f"Version: {info['version']}")
print(f"Presets: {info['presetCount']}")
print(f"Runes: {info['runeMetadataCount']}")
print(f"Styles: {info['styleMetadataCount']}")
```

### Using Recommended Summoner Spells

Presets can include recommended summoner spell IDs:

```python
from lcu_backend import PresetProvider, RuneContext, SummonerSpellManager

# Load presets
provider = PresetProvider()
provider.load_from_file("preset_database.json")

# Query presets
context = RuneContext(championId=1, queueId=420, role="middle")
presets = provider.get_presets(context)

# Check for recommended spells
for preset in presets:
    print(f"Preset: {preset.name}")
    
    if preset.recommendedSpells:
        spell1_id, spell2_id = preset.recommendedSpells
        print(f"  Recommended: Spell {spell1_id} + Spell {spell2_id}")
        
        # Optionally look up spell names using SummonerSpellManager
        spell1 = spell_manager.get_spell_by_id(spell1_id)
        spell2 = spell_manager.get_spell_by_id(spell2_id)
        print(f"  Names: {spell1.name} + {spell2.name}")
    else:
        print("  No recommended spells - user should select manually")
```

**Common Summoner Spell IDs:**
- 4: Flash
- 14: Ignite
- 12: Teleport
- 11: Smite
- 7: Heal
- 21: Barrier
- 3: Exhaust
- 1: Cleanse


## Data Models

### RunePage

Represents a complete rune page configuration:

```python
@dataclass
class RunePage:
    name: str                           # Page name
    primaryStyleId: int                 # Primary rune tree (8000-8400)
    subStyleId: int                     # Secondary rune tree (8000-8400)
    selectedPerkIds: list[int]          # 6 perks: 4 primary + 2 secondary
    statShards: list[int]               # 3 stat shards
    recommendedSpells: list[int] | None # Optional: [spell1_id, spell2_id]
```

**Recommended Spells**: Each preset can optionally include recommended summoner spell IDs. This allows the UI to display and auto-select appropriate spells for the preset. If `None`, the UI should let users select spells manually or use role-based defaults.

### RuneContext

Context for preset lookup:

```python
@dataclass
class RuneContext:
    championId: int    # Champion ID
    queueId: int       # Queue ID (420=Ranked Solo, 450=ARAM, etc.)
    role: str          # Role (top, jungle, middle, bottom, utility, none)
```

### RuneMetadata

Metadata for individual runes:

```python
@dataclass
class RuneMetadata:
    id: int           # Rune ID
    key: str          # Rune key (e.g., "SummonAery")
    name: str         # Display name
    shortDesc: str    # Short description
    icon: str         # Icon path
    styleId: int      # Parent style ID
    slot: int         # Slot index in style
```

### StyleMetadata

Metadata for rune styles (trees):

```python
@dataclass
class StyleMetadata:
    id: int                    # Style ID
    key: str                   # Style key (e.g., "Sorcery")
    name: str                  # Display name
    icon: str                  # Icon path
    slots: list[list[int]]     # Rune IDs organized by slot
```

## Validation

The PresetProvider validates all data on load:

### Preset Entry Validation
- ✓ championId must be positive integer
- ✓ queueId must be positive integer
- ✓ role must be string
- ✓ pages must contain 1-3 entries

### Rune Page Validation
- ✓ name must be non-empty string
- ✓ primaryStyleId must be valid (8000, 8100, 8200, 8300, 8400)
- ✓ subStyleId must be valid and different from primary
- ✓ selectedPerkIds must contain exactly 6 valid rune IDs
- ✓ statShards must contain exactly 3 valid stat shard IDs

### Metadata Validation
- ✓ All required fields present
- ✓ IDs are positive integers
- ✓ Slots are properly structured

## Lookup Algorithm

The preset lookup uses a two-tier approach:

1. **Exact Match**: Generate key `"{championId}_{queueId}_{role}"` and lookup in Map
2. **Fallback**: If no exact match, find any preset for the champion (ignoring queue/role)

This provides O(1) performance for exact matches and graceful degradation for missing data.

## Performance

- **Lookup Time**: O(1) for exact match, O(n) for fallback (n = number of preset entries)
- **Memory Usage**: ~2-5 MB for typical preset database
- **Initialization**: < 100ms for loading and validation

## Error Handling

The component raises clear exceptions for common errors:

```python
# File not found
FileNotFoundError: Preset database file not found: path/to/file.json

# Invalid JSON
ValueError: Invalid JSON in preset database: ...

# Missing required field
ValueError: Missing required field in preset database: version

# Invalid data
ValueError: Preset entry 0 has invalid championId

# Not initialized
RuntimeError: PresetProvider not initialized
```

## Testing

Run the test suite:

```bash
pytest lcu_backend/test_preset_provider.py -v
```

Run the example:

```bash
python -m lcu_backend.example_preset_usage
```

## Integration

The PresetProvider integrates with other components:

- **State Manager**: Queries presets when champion select context changes
- **Rune Page Controller**: Uses RunePage objects to apply presets to LCU
- **UI Layer**: Displays preset metadata (names, icons, descriptions)

## Future Enhancements

Potential improvements for future versions:

- [ ] External preset provider integration (fetch from web API)
- [ ] Preset caching and update mechanism
- [ ] Preset popularity/win rate metadata
- [ ] User-defined custom presets
- [ ] Preset import/export functionality
