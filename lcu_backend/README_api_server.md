# API Server

The API Server provides HTTP REST endpoints and WebSocket support for the mobile interface. It exposes backend functionality through a FastAPI-based server that listens on the local network, allowing mobile devices to connect and interact with the rune page manager.

## Requirements

- **12.1**: Mobile Web Interface Access - Serve mobile-optimized web interface via HTTP on local network
- **13.1**: Real-Time State Synchronization - WebSocket connection for state updates

## Features

- **REST API**: HTTP endpoints for querying state and triggering actions
- **WebSocket**: Real-time state updates broadcast to all connected clients
- **CORS Enabled**: Allows mobile devices on local network to connect
- **Network Access**: Listens on 0.0.0.0 (all network interfaces) for local network access
- **State Integration**: Integrates with StateManager to coordinate backend operations

## Architecture

```
Mobile Device (Browser)
    |
    | HTTP/WebSocket
    v
API Server (FastAPI)
    |
    | State Changes
    v
StateManager
    |
    +-- LCU Monitor
    +-- Preset Provider
    +-- Rune Page Controller
```

## API Endpoints

### Health Check

**GET /api/health**

Returns server health status and initialization state.

**Response:**
```json
{
  "ok": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "initialized": true
}
```

### Get Current State

**GET /api/state**

Returns complete application state including gameflow phase, champion select context, available presets, app slots, and edit mode status.

**Response:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "gameflowPhase": "ChampSelect",
  "champSelectContext": {
    "championId": 157,
    "queueId": 420,
    "role": "middle",
    "phase": "BAN_PICK"
  },
  "availablePresets": [
    {
      "name": "Yasuo - Aggressive",
      "primaryStyleId": 8000,
      "subStyleId": 8100,
      "selectedPerkIds": [8005, 9111, 9104, 8014, 8139, 8135],
      "statShards": [5008, 5008, 5002]
    }
  ],
  "selectedPresetIndex": null,
  "appSlots": [
    {
      "slotIndex": 0,
      "pageId": 12345,
      "name": "App Slot 1",
      "isActive": false,
      "currentPage": null
    }
  ],
  "activeSlotIndex": null,
  "isEditMode": false
}
```

### Get Available Presets

**GET /api/presets**

Returns list of available presets for current champion select context.

**Response:**
```json
[
  {
    "name": "Yasuo - Aggressive",
    "primaryStyleId": 8000,
    "subStyleId": 8100,
    "selectedPerkIds": [8005, 9111, 9104, 8014, 8139, 8135],
    "statShards": [5008, 5008, 5002]
  }
]
```

### Select Preset

**POST /api/preset/select**

Select and apply a preset to an app slot.

**Request Body:**
```json
{
  "preset_index": 0
}
```

**Response:**
```json
{
  "success": true,
  "message": "Preset 0 applied successfully"
}
```

**Errors:**
- 400: Invalid preset index or no presets available
- 500: Failed to apply preset (LCU error)

### Edit Rune

**PATCH /api/rune/edit**

Edit a rune in the active slot.

**Request Body:**
```json
{
  "rune_id": 8128,
  "slot_type": "keystone"
}
```

**Valid slot types:**
- `keystone` - Primary keystone rune
- `primary1`, `primary2`, `primary3` - Primary tree slots
- `secondary1`, `secondary2` - Secondary tree slots
- `statShard1`, `statShard2`, `statShard3` - Stat shard slots

**Response:**
```json
{
  "success": true,
  "message": "Rune 8128 applied to keystone"
}
```

**Errors:**
- 400: Invalid rune ID, slot type, or rune incompatible with slot
- 500: Failed to update rune (LCU error)

### Set Edit Mode

**POST /api/edit-mode**

Toggle edit mode on/off.

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "success": true,
  "editMode": true
}
```

### Get All Rune Pages

**GET /api/pages**

Get all rune pages from LCU (both user-created and app-managed).

**Response:**
```json
[
  {
    "id": 12345,
    "name": "App Slot 1",
    "current": true,
    "primaryStyleId": 8000,
    "subStyleId": 8100,
    "selectedPerkIds": [8005, 9111, 9104, 8014, 8139, 8135, 5008, 5008, 5002],
    "isDeletable": true,
    "isEditable": true
  }
]
```

## WebSocket

### Connection

**WS /ws**

WebSocket endpoint for real-time state updates.

**Connection Flow:**
1. Client connects to `ws://<host>:<port>/ws`
2. Server sends initial state immediately
3. Server broadcasts state updates whenever state changes
4. Client can send ping messages to keep connection alive

