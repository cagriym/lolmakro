/**
 * API Service Layer for LoL Rune Page Manager
 * 
 * Provides HTTP client for REST API calls with comprehensive error handling,
 * retry logic, and type-safe service methods for all backend endpoints.
 */

import type { RunePage, RuneStyle, Champion, SummonerSpell, LiveGameStats } from "@/types";

// ============================================================================
// Configuration
// ============================================================================

interface ApiConfig {
  baseUrl: string;
  timeout: number;
  maxRetries: number;
  retryDelay: number;
}

const defaultConfig: ApiConfig = {
  baseUrl: import.meta.env.VITE_API_BASE || window.location.origin,
  timeout: 10000, // 10 seconds
  maxRetries: 3,
  retryDelay: 1000, // 1 second
};

// ============================================================================
// Error Types
// ============================================================================

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public response?: any
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class NetworkError extends Error {
  constructor(message: string, public originalError?: Error) {
    super(message);
    this.name = "NetworkError";
  }
}

export class TimeoutError extends Error {
  constructor(message: string = "Request timeout") {
    super(message);
    this.name = "TimeoutError";
  }
}

// ============================================================================
// HTTP Client with Retry Logic
// ============================================================================

/**
 * Sleep utility for retry delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Check if error is retryable (network errors, 5xx errors)
 */
function isRetryableError(error: any): boolean {
  if (error instanceof NetworkError) return true;
  if (error instanceof TimeoutError) return true;
  if (error instanceof ApiError) {
    const status = error.statusCode;
    return status !== undefined && status >= 500 && status < 600;
  }
  return false;
}

/**
 * Make HTTP request with timeout and retry logic
 */
async function requestWithRetry<T>(
  path: string,
  options: RequestInit = {},
  config: ApiConfig = defaultConfig
): Promise<T> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
    try {
      // Create abort controller for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), config.timeout);

      try {
        const response = await fetch(`${config.baseUrl}${path}`, {
          ...options,
          signal: controller.signal,
          headers: {
            "Content-Type": "application/json",
            ...options.headers,
          },
        });

        clearTimeout(timeoutId);

        // Parse response
        const text = await response.text();
        let parsed: any;
        try {
          parsed = text ? JSON.parse(text) : null;
        } catch {
          parsed = text;
        }

        // Handle HTTP errors
        if (!response.ok) {
          const message =
            typeof parsed === "object" && parsed?.detail
              ? parsed.detail
              : typeof parsed === "string"
              ? parsed
              : `HTTP ${response.status}`;

          throw new ApiError(message, response.status, parsed);
        }

        return parsed as T;
      } catch (error: any) {
        clearTimeout(timeoutId);

        // Handle abort (timeout)
        if (error.name === "AbortError") {
          throw new TimeoutError(`Request timeout after ${config.timeout}ms`);
        }

        // Handle network errors
        if (error instanceof TypeError && error.message.includes("fetch")) {
          throw new NetworkError("Network request failed", error);
        }

        throw error;
      }
    } catch (error: any) {
      lastError = error;

      // Don't retry on client errors (4xx) or non-retryable errors
      if (!isRetryableError(error)) {
        throw error;
      }

      // Don't retry on last attempt
      if (attempt === config.maxRetries) {
        throw error;
      }

      // Exponential backoff
      const delay = config.retryDelay * Math.pow(2, attempt);
      await sleep(delay);
    }
  }

  throw lastError || new Error("Request failed after retries");
}

/**
 * Convenience wrapper for GET requests
 */
async function get<T>(path: string, config?: ApiConfig): Promise<T> {
  return requestWithRetry<T>(path, { method: "GET" }, config);
}

/**
 * Convenience wrapper for POST requests
 */
async function post<T>(
  path: string,
  body?: any,
  config?: ApiConfig
): Promise<T> {
  return requestWithRetry<T>(
    path,
    {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    },
    config
  );
}

/**
 * Convenience wrapper for PATCH requests
 */
async function patch<T>(
  path: string,
  body?: any,
  config?: ApiConfig
): Promise<T> {
  return requestWithRetry<T>(
    path,
    {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    },
    config
  );
}

/**
 * Convenience wrapper for PUT requests
 * @internal Reserved for future use
 */
// @ts-expect-error - Reserved for future use
async function put<T>(
  path: string,
  body?: any,
  config?: ApiConfig
): Promise<T> {
  return requestWithRetry<T>(
    path,
    {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    },
    config
  );
}

/**
 * Convenience wrapper for DELETE requests
 * @internal Reserved for future use
 */
// @ts-expect-error - Reserved for future use
async function del<T>(path: string, config?: ApiConfig): Promise<T> {
  return requestWithRetry<T>(path, { method: "DELETE" }, config);
}

// ============================================================================
// Response Types
// ============================================================================

interface HealthResponse {
  ok: boolean;
  timestamp: string;
  initialized: boolean;
}

