# Rune Page Controller

The Rune Page Controller manages three dedicated application-owned rune page slots in the League of Legends client. It provides slot initialization, detection, and management functionality while ensuring user-created rune pages are never modified.

## Features

- **Slot Initialization**: Creates or identifies three dedicated app slots ("App Slot 1", "App Slot 2", "App Slot 3")
- **Duplicate Prevention**: Reuses existing app slots instead of creating duplicates
- **Page Limit Validation**: Validates that the user has space for new pages (max 25 pages)
- **User Page Isolation**: Never modifies or deletes user-created rune pages
- **Active Slot Tracking**: Tracks which slot is currently active in the LCU client

## Architecture

The Rune Page Controller is part of the LoL Rune Page Manager system and integrates with:

- **LCU Connection**: Uses LCU API to create, read, and manage rune pages
- **Preset Provider**: Will apply presets to slots (future functionality)
- **State Manager**: Coordinates with other components (future functionality)

## Usage

### Basic Initialization

```python
from lcu_backend.lcu_connection import LCUConnection
from lcu_backend.rune_page_controller import RunePageController

# Create LCU connection
lcu = LCUConnection()
await lcu.retry_until_connected()

# Create and initialize controller
controller = RunePageController(lcu)
await controller.initialize()

# Get app slots
slots = controller.get_app_slots()
for slot in slots:
    print(f"{slot.name}: Page ID {slot.pageId}")
```

### Error Handling

```python
try:
    await controller.initialize()
except ConnectionError:
    print("League Client not connected")
except RuntimeError as e:
    if "Page limit reached" in str(e):
        print("User has 25 pages. Please delete some pages.")
    else:
        print(f"Initialization failed: {e}")
```

### Checking Initialization State

```python
if controller.is_initialized():
    slots = controller.get_app_slots()
else:
    await controller.initialize()
```

## API Reference

### RunePageController

#### `__init__(lcu_connection: LCUConnection)`

Creates a new Rune Page Controller instance.

**Parameters:**
- `lcu_connection`: LCU connection instance for API calls

#### `async initialize() -> None`

Initializes three managed app slots. Creates new slots if they don't exist, or reuses existing slots.

**Raises:**
- `ConnectionError`: If LCU is not connected
- `RuntimeError`: If user has 25 pages and no app slots exist, or if API calls fail

**Behavior:**
1. Fetches existing rune pages from LCU
2. Checks for page limit (25 pages max)
3. For each slot (0, 1, 2):
   - Searches for existing slot by name
   - Reuses existing slot if found
   - Creates new slot with default runes if not found
4. Marks controller as initialized

#### `get_app_slots() -> list[AppSlot]`

Returns a copy of all app slots.

**Returns:**
- List of `AppSlot` objects

**Raises:**
- `RuntimeError`: If controller not initialized

#### `is_initialized() -> bool`

Checks if the controller has been initialized.

**Returns:**
- `True` if initialized, `False` otherwise

### AppSlot

Data class representing a managed rune page slot.

**Attributes:**
- `slotIndex: int` - Index of the slot (0, 1, 2)
- `pageId: Optional[int]` - LCU page ID, None if not yet created
- `name: str` - Slot name ("App Slot 1", "App Slot 2", "App Slot 3")
- `currentPage: Optional[RunePage]` - Current preset applied to this slot
- `isActive: bool` - Whether this slot is the active page in LCU

## Implementation Details

### Slot Detection Algorithm

The initialization algorithm follows these steps:

1. **Fetch Existing Pages**: GET `/lol-perks/v1/pages`
2. **Validate Page Limit**: Check if user has < 25 pages or app slots already exist
3. **For Each Slot (0-2)**:
   - Search for page with matching name in existing pages
   - If found: Reuse the page ID and active status
   - If not found: Create new page with default runes via POST
4. **Mark Initialized**: Set internal flag to prevent re-initialization

### Default Rune Page

When creating a new slot, the controller uses this default configuration:

- **Primary Style**: Precision (8000)
- **Sub Style**: Domination (8100)
- **Selected Perks**:
  - Keystone: Press the Attack (8005)
  - Primary: Triumph (9111), Legend: Alacrity (9104), Coup de Grace (8014)
  - Secondary: Cheap Shot (8126), Ultimate Hunter (8106)
- **Properties**: Deletable, Editable, Valid

### Page Limit Handling

The LCU enforces a maximum of 25 rune pages per account. The controller handles this by:

1. Counting existing pages
2. If at limit (25 pages):
   - Check if any app slots already exist
   - If yes: Reuse them (no new pages needed)
   - If no: Raise error asking user to delete pages
3. If below limit: Create missing slots

### User Page Isolation

The controller ensures user pages are never modified by:

- Only tracking pages with names "App Slot 1", "App Slot 2", "App Slot 3"
- Never calling PATCH/DELETE on pages not in the app slots list
- Creating new pages only when necessary
- Reusing existing app slots to prevent duplicates

## Requirements Satisfied

This implementation satisfies the following requirements from the spec:

- **5.1**: Creates or identifies three dedicated app slots
- **5.2**: Names slots "App Slot 1", "App Slot 2", "App Slot 3"
- **5.3**: Searches for pages with matching names
- **5.4**: Reuses existing page ID if slot already exists
- **5.5**: Creates new page with default runes if slot doesn't exist
- **5.6**: Marks all app slot pages as deletable and editable
- **5.7**: Ensures user has fewer than 25 total rune pages

## Testing

The controller includes comprehensive unit tests covering:

- Creating three new slots when none exist
- Reusing existing slots to prevent duplicates
- Creating only missing slots (partial reuse)
- Handling slots in any order
- Page limit validation (25 pages max)
- Error handling (connection failures, API errors)
- Default page structure validation
- User page isolation

Run tests with:

```bash
pytest lcu_backend/test_rune_page_controller.py -v
```

## Example

See `example_rune_controller_usage.py` for a complete working example.

## Future Enhancements

The following functionality will be added in future tasks:

- **Preset Application** (Task 4.2): Apply presets to slots
- **Active Slot Management** (Task 4.2): Set which slot is active
- **Rune Editing** (Task 4.3): Update individual runes in active slot
- **Page Validation** (Task 4.4): Validate page structure before applying

## Constants

- `VALID_STYLE_IDS`: {8000, 8100, 8200, 8300, 8400}
- `MAX_PAGES`: 25
- `SLOT_NAMES`: ["App Slot 1", "App Slot 2", "App Slot 3"]

## LCU API Endpoints Used

- `GET /lol-perks/v1/pages` - Fetch existing rune pages
- `POST /lol-perks/v1/pages` - Create new rune page

## Dependencies

- `lcu_connection.LCUConnection` - For LCU API communication
- `preset_provider.RunePage` - For rune page data structure
