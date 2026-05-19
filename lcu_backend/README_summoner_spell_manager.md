# Summoner Spell Manager

## Overview

The Summoner Spell Manager component fetches, normalizes, and caches summoner spell data from the League of Legends Client (LCU) API. It provides a simple interface for accessing spell information and managing summoner spell selection during champion select.

## Features

- **Fetch spell catalog from LCU API**: Retrieves all available summoner spells
- **Data normalization**: Converts LCU API format to a consistent internal format
- **Alphabetical sorting**: Spells are sorted by name for easy browsing
- **Caching**: Spell data is cached in memory for performance
- **Quick lookups**: O(1) spell lookup by ID using internal map
- **Spell selection retrieval**: Fetch current summoner spell selection from champion select
- **Spell updates**: Update summoner spells during champion select with phase validation
- **Immediate synchronization**: Changes are synchronized to LCU immediately

## Usage

### Basic Usage

```python
from lcu_backend.lcu_connection import LCUConnection
from lcu_backend.summoner_spell_manager import SummonerSpellManager

# Initialize connection and manager
connection = LCUConnection()
spell_manager = SummonerSpellManager(connection)

# Load spell catalog from LCU API
spells = await spell_manager.load_spell_catalog()

# Access cached catalog
all_spells = spell_manager.get_spell_catalog()

# Get specific spell by ID
flash = spell_manager.get_spell_by_id(4)
if flash:
    print(f"Spell: {flash.name}")
    print(f"Description: {flash.description}")
    print(f"Icon: {flash.icon_path}")

# Check if catalog is loaded
if spell_manager.is_catalog_loaded():
    print("Spell catalog is ready")
```

### Summoner Spell Selection

```python
from lcu_backend.lcu_monitor import GameflowPhase

# Get current summoner spell selection
selection = await spell_manager.get_current_spell_selection()
if selection:
    print(f"Spell 1: {selection.spell1_id}")
    print(f"Spell 2: {selection.spell2_id}")

# Update summoner spells (only during ChampSelect phase)
await spell_manager.update_summoner_spells(
    spell1_id=4,   # Flash
    spell2_id=14,  # Ignite
    current_phase=GameflowPhase.CHAMP_SELECT
)

# Update only one spell
await spell_manager.update_summoner_spells(
    spell1_id=12,  # Teleport
    spell2_id=None,  # Keep current spell2
    current_phase=GameflowPhase.CHAMP_SELECT
)
```

### Integration with State Manager

```python
from lcu_backend.state_manager import StateManager

# State manager will initialize spell manager automatically
state_manager = StateManager()
await state_manager.initialize()

# Access spell manager through state manager
spell_manager = state_manager.spell_manager
spells = spell_manager.get_spell_catalog()
```

## Data Model

### SummonerSpell

```python
@dataclass
class SummonerSpell:
    id: int              # Spell ID (e.g., 4 for Flash)
    name: str            # Spell name (e.g., "Flash")
    description: str     # Spell description
    icon_path: str       # Path to spell icon in LCU assets
```

### SummonerSpellSelection

```python
@dataclass
class SummonerSpellSelection:
    spell1_id: int       # Spell ID for slot 1
    spell2_id: int       # Spell ID for slot 2
```

## API Reference

### SummonerSpellManager

#### `__init__(lcu_connection: LCUConnection)`

Initialize the summoner spell manager.

**Parameters:**
- `lcu_connection`: LCU connection instance for API calls

#### `async load_spell_catalog() -> list[SummonerSpell]`

Fetch summoner spell data from LCU API and cache it.

**Returns:**
- List of `SummonerSpell` objects sorted alphabetically by name

**Raises:**
- `RuntimeError`: If LCU API call fails

**Example:**
```python
spells = await spell_manager.load_spell_catalog()
print(f"Loaded {len(spells)} summoner spells")
```

#### `get_spell_catalog() -> list[SummonerSpell]`

Get cached summoner spell catalog.

**Returns:**
- List of `SummonerSpell` objects sorted alphabetically by name

**Note:** Returns a copy of the internal catalog to prevent external modifications.

#### `get_spell_by_id(spell_id: int) -> SummonerSpell | None`

Get summoner spell by ID from cached catalog.

**Parameters:**
- `spell_id`: Summoner spell ID

**Returns:**
- `SummonerSpell` object or `None` if not found

**Example:**
```python
flash = spell_manager.get_spell_by_id(4)
ignite = spell_manager.get_spell_by_id(14)
teleport = spell_manager.get_spell_by_id(12)
```

#### `is_catalog_loaded() -> bool`

Check if spell catalog has been loaded.

**Returns:**
- `True` if catalog is loaded, `False` otherwise

#### `async get_current_spell_selection() -> SummonerSpellSelection | None`

Fetch current summoner spell selection from champion select session.

**Returns:**
- `SummonerSpellSelection` with current spell IDs, or `None` if not in champion select

