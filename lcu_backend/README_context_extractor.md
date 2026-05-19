# Context Extractor

The Context Extractor component extracts champion select context from `ChampSelectSession` data provided by the LCU Monitor. It parses session data to identify the local player's selected champion, assigned role, queue type, and current phase.

## Overview

The context extractor provides a clean interface for extracting relevant information from the complex champion select session data structure. It handles edge cases such as:

- Champion not yet selected (championId = 0 or None)
- Missing or incomplete session data
- Empty or missing role assignments
- Role name variations and normalization
- Queue ID inference from session data

## Data Models

### ChampSelectContext

```python
@dataclass
class ChampSelectContext:
    """Champion select context containing champion, queue, role, and phase information"""
    champion_id: int      # Selected champion ID (e.g., 64 for Lee Sin)
    queue_id: int         # Queue type ID (e.g., 420 for Ranked Solo/Duo)
    role: str             # Assigned role: "top", "jungle", "middle", "bottom", "utility", or "none"
    phase: str            # Current phase: "PLANNING", "BAN_PICK", or "FINALIZATION"
```

## Main Function

### extract_champ_select_context()

```python
def extract_champ_select_context(session: ChampSelectSession) -> ChampSelectContext | None
```

Extracts champion select context from a `ChampSelectSession` object.

**Parameters:**
- `session`: ChampSelectSession object from LCU Monitor

**Returns:**
- `ChampSelectContext` if champion is selected and valid
- `None` if:
  - Session is None
  - Local player not found in team
  - Champion not selected (championId = 0 or None)

**Example:**

```python
from lcu_backend import extract_champ_select_context, ChampSelectSession

# Assume we have a session from LCU Monitor
session = ChampSelectSession(
    local_player_cell_id=1,
    my_team=[
        {"cellId": 1, "championId": 64, "assignedPosition": "jungle"}
    ],
    timer={"phase": "BAN_PICK"},
    actions=[],
    raw_data={"queueId": 420}
)

context = extract_champ_select_context(session)

if context:
    print(f"Champion: {context.champion_id}")
    print(f"Queue: {context.queue_id}")
    print(f"Role: {context.role}")
    print(f"Phase: {context.phase}")
else:
    print("Champion not selected yet")
```

## Helper Functions

### _normalize_role()

Normalizes role strings to standard format. Handles common variations:

- `"mid"` → `"middle"`
- `"bot"`, `"adc"` → `"bottom"`
- `"support"` → `"utility"`
- Empty or unknown → `"none"`

Case-insensitive.

### _infer_queue_id()

Infers queue ID from session raw data. Looks for `queueId` field in the session's raw data. Returns 0 if not found.

## Role Normalization

The context extractor normalizes role strings to one of the following standard values:

| Standard Role | Variations Accepted |
|--------------|---------------------|
| `"top"` | top, TOP |
| `"jungle"` | jungle, JUNGLE |
| `"middle"` | middle, mid, MIDDLE, MID |
| `"bottom"` | bottom, bot, adc, BOTTOM, BOT, ADC |
| `"utility"` | utility, support, UTILITY, SUPPORT |
| `"none"` | (empty), (unknown values) |

## Queue IDs

Common queue IDs you may encounter:

| Queue ID | Description |
|----------|-------------|
| 420 | Ranked Solo/Duo |
| 440 | Ranked Flex |
| 450 | ARAM |
| 400 | Draft Pick |
| 430 | Blind Pick |
| 490 | Quickplay |

## Integration with LCU Monitor

The context extractor is designed to work seamlessly with the LCU Monitor:

```python
import asyncio
from lcu_backend import LCUConnection, LCUMonitor, extract_champ_select_context

async def on_champ_select_change(session):
    context = extract_champ_select_context(session)
    
    if context:
        print(f"Champion {context.champion_id} selected for {context.role}")
        # Fetch rune presets for this context
        # presets = preset_provider.get_presets(context)
    else:
        print("Waiting for champion selection...")

async def main():
    connection = LCUConnection()
    await connection.connect()
    
    monitor = LCUMonitor(connection)
    monitor.on_champ_select_change(on_champ_select_change)
    
    await monitor.start()
    # ... keep running ...

asyncio.run(main())
```

## Error Handling

The context extractor is designed to handle errors gracefully:

- **None session**: Returns `None`
- **Local player not found**: Returns `None`
- **Champion not selected**: Returns `None`
- **Missing role**: Defaults to `"none"`
- **Missing queue ID**: Defaults to `0`
- **Missing phase**: Defaults to `"PLANNING"`

No exceptions are raised for invalid data; the function returns `None` or uses sensible defaults.

## Testing

The context extractor includes comprehensive unit tests covering:

- Valid session extraction
- Champion not selected scenarios
- Missing or incomplete data
- Role normalization (all variations)
- Queue ID inference
- Edge cases (None values, empty strings, etc.)

Run tests with:

```bash
python -m pytest lcu_backend/test_context_extractor.py -v
```

## Requirements Satisfied

This implementation satisfies the following requirements:

- **3.1**: Fetches champion select session data (via LCU Monitor)
- **3.2**: Extracts local player's champion ID from session
- **3.3**: Extracts local player's assigned role from session
- **3.4**: Extracts queue ID from session
- **3.5**: Returns null context when champion not selected
- **3.6**: Treats championId 0 or null as no champion selected
- **3.7**: Defaults role to "none" when empty or null

## Next Steps

The extracted context is used by the Preset Provider to query appropriate rune page presets:

```python
# After extracting context
context = extract_champ_select_context(session)

if context:
    # Query presets using the context
    presets = preset_provider.get_presets(
        champion_id=context.champion_id,
        queue_id=context.queue_id,
        role=context.role
    )
    
    # Display presets to user
    # ...
```
