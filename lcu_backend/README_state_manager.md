# State Manager Component

## Overview

The State Manager is the central coordination component that orchestrates interactions between the LCU Monitor, Preset Provider, and Rune Page Controller. It maintains the application state and provides a unified interface for managing rune pages during champion select.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      State Manager                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Application State                        │  │
│  │  - Gameflow Phase                                     │  │
│  │  - Champion Select Context                            │  │
│  │  - Available Presets                                  │  │
│  │  - Selected Preset Index                              │  │
│  │  - App Slots                                          │  │
│  │  - Active Slot Index                                  │  │
│  │  - Edit Mode                                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  LCU Monitor    │  │ Preset Provider │  │ Rune Page       │
│                 │  │                 │  │ Controller      │
│ - Gameflow      │  │ - Preset DB     │  │                 │
│ - Champ Select  │  │ - Rune Metadata │  │ - App Slots     │
│ - Events        │  │ - Lookups       │  │ - LCU Sync      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Key Features

1. **Component Coordination**: Initializes and coordinates all backend components
2. **State Management**: Maintains centralized application state
3. **Event Handling**: Processes gameflow and champion select events
4. **State Notifications**: Broadcasts state changes to registered callbacks
5. **Preset Selection**: Orchestrates preset application workflow
6. **Rune Editing**: Coordinates rune updates in active slots

## Data Models

### AppState

```python
@dataclass
class AppState:
    """Application state model"""
    gameflow_phase: Optional[GameflowPhase] = None
    champ_select_context: Optional[ChampSelectContext] = None
    available_presets: list[RunePage] = field(default_factory=list)
    selected_preset_index: Optional[int] = None
    app_slots: list[AppSlot] = field(default_factory=list)
    active_slot_index: Optional[int] = None
    is_edit_mode: bool = False
```

## API Reference

### Initialization

```python
state_manager = StateManager(
    lcu_monitor=lcu_monitor,
    preset_provider=preset_provider,
    rune_page_controller=rune_page_controller
)

await state_manager.initialize()
```

**Behavior**:
- Initializes Rune Page Controller (creates app slots)
- Registers event handlers for gameflow and champion select changes
- Starts LCU monitoring
- Notifies initial state to callbacks

### State Access

```python
# Get current state (returns a copy)
state = state_manager.get_current_state()

# Register callback for state changes
def on_state_change(state: AppState):
    print(f"Phase: {state.gameflow_phase}")
    print(f"Presets: {len(state.available_presets)}")

state_manager.on_state_change(on_state_change)
```

**Behavior**:
- `get_current_state()` returns a copy to prevent external modifications
- Callbacks can be sync or async functions
- Callbacks are called whenever state changes

### Preset Selection

```python
# Select and apply a preset
await state_manager.select_preset(preset_index=0)
```

**Behavior**:
- Validates preset index
- Applies preset to corresponding app slot (preset 0 → slot 0, etc.)
- Sets slot as active in LCU
- Updates state and notifies callbacks

**Raises**:
- `ValueError`: If preset_index is invalid
- `RuntimeError`: If not initialized
- `ConnectionError`: If LCU API call fails

### Rune Editing

```python
from lcu_backend.rune_page_controller import RuneSlotType

# Edit a rune in the active slot
await state_manager.edit_rune(
    rune_id=8128,  # Dark Harvest
    slot_type=RuneSlotType.KEYSTONE
)
```

**Behavior**:
- Validates rune compatibility with slot style
- Updates rune in active slot
- Syncs change to LCU
- Updates state and notifies callbacks

**Raises**:
- `ValueError`: If rune is incompatible with slot
- `RuntimeError`: If not initialized or no active slot
- `ConnectionError`: If LCU API call fails

### Edit Mode

```python
# Enable edit mode
await state_manager.set_edit_mode(True)

# Disable edit mode
await state_manager.set_edit_mode(False)
```

**Behavior**:
- Updates edit mode flag in state
- Notifies callbacks if state changed

### Shutdown

```python
# Shutdown state manager
await state_manager.shutdown()
```

**Behavior**:
- Stops LCU monitoring
- Cleans up resources
- Sets initialized flag to False

## Event Flow

### Champion Select Flow

```
1. LCU Monitor detects ChampSelect phase
   ↓
2. State Manager receives gameflow change event
   ↓
3. State Manager updates gameflow_phase in state
   ↓
4. LCU Monitor detects champion selection
   ↓
5. State Manager receives champion select session
   ↓
6. State Manager extracts context (champion, queue, role)
   ↓
7. State Manager queries Preset Provider for presets
   ↓
8. State Manager updates available_presets in state
   ↓
9. State Manager notifies callbacks with updated state
   ↓
10. UI displays preset options to user
```

### Preset Selection Flow

```
1. User selects preset (e.g., preset 0)
   ↓
2. State Manager calls select_preset(0)
   ↓
3. State Manager applies preset to slot 0 via Rune Page Controller
   ↓
4. Rune Page Controller updates LCU page
   ↓
5. Rune Page Controller sets page as active
   ↓
6. State Manager updates selected_preset_index and active_slot_index
   ↓
7. State Manager notifies callbacks with updated state
   ↓
8. UI updates to show selected preset
```

### Rune Editing Flow

```
1. User edits rune (e.g., changes keystone)
   ↓
2. State Manager calls edit_rune(rune_id, slot_type)
   ↓
3. State Manager gets rune metadata from Preset Provider
   ↓
4. State Manager validates rune compatibility
   ↓
5. State Manager updates rune via Rune Page Controller
   ↓
6. Rune Page Controller updates LCU page
   ↓
7. State Manager updates app_slots in state
   ↓
8. State Manager notifies callbacks with updated state
   ↓
9. UI updates to show new rune
```

