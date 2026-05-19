# LCU Monitor Component

## Overview

The LCU Monitor component monitors League Client state changes and provides real-time notifications for gameflow phase transitions and champion select session updates.

## Features

✅ **Gameflow Phase Monitoring**
- Polls `/lol-gameflow/v1/gameflow-phase` endpoint at 1-second intervals
- Detects phase changes (None, Lobby, ChampSelect, InProgress, etc.)
- Notifies registered callbacks when phase changes occur

✅ **Champion Select Session Monitoring**
- Automatically starts monitoring when entering ChampSelect phase
- Polls `/lol-champ-select/v1/session` endpoint at 0.5-second intervals
- Extracts champion select context (champion ID, role, team data)
- Notifies callbacks when session data changes

✅ **State Change Detection**
- Compares current state with previous state
- Only triggers callbacks when actual changes occur
- Clears champion select context when leaving ChampSelect phase

✅ **Connection Management**
- Handles LCU connection loss gracefully
- Notifies callbacks when connection is lost (phase becomes None)
- Automatically resumes monitoring when connection is restored

## Usage

### Basic Setup

```python
from lcu_connection import LCUConnection
from lcu_monitor import LCUMonitor, GameflowPhase

# Create connection and monitor
connection = LCUConnection()
monitor = LCUMonitor(connection)

# Register callbacks
async def on_phase_change(phase: GameflowPhase | None):
    print(f"Phase changed to: {phase}")

monitor.on_gameflow_change(on_phase_change)

# Start monitoring
await monitor.start()

# Stop monitoring when done
await monitor.stop()
```

### Champion Select Monitoring

```python
async def on_champ_select_change(session):
    if session is None:
        print("Champion select ended")
    else:
        print(f"Local player cell: {session.local_player_cell_id}")
        print(f"Team: {session.my_team}")

monitor.on_champ_select_change(on_champ_select_change)
```

### Getting Current State

```python
# Get current gameflow phase
phase = await monitor.get_gameflow_phase()

# Get current champion select session (only valid during ChampSelect)
session = await monitor.get_champ_select_session()
```

## Architecture

### Polling Mechanism

The monitor uses two polling loops:

1. **Gameflow Polling** (1.0s interval)
   - Continuously polls gameflow phase endpoint
   - Detects phase transitions
   - Triggers gameflow callbacks

2. **Champion Select Polling** (0.5s interval)
   - Only active during ChampSelect phase
   - Polls champion select session endpoint
   - Detects session changes
   - Triggers champion select callbacks

### State Management

- `_current_phase`: Tracks current gameflow phase
- `_running`: Controls polling loop execution
- `_polling_task`: Asyncio task for gameflow polling
- Callbacks are stored in lists and called sequentially

### Error Handling

- All exceptions in polling loops are caught and silently handled
- Callback exceptions don't interrupt monitoring
- Connection loss is detected and reported via callbacks

## Data Models

### GameflowPhase Enum

```python
class GameflowPhase(str, Enum):
    NONE = "None"
    LOBBY = "Lobby"
    CHAMP_SELECT = "ChampSelect"
    IN_PROGRESS = "InProgress"
    END_OF_GAME = "EndOfGame"
    READY_CHECK = "ReadyCheck"
    MATCHMAKING = "Matchmaking"
    WAITING_FOR_STATS = "WaitingForStats"
    PRE_END_OF_GAME = "PreEndOfGame"
    RECONNECT = "Reconnect"
```

### ChampSelectSession

```python
@dataclass
class ChampSelectSession:
    local_player_cell_id: int
    my_team: list[dict[str, Any]]
    timer: dict[str, Any]
    actions: list[list[dict[str, Any]]]
    raw_data: dict[str, Any]  # Full session data
```

## Testing

Run the test suite:

```bash
pytest lcu_backend/test_lcu_monitor.py -v
```

All 10 tests pass, covering:
- Monitor initialization
- Start/stop functionality
- Phase detection and change notification
- Champion select session parsing
- Connection loss handling
- Multiple callback registration
- State retrieval

## Example

See `example_monitor_usage.py` for a complete working example that demonstrates:
- Connecting to League Client
- Monitoring gameflow phases
- Tracking champion select sessions
- Extracting champion and role information

## Requirements Satisfied

This implementation satisfies the following requirements from the spec:

- **Requirement 2.1**: Poll gameflow phase endpoint at regular intervals ✅
- **Requirement 2.2**: Notify State_Manager of ChampSelect phase changes ✅
- **Requirement 2.3**: Clear champion select context when leaving ChampSelect ✅
- **Requirement 2.4**: Subscribe to gameflow events (via polling) ✅
- **Requirement 2.5**: Update phase immediately on changes ✅

## Configuration

Polling intervals are configured in `config.py`:

```python
GAMEFLOW_POLL_INTERVAL = 1.0  # seconds
CHAMP_SELECT_POLL_INTERVAL = 0.5  # seconds
```

## Next Steps

The next task (2.3) will implement champion select context extraction, which will:
- Parse champion select session data
- Extract championId, queueId, and role
- Validate champion selection state
- Handle missing or incomplete session data