**Initial Message (on connect):**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "gameflowPhase": "ChampSelect",
  "champSelectContext": { ... },
  "availablePresets": [ ... ],
  "appSlots": [ ... ],
  "activeSlotIndex": null,
  "isEditMode": false
}
```

**State Update Messages:**
Same format as initial message, sent whenever:
- Gameflow phase changes
- Champion select context changes
- Preset is applied
- Rune is edited
- Edit mode is toggled

## Usage Example

### Starting the Server

```python
import asyncio
from lcu_backend.lcu_monitor import LCUMonitor
from lcu_backend.preset_provider import PresetProvider
from lcu_backend.rune_page_controller import RunePageController
from lcu_backend.state_manager import StateManager
from lcu_backend.api_server import APIServer

async def main():
    # Initialize components
    lcu_monitor = LCUMonitor()
    preset_provider = PresetProvider()
    rune_controller = RunePageController(lcu_monitor)
    state_manager = StateManager(lcu_monitor, preset_provider, rune_controller)
    
    # Create and start API server
    api_server = APIServer(
        state_manager=state_manager,
        host="0.0.0.0",  # Listen on all network interfaces
        port=8765
    )
    
    await api_server.start()

asyncio.run(main())
```

### Client Example (JavaScript)

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://192.168.1.100:8765/ws');

ws.onopen = () => {
  console.log('Connected to API server');
};

ws.onmessage = (event) => {
  const state = JSON.parse(event.data);
  console.log('State update:', state);
  // Update UI with new state
};

// Select a preset
async function selectPreset(index) {
  const response = await fetch('http://192.168.1.100:8765/api/preset/select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ preset_index: index })
  });
  const result = await response.json();
  console.log('Preset applied:', result);
}

// Edit a rune
async function editRune(runeId, slotType) {
  const response = await fetch('http://192.168.1.100:8765/api/rune/edit', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rune_id: runeId, slot_type: slotType })
  });
  const result = await response.json();
  console.log('Rune edited:', result);
}
```

## Configuration

### Environment Variables

- `API_HOST`: Host address to bind to (default: `0.0.0.0`)
- `API_PORT`: Port to listen on (default: `8765`)

### Network Access

The server listens on `0.0.0.0` by default, which means it accepts connections from any network interface. This allows mobile devices on the same local network to connect.

To find your local IP address:
- **Windows**: `ipconfig` (look for IPv4 Address)
- **macOS/Linux**: `ifconfig` or `ip addr` (look for inet address)

Mobile devices can then connect to `http://<your-local-ip>:8765`

## Error Handling

### HTTP Errors

- **400 Bad Request**: Invalid request parameters (e.g., invalid preset index, incompatible rune)
- **500 Internal Server Error**: Backend operation failed (e.g., LCU connection error)

### WebSocket Errors

- Connection automatically removed if send fails
- Stale connections cleaned up on broadcast
- Client should implement reconnection logic

## Security Considerations

- **Local Network Only**: Server should only be accessible on trusted local networks
- **No Authentication**: Currently no authentication required (assumes trusted local network)
- **CORS Enabled**: Allows all origins for local network access
- **Input Validation**: All request parameters validated with Pydantic models

## Testing

Run the example to test the server:

```bash
python -m lcu_backend.example_api_server_usage
```

Test endpoints with curl:

```bash
# Health check
curl http://localhost:8765/api/health

# Get state
curl http://localhost:8765/api/state

# Select preset
curl -X POST http://localhost:8765/api/preset/select \
  -H "Content-Type: application/json" \
  -d '{"preset_index": 0}'
```

Test WebSocket with a simple client:

```bash
# Install wscat if needed: npm install -g wscat
wscat -c ws://localhost:8765/ws
```

## Integration with Mobile Interface

The mobile interface should:

1. **Connect to WebSocket** on app load to receive real-time updates
2. **Subscribe to state changes** and update UI reactively
3. **Call REST endpoints** for user actions (select preset, edit rune)
4. **Handle disconnections** with automatic reconnection logic
5. **Display connection status** to inform user of server availability

## Performance

- **Latency**: < 100ms for REST endpoints
- **WebSocket**: Real-time updates with minimal delay
- **Concurrent Connections**: Supports multiple mobile devices simultaneously
- **Memory**: Minimal overhead, state serialization is lightweight

## Future Enhancements

- Authentication for secure access
- HTTPS support with self-signed certificates
- Rate limiting to prevent abuse
- Metrics and monitoring endpoints
- Static file serving for mobile web app