## State Transitions

### Gameflow Phase Transitions

```
None → Lobby → ChampSelect → InProgress → EndOfGame → None
                    ↓
              [Context Extracted]
                    ↓
              [Presets Loaded]
```

**State Changes**:
- **Entering ChampSelect**: No immediate state change (waiting for champion selection)
- **Champion Selected**: Context extracted, presets loaded
- **Leaving ChampSelect**: Context and presets cleared

### Preset Selection States

```
No Presets → Presets Available → Preset Selected → Rune Edited
                                        ↓
                                  [Slot Active]
```

**State Changes**:
- **Presets Available**: `available_presets` populated, `selected_preset_index` is None
- **Preset Selected**: `selected_preset_index` set, `active_slot_index` set
- **Rune Edited**: `app_slots` updated with new rune data

## Error Handling

### Initialization Errors

```python
try:
    await state_manager.initialize()
except RuntimeError as e:
    # Component initialization failed
    print(f"Failed to initialize: {e}")
```

**Common Causes**:
- LCU not connected
- User has 25 rune pages (no space for app slots)
- Preset Provider not initialized

### Preset Selection Errors

```python
try:
    await state_manager.select_preset(0)
except ValueError as e:
    # Invalid preset index
    print(f"Invalid preset: {e}")
except ConnectionError as e:
    # LCU API call failed
    print(f"LCU error: {e}")
```

**Common Causes**:
- Invalid preset index
- LCU connection lost
- Page limit reached

### Rune Editing Errors

```python
try:
    await state_manager.edit_rune(8128, RuneSlotType.KEYSTONE)
except ValueError as e:
    # Rune incompatible with slot
    print(f"Invalid rune: {e}")
except RuntimeError as e:
    # No active slot
    print(f"No active slot: {e}")
```

**Common Causes**:
- Rune incompatible with slot style
- No active slot
- LCU connection lost

## Testing

### Unit Tests

Run unit tests:
```bash
python -m pytest lcu_backend/test_state_manager.py -v
```

**Test Coverage**:
- Initialization and shutdown
- Gameflow phase handling
- Champion select session handling
- Preset selection workflow
- Rune editing workflow
- Edit mode management
- State change callbacks
- Error handling

### Integration Testing

For integration testing with real LCU:
```bash
python lcu_backend/example_state_manager_usage.py
```

**Requirements**:
- League of Legends client running
- Preset database available
- User has < 25 rune pages

## Best Practices

### 1. Always Initialize Before Use

```python
# ✓ Good
await state_manager.initialize()
await state_manager.select_preset(0)

# ✗ Bad
await state_manager.select_preset(0)  # RuntimeError!
```

### 2. Handle State Change Callbacks Gracefully

```python
# ✓ Good - Handle errors in callback
def on_state_change(state: AppState):
    try:
        # Process state
        update_ui(state)
    except Exception as e:
        log_error(e)

# ✗ Bad - Let errors propagate
def on_state_change(state: AppState):
    update_ui(state)  # May break other callbacks!
```

### 3. Use State Copies

```python
# ✓ Good - Use returned copy
state = state_manager.get_current_state()
state.is_edit_mode = True  # Only affects local copy

# ✗ Bad - Don't try to modify internal state
state_manager._state.is_edit_mode = True  # Don't do this!
```

### 4. Validate Preset Index

```python
# ✓ Good - Validate before selecting
state = state_manager.get_current_state()
if 0 <= index < len(state.available_presets):
    await state_manager.select_preset(index)

# ✗ Bad - No validation
await state_manager.select_preset(index)  # May raise ValueError!
```

### 5. Shutdown Properly

```python
# ✓ Good - Always shutdown
try:
    await state_manager.initialize()
    # ... use state manager ...
finally:
    await state_manager.shutdown()

# ✗ Bad - No cleanup
await state_manager.initialize()
# ... use state manager ...
# (monitoring continues in background!)
```

## Requirements Mapping

This component satisfies the following requirements:

- **Requirement 2.1**: Polls gameflow phase endpoint via LCU Monitor
- **Requirement 2.2**: Notifies state changes when entering ChampSelect
- **Requirement 2.3**: Clears context when leaving ChampSelect
- **Requirement 3.1**: Fetches champion select session via LCU Monitor
- **Requirement 3.2**: Extracts context using Context Extractor

## Related Components

- **LCU Monitor**: Provides gameflow and champion select events
- **Context Extractor**: Extracts context from champion select sessions
- **Preset Provider**: Provides rune page presets and metadata
- **Rune Page Controller**: Manages app slots and LCU synchronization

## Example Usage

See `example_state_manager_usage.py` for complete working examples.

### Basic Usage

```python
import asyncio
from lcu_backend.lcu_connection import LCUConnection
from lcu_backend.lcu_monitor import LCUMonitor
from lcu_backend.preset_provider import PresetProvider
from lcu_backend.rune_page_controller import RunePageController
from lcu_backend.state_manager import StateManager

async def main():
    # Initialize components
    lcu_connection = LCUConnection()
    await lcu_connection.connect()
    
    lcu_monitor = LCUMonitor(lcu_connection)
    preset_provider = PresetProvider()
    preset_provider.load_from_file("preset_database.json")
    rune_page_controller = RunePageController(lcu_connection, preset_provider)
    
    # Create and initialize state manager
    state_manager = StateManager(lcu_monitor, preset_provider, rune_page_controller)
    await state_manager.initialize()
    
    # Register callback
    def on_state_change(state):
        print(f"State changed: {state.gameflow_phase}")
    
    state_manager.on_state_change(on_state_change)
    
    # Monitor for changes
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await state_manager.shutdown()
        await lcu_connection.disconnect()

asyncio.run(main())
```
