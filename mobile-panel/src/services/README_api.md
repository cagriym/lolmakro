# API Service Layer

The API service layer provides a comprehensive HTTP client for communicating with the backend server. It includes robust error handling, automatic retry logic with exponential backoff, and type-safe service methods for all backend endpoints.

## Features

- **Type-Safe API Methods**: All endpoints have strongly-typed request/response interfaces
- **Automatic Retry Logic**: Failed requests are automatically retried with exponential backoff
- **Error Handling**: Comprehensive error types (ApiError, NetworkError, TimeoutError)
- **Request Timeout**: Configurable timeout for all requests (default: 10 seconds)
- **Environment Configuration**: API base URL configurable via environment variables
- **Network Resilience**: Handles network failures, timeouts, and server errors gracefully

## Usage

### Basic Usage

```typescript
import { api } from "@services/api";

// Health check
const health = await api.health();
console.log(health.ok); // true

// Get current state
const state = await api.getState();
console.log(state.gameflowPhase); // "ChampSelect"

// Select a preset
await api.selectPreset(0);

// Edit a rune
await api.editRune(8128, "keystone");
```

### Error Handling

```typescript
import { api, ApiError, NetworkError, TimeoutError } from "@services/api";

try {
  await api.selectPreset(5);
} catch (error) {
  if (error instanceof ApiError) {
    // HTTP error (4xx, 5xx)
    console.error(`API Error ${error.statusCode}: ${error.message}`);
  } else if (error instanceof NetworkError) {
    // Network failure
    console.error("Network error:", error.message);
  } else if (error instanceof TimeoutError) {
    // Request timeout
    console.error("Request timeout");
  }
}
```

### Configuration

```typescript
import { setApiBaseUrl, setApiTimeout, setRetryConfig } from "@services/api";

// Set custom API base URL
setApiBaseUrl("http://192.168.1.100:8765");

// Set request timeout (milliseconds)
setApiTimeout(5000);

// Configure retry behavior (maxRetries, retryDelay in ms)
setRetryConfig(5, 2000);
```

## API Methods

### Health & State

#### `api.health()`
Health check endpoint to verify server is running.

**Returns:** `Promise<HealthResponse>`
```typescript
{
  ok: boolean;
  timestamp: string;
  initialized: boolean;
}
```

#### `api.getState()`
Get current application state including gameflow phase, champion select context, available presets, and app slots.

**Returns:** `Promise<StateResponse>`
```typescript
{
  timestamp: string;
  gameflowPhase: string;
  champSelectContext: {
    championId: number;
    queueId: number;
    role: string;
    phase: string;
  } | null;
  availablePresets: RunePage[];
  selectedPresetIndex: number | null;
  appSlots: Array<{
    slotIndex: number;
    pageId: number | null;
    name: string;
    isActive: boolean;
    currentPage: RunePage | null;
  }>;
  activeSlotIndex: number | null;
  isEditMode: boolean;
}
```

#### `api.getPresets()`
Get available presets for current champion select context.

**Returns:** `Promise<RunePage[]>`

#### `api.getPages()`
Get all rune pages (both user-created and app-managed).

**Returns:** `Promise<RunePage[]>`

### Preset Management

#### `api.selectPreset(presetIndex: number)`
Select and apply a preset to an app slot.

**Parameters:**
- `presetIndex` - Index of preset to apply (0-2)

**Returns:** `Promise<SuccessResponse>`
```typescript
{
  success: boolean;
  message: string;
}
```

**Errors:**
- `ApiError` with status 400 if preset index is invalid
- `ApiError` with status 500 if LCU operation fails

### Rune Editing

#### `api.editRune(runeId: number, slotType: string)`
Edit a rune in the active slot.

**Parameters:**
- `runeId` - ID of the rune to apply
- `slotType` - Slot to update: `"keystone"`, `"primary1"`, `"primary2"`, `"primary3"`, `"secondary1"`, `"secondary2"`, `"statShard1"`, `"statShard2"`, `"statShard3"`

**Returns:** `Promise<SuccessResponse>`

**Errors:**
- `ApiError` with status 400 if rune is incompatible with slot
- `ApiError` with status 500 if LCU operation fails

#### `api.setEditMode(enabled: boolean)`
Toggle edit mode on/off.

**Parameters:**
- `enabled` - Whether to enable edit mode

**Returns:** `Promise<EditModeResponse>`
```typescript
{
  success: boolean;
  editMode: boolean;
}
```

### Champion Select Actions

#### `api.acceptReadyCheck()`
Accept the ready check.

**Returns:** `Promise<SuccessResponse>`

#### `api.banChampion(championId: number)`
Ban a champion during champion select.

**Parameters:**
- `championId` - ID of champion to ban

**Returns:** `Promise<SuccessResponse>`

#### `api.hoverChampion(championId: number)`
Hover a champion during champion select.

**Parameters:**
- `championId` - ID of champion to hover

**Returns:** `Promise<SuccessResponse>`

#### `api.lockChampion(championId: number)`
Lock in a champion during champion select.

**Parameters:**
- `championId` - ID of champion to lock

**Returns:** `Promise<SuccessResponse>`

#### `api.updateSpells(spell1Id: number, spell2Id: number)`
Update summoner spells during champion select.

**Parameters:**
- `spell1Id` - ID of first summoner spell
- `spell2Id` - ID of second summoner spell

**Returns:** `Promise<SuccessResponse>`

### Data Fetching