**Raises:**
- `RuntimeError`: If LCU API call fails

**Example:**
```python
selection = await spell_manager.get_current_spell_selection()
if selection:
    spell1 = spell_manager.get_spell_by_id(selection.spell1_id)
    spell2 = spell_manager.get_spell_by_id(selection.spell2_id)
    print(f"Current spells: {spell1.name}, {spell2.name}")
```

#### `async update_summoner_spells(spell1_id: int | None = None, spell2_id: int | None = None, current_phase: GameflowPhase | None = None) -> None`

Update summoner spell selection in champion select session.

**Parameters:**
- `spell1_id`: New spell ID for slot 1 (None to keep current)
- `spell2_id`: New spell ID for slot 2 (None to keep current)
- `current_phase`: Current gameflow phase for validation

**Raises:**
- `ValueError`: If not in ChampSelect phase
- `RuntimeError`: If LCU API call fails

**Example:**
```python
from lcu_backend.lcu_monitor import GameflowPhase

# Update both spells
await spell_manager.update_summoner_spells(
    spell1_id=4,
    spell2_id=14,
    current_phase=GameflowPhase.CHAMP_SELECT
)

# Update only spell1
await spell_manager.update_summoner_spells(
    spell1_id=12,
    current_phase=GameflowPhase.CHAMP_SELECT
)
```

## Common Summoner Spell IDs

| ID | Name | Description |
|----|------|-------------|
| 1 | Cleanse | Removes all disables and summoner spell debuffs |
| 3 | Exhaust | Exhausts target enemy champion |
| 4 | Flash | Teleports your champion a short distance |
| 6 | Ghost | Grants increased movement speed |
| 7 | Heal | Restores health to you and target ally |
| 11 | Smite | Deals damage to target monster or minion |
| 12 | Teleport | Teleports to target allied structure |
| 13 | Clarity | Restores mana (ARAM only) |
| 14 | Ignite | Ignites target enemy champion |
| 21 | Barrier | Shields your champion from damage |

## Error Handling

The spell manager handles various error scenarios:

1. **LCU API Failure**: Raises `RuntimeError` if spell data cannot be fetched
2. **Invalid Spell Entries**: Skips spells with missing required fields
3. **Empty Names**: Filters out spells with empty names
4. **Invalid IDs**: Skips entries with non-numeric IDs
5. **Phase Validation**: Raises `ValueError` if spell updates attempted outside ChampSelect phase
6. **Update Failures**: Raises `RuntimeError` if spell update API call fails

## Performance Considerations

- **Caching**: Spell data is cached after first load, avoiding repeated API calls
- **O(1) Lookups**: Spell lookup by ID uses a dictionary for constant-time access
- **Minimal Memory**: Only stores essential spell information
- **Sorted Output**: Spells are pre-sorted alphabetically for UI display
- **Immediate Sync**: Spell updates are synchronized to LCU immediately via PATCH request

## Requirements Satisfied

This component satisfies the following requirements from the specification:

- **Requirement 8.1**: Fetch summoner spell catalog from LCU API
- **Requirement 8.2**: Normalize and store summoner spell data (ID, name, description, icon path)
- **Requirement 8.3**: Fetch current summoner spell selection from champion select session
- **Requirement 8.4**: Display recommended summoner spells for presets
- **Requirement 8.5**: Update summoner spells via PATCH /lol-champ-select/v1/session
- **Requirement 8.6**: Validate spell changes only occur during ChampSelect phase
- **Requirement 8.7**: Synchronize spell changes immediately to LCU
- **Requirement 10.4**: Allow user to select different summoner spells
- **Requirement 10.5**: Update champion select session via LCU PATCH endpoint
- **Requirement 10.6**: Validate spell changes only occur during ChampSelect phase
- **Requirement 22.4**: Fetch summoner spell catalog from LCU game data assets
- **Requirement 22.5**: Normalize summoner spell data
- **Requirement 22.6**: Sort summoner spell list alphabetically by name

## Testing

The component includes comprehensive unit tests covering:

- Successful spell catalog loading
- Data normalization
- Caching behavior
- API failure handling
- Invalid entry filtering
- Alphabetical sorting
- Spell lookup by ID
- Missing optional fields
- Current spell selection retrieval
- Spell updates with phase validation
- Single and dual spell updates
- Phase validation errors
- API failure handling for updates
- Immediate synchronization

Run tests with:
```bash
pytest lcu_backend/test_summoner_spell_manager.py -v
```

## Future Enhancements

Potential improvements for future versions:

1. **Spell Filtering**: Filter spells by game mode (e.g., exclude Clarity from Summoner's Rift)
2. **Icon Caching**: Download and cache spell icons locally
3. **Spell Recommendations**: Suggest spell pairs based on champion/role
4. **Cooldown Information**: Include spell cooldown data
5. **Spell Availability**: Check which spells are available in current game mode
6. **Spell Swap Detection**: Detect when spells are swapped between slots