interface StateResponse {
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

interface SuccessResponse {
  success: boolean;
  message: string;
}

interface EditModeResponse {
  success: boolean;
  editMode: boolean;
}

// ============================================================================
// API Service
// ============================================================================

/**
 * API service with methods for all backend endpoints
 */
export const api = {
  // --------------------------------------------------------------------------
  // Health & State
  // --------------------------------------------------------------------------

  /**
   * Health check endpoint
   */
  health: (): Promise<HealthResponse> => get("/api/health"),

  /**
   * Get current application state
   */
  getState: (): Promise<StateResponse> => get("/api/state"),

  /**
   * Get available presets for current context
   */
  getPresets: (): Promise<RunePage[]> => get("/api/presets"),

  /**
   * Get all rune pages (user-created and app-managed)
   */
  getPages: (): Promise<RunePage[]> => get("/api/pages"),

  // --------------------------------------------------------------------------
  // Preset Management
  // --------------------------------------------------------------------------

  /**
   * Select and apply a preset to an app slot
   */
  selectPreset: (presetIndex: number): Promise<SuccessResponse> =>
    post("/api/preset/select", { preset_index: presetIndex }),

  // --------------------------------------------------------------------------
  // Rune Editing
  // --------------------------------------------------------------------------

  /**
   * Edit a rune in the active slot
   */
  editRune: (
    runeId: number,
    slotType:
      | "keystone"
      | "primary1"
      | "primary2"
      | "primary3"
      | "secondary1"
      | "secondary2"
      | "statShard1"
      | "statShard2"
      | "statShard3"
  ): Promise<SuccessResponse> =>
    patch("/api/rune/edit", { rune_id: runeId, slot_type: slotType }),

  /**
   * Toggle edit mode
   */
  setEditMode: (enabled: boolean): Promise<EditModeResponse> =>
    post("/api/edit-mode", { enabled }),

  // --------------------------------------------------------------------------
  // Champion Select Actions (Future endpoints - not yet implemented)
  // --------------------------------------------------------------------------

  /**
   * Accept ready check
   */
  acceptReadyCheck: (): Promise<SuccessResponse> =>
    post("/api/ready-check/accept", {}),

  /**
   * Ban a champion
   */
  banChampion: (championId: number): Promise<SuccessResponse> =>
    post("/api/champ-select/ban", { championId }),

  /**
   * Hover a champion
   */
  hoverChampion: (championId: number): Promise<SuccessResponse> =>
    post("/api/champ-select/hover", { championId }),

  /**
   * Lock in a champion
   */
  lockChampion: (championId: number): Promise<SuccessResponse> =>
    post("/api/champ-select/lock", { championId }),

  /**
   * Update summoner spells
   */
  updateSpells: (spell1Id: number, spell2Id: number): Promise<SuccessResponse> =>
    post("/api/champ-select/spells", { spell1Id, spell2Id }),

  // --------------------------------------------------------------------------
  // Data Fetching (Future endpoints - not yet implemented)
  // --------------------------------------------------------------------------

  /**
   * Get champion catalog
   */
  getChampions: (): Promise<Champion[]> => get("/api/champions"),

  /**
   * Get summoner spell catalog
   */
  getSpells: (): Promise<SummonerSpell[]> => get("/api/spells"),

  /**
   * Get current summoner spell selection
   */
  getCurrentSpells: (): Promise<{ spell1Id: number; spell2Id: number }> =>
    get("/api/spells/current"),

  /**
   * Get rune styles (rune trees with all perks)
   */
  getRuneStyles: (): Promise<RuneStyle[]> => get("/api/runes/styles"),

  /**
   * Apply a complete rune page configuration
   */
  applyRunePage: (config: RunePage): Promise<SuccessResponse> =>
    post("/api/runes/apply", config),

  /**
   * Get build suggestions for a champion
   */
  getBuildSuggestions: (championId: number): Promise<any> =>
    get(`/api/builds/suggestions/${championId}`),

  // --------------------------------------------------------------------------
  // Live Game Stats
  // --------------------------------------------------------------------------

  /**
   * Get live game statistics
   */
  getLiveStats: (): Promise<LiveGameStats> => get("/api/live-stats"),
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Configure API base URL (useful for testing or custom deployments)
 */
export function setApiBaseUrl(url: string): void {
  defaultConfig.baseUrl = url;
}

/**
 * Configure request timeout
 */
export function setApiTimeout(ms: number): void {
  defaultConfig.timeout = ms;
}

/**
 * Configure retry settings
 */
export function setRetryConfig(maxRetries: number, retryDelay: number): void {
  defaultConfig.maxRetries = maxRetries;
  defaultConfig.retryDelay = retryDelay;
}

/**
 * Get current API configuration
 */
export function getApiConfig(): Readonly<ApiConfig> {
  return { ...defaultConfig };
}
