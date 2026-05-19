/**
 * API Service Usage Examples
 * 
 * Demonstrates how to use the API service layer for various operations.
 */

import { useState } from "react";
import { api, ApiError, NetworkError, TimeoutError } from "@services/api";
import type { RunePage } from "@/types";

export function ApiExample() {
  const [status, setStatus] = useState<string>("Ready");
  const [error, setError] = useState<string | null>(null);
  const [presets, setPresets] = useState<RunePage[]>([]);

  // Example 1: Health Check
  const checkHealth = async () => {
    try {
      setStatus("Checking health...");
      setError(null);
      
      const health = await api.health();
      setStatus(`Server OK: ${health.initialized ? "Initialized" : "Not initialized"}`);
    } catch (err) {
      handleError(err, "Health check failed");
    }
  };

  // Example 2: Get Current State
  const fetchState = async () => {
    try {
      setStatus("Fetching state...");
      setError(null);
      
      const state = await api.getState();
      setStatus(`Phase: ${state.gameflowPhase}, Presets: ${state.availablePresets.length}`);
    } catch (err) {
      handleError(err, "Failed to fetch state");
    }
  };

  // Example 3: Get Available Presets
  const fetchPresets = async () => {
    try {
      setStatus("Fetching presets...");
      setError(null);
      
      const fetchedPresets = await api.getPresets();
      setPresets(fetchedPresets);
      setStatus(`Found ${fetchedPresets.length} presets`);
    } catch (err) {
      handleError(err, "Failed to fetch presets");
    }
  };

  // Example 4: Select a Preset
  const selectPreset = async (index: number) => {
    try {
      setStatus(`Selecting preset ${index}...`);
      setError(null);
      
      const result = await api.selectPreset(index);
      setStatus(result.message);
    } catch (err) {
      handleError(err, "Failed to select preset");
    }
  };

  // Example 5: Edit a Rune
  const editRune = async () => {
    try {
      setStatus("Editing rune...");
      setError(null);
      
      // Example: Change keystone to Electrocute (8128)
      const result = await api.editRune(8128, "keystone");
      setStatus(result.message);
    } catch (err) {
      handleError(err, "Failed to edit rune");
    }
  };

  // Example 6: Toggle Edit Mode
  const toggleEditMode = async (enabled: boolean) => {
    try {
      setStatus(`${enabled ? "Enabling" : "Disabling"} edit mode...`);
      setError(null);
      
      const result = await api.setEditMode(enabled);
      setStatus(`Edit mode: ${result.editMode ? "ON" : "OFF"}`);
    } catch (err) {
      handleError(err, "Failed to toggle edit mode");
    }
  };

  // Example 7: Get All Rune Pages
  const fetchPages = async () => {
    try {
      setStatus("Fetching rune pages...");
      setError(null);
      
      const pages = await api.getPages();
      setStatus(`Found ${pages.length} rune pages`);
    } catch (err) {
      handleError(err, "Failed to fetch pages");
    }
  };

  // Example 8: Champion Select Actions
  const banChampion = async (championId: number) => {
    try {
      setStatus(`Banning champion ${championId}...`);
      setError(null);
      
      const result = await api.banChampion(championId);
      setStatus(result.message);
    } catch (err) {
      handleError(err, "Failed to ban champion");
    }
  };

  // Example 9: Update Summoner Spells
  const updateSpells = async () => {
    try {
      setStatus("Updating summoner spells...");
      setError(null);
      
      // Example: Flash (4) + Ignite (14)
      const result = await api.updateSpells(4, 14);
      setStatus(result.message);
    } catch (err) {
      handleError(err, "Failed to update spells");
    }
  };

  // Example 10: Get Live Game Stats
  const fetchLiveStats = async () => {
    try {
      setStatus("Fetching live stats...");
      setError(null);
      
      const stats = await api.getLiveStats();
      setStatus(`Game time: ${Math.floor(stats.gameTime / 60)}:${(stats.gameTime % 60).toString().padStart(2, "0")}`);
    } catch (err) {
      handleError(err, "Failed to fetch live stats");
    }
  };

  // Comprehensive Error Handling
  const handleError = (err: unknown, context: string) => {
    if (err instanceof ApiError) {
      // HTTP error (4xx, 5xx)
      setError(`${context}: ${err.message} (Status: ${err.statusCode})`);
      setStatus("Error");
      
      // Handle specific status codes
      if (err.statusCode === 400) {
        console.error("Validation error:", err.response);
      } else if (err.statusCode === 500) {
        console.error("Server error:", err.response);
      }
    } else if (err instanceof NetworkError) {
      // Network failure
      setError(`${context}: Network error - Server may be unreachable`);
      setStatus("Network Error");
    } else if (err instanceof TimeoutError) {
      // Request timeout
      setError(`${context}: Request timeout - Server is not responding`);
      setStatus("Timeout");
    } else {
      // Unknown error
      setError(`${context}: ${err instanceof Error ? err.message : "Unknown error"}`);
      setStatus("Error");
    }
  };

  return (
    <div style={{ padding: "20px", fontFamily: "monospace" }}>
      <h1>API Service Examples</h1>
      
      <div style={{ marginBottom: "20px", padding: "10px", background: "#f0f0f0" }}>
        <strong>Status:</strong> {status}
        {error && (
          <div style={{ color: "red", marginTop: "10px" }}>
            <strong>Error:</strong> {error}
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "10px" }}>
        <button onClick={checkHealth}>1. Health Check</button>
        <button onClick={fetchState}>2. Get State</button>
        <button onClick={fetchPresets}>3. Get Presets</button>
        <button onClick={() => selectPreset(0)}>4. Select Preset 0</button>
        <button onClick={editRune}>5. Edit Rune</button>
        <button onClick={() => toggleEditMode(true)}>6. Enable Edit Mode</button>
        <button onClick={fetchPages}>7. Get All Pages</button>
        <button onClick={() => banChampion(157)}>8. Ban Yasuo</button>
        <button onClick={updateSpells}>9. Update Spells</button>
        <button onClick={fetchLiveStats}>10. Get Live Stats</button>
      </div>

      {presets.length > 0 && (
        <div style={{ marginTop: "20px" }}>
          <h2>Available Presets</h2>
          <ul>
            {presets.map((preset, index) => (
              <li key={index}>
                <strong>{preset.name}</strong>
                <br />
                Primary: {preset.primaryStyleId}, Sub: {preset.subStyleId}
                <br />
                Perks: {preset.selectedPerkIds.join(", ")}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ marginTop: "40px", padding: "10px", background: "#e8f4f8" }}>
        <h3>Error Handling Examples</h3>
        <p>
          The API service provides comprehensive error handling with specific error types:
        </p>
        <ul>
          <li><strong>ApiError:</strong> HTTP errors (4xx, 5xx) with status codes</li>
          <li><strong>NetworkError:</strong> Network failures (server unreachable)</li>
          <li><strong>TimeoutError:</strong> Request timeouts (server not responding)</li>
        </ul>
        <p>
          All requests automatically retry on network errors and 5xx errors with exponential backoff.
        </p>
      </div>
    </div>
  );
}