#### `api.getChampions()`
Get list of owned champions.

**Returns:** `Promise<Champion[]>`

#### `api.getSpells()`
Get summoner spell catalog.

**Returns:** `Promise<SummonerSpell[]>`

#### `api.getCurrentSpells()`
Get current summoner spell selection.

**Returns:** `Promise<{ spell1Id: number; spell2Id: number }>`

#### `api.getRuneStyles()`
Get rune styles (rune trees with all perks).

**Returns:** `Promise<RuneStyle[]>`

#### `api.getBuildSuggestions(championId: number)`
Get build suggestions for a champion.

**Parameters:**
- `championId` - ID of champion

**Returns:** `Promise<any>`

### Live Game Stats

#### `api.getLiveStats()`
Get live game statistics for current match.

**Returns:** `Promise<LiveGameStats>`

## Error Types

### `ApiError`
Thrown when the API returns an HTTP error (4xx, 5xx).

**Properties:**
- `message: string` - Error message
- `statusCode?: number` - HTTP status code
- `response?: any` - Raw response data

### `NetworkError`
Thrown when a network request fails (e.g., server unreachable).

**Properties:**
- `message: string` - Error message
- `originalError?: Error` - Original error from fetch

### `TimeoutError`
Thrown when a request exceeds the configured timeout.

**Properties:**
- `message: string` - Error message (includes timeout duration)

## Retry Logic

The API client automatically retries failed requests in the following scenarios:

- **Network Errors**: Connection failures, DNS errors, etc.
- **Server Errors (5xx)**: Internal server errors, service unavailable, etc.
- **Timeouts**: Requests that exceed the configured timeout

**Retry Behavior:**
- Maximum retries: 3 (configurable)
- Retry delay: 1 second base (configurable)
- Exponential backoff: Delay doubles on each retry (1s, 2s, 4s)
- Non-retryable: Client errors (4xx) are not retried

**Example:**
```typescript
// Configure retry behavior
setRetryConfig(5, 2000); // 5 retries, 2 second base delay

// This will retry up to 5 times with delays: 2s, 4s, 8s, 16s, 32s
await api.health();
```

## Configuration

### Environment Variables

Set the API base URL via environment variable:

```bash
# .env
VITE_API_BASE=http://192.168.1.100:8765
```

If not set, defaults to `window.location.origin` (same origin as the web app).

### Runtime Configuration

```typescript
import { setApiBaseUrl, setApiTimeout, setRetryConfig, getApiConfig } from "@services/api";

// Set API base URL
setApiBaseUrl("http://192.168.1.100:8765");

// Set request timeout (10 seconds)
setApiTimeout(10000);

// Set retry config (3 retries, 1 second base delay)
setRetryConfig(3, 1000);

// Get current configuration
const config = getApiConfig();
console.log(config.baseUrl); // "http://192.168.1.100:8765"
console.log(config.timeout); // 10000
console.log(config.maxRetries); // 3
console.log(config.retryDelay); // 1000
```

## Integration with State Management

The API service is designed to work seamlessly with the Zustand store:

```typescript
import { api } from "@services/api";
import { useAppStore } from "@store/useAppStore";

// In a React component or effect
const updateState = async () => {
  try {
    const state = await api.getState();
    useAppStore.setState({
      phase: state.gameflowPhase,
      champSelect: state.champSelectContext,
    });
  } catch (error) {
    console.error("Failed to fetch state:", error);
  }
};
```

## Best Practices

### 1. Always Handle Errors

```typescript
try {
  await api.selectPreset(0);
} catch (error) {
  // Show user-friendly error message
  console.error("Failed to apply preset:", error);
}
```

### 2. Use Type Guards for Error Handling

```typescript
import { ApiError, NetworkError, TimeoutError } from "@services/api";

try {
  await api.health();
} catch (error) {
  if (error instanceof ApiError && error.statusCode === 400) {
    // Handle validation error
  } else if (error instanceof NetworkError) {
    // Handle network error
  } else if (error instanceof TimeoutError) {
    // Handle timeout
  }
}
```

### 3. Configure for Your Network

```typescript
// For slower networks, increase timeout and retries
setApiTimeout(15000); // 15 seconds
setRetryConfig(5, 2000); // 5 retries, 2 second base delay
```

### 4. Use with React Query (Optional)

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "@services/api";

function useGameState() {
  return useQuery({
    queryKey: ["gameState"],
    queryFn: () => api.getState(),
    refetchInterval: 1000, // Poll every second
  });
}
```

## Performance Considerations

- **Request Timeout**: Default 10 seconds prevents hanging requests
- **Retry Backoff**: Exponential backoff prevents overwhelming the server
- **Connection Reuse**: Fetch API reuses HTTP connections automatically
- **JSON Parsing**: Efficient JSON parsing with error handling

## Security Considerations

- **CORS**: Server must enable CORS for local network access
- **HTTPS**: Use HTTPS in production environments
- **Input Validation**: All request parameters are validated by the backend
- **Error Messages**: Error messages are sanitized to prevent information disclosure

## Future Enhancements

- Request cancellation support
- Request deduplication
- Response caching
- Request batching
- WebSocket fallback for real-time updates
- Offline queue for failed requests

## Related Documentation

- [WebSocket Service](./README_websocket.md) - Real-time state synchronization
- [Backend API Server](../../lcu_backend/README_api_server.md) - Backend endpoint documentation
- [Type Definitions](../types/index.ts) - TypeScript type definitions
