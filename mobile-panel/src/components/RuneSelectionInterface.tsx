// RuneSelectionInterface component - Main rune selection UI

import { useState, useEffect } from "react";
import { RunePresetCard } from "./RunePresetCard";
import { SummonerSpellSlot } from "./SummonerSpellSlot";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/services/api";
import type { PresetOption } from "@/types";
import "./RuneSelectionInterface.css";

interface RuneSelectionInterfaceProps {
  onClose: () => void;
}

export function RuneSelectionInterface({ onClose }: RuneSelectionInterfaceProps) {
  const [presets, setPresets] = useState<PresetOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [activePresetIndex, setActivePresetIndex] = useState<number | null>(null);

  const mySelection = useAppStore((state) => state.mySelection);

  // Fetch presets when component mounts
  useEffect(() => {
    fetchPresets();
  }, []);

  const fetchPresets = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch presets from API
      const response = await api.getPresets();

      // Transform API response to PresetOption format
      const transformedPresets: PresetOption[] = response.map((preset, index) => ({
        slotLabel: `Option ${index + 1}`,
        name: preset.name || `Preset ${index + 1}`,
        primaryStyleId: preset.primaryStyleId || null,
        subStyleId: preset.subStyleId || null,
        selectedPerkIds: preset.selectedPerkIds || [],
        spells: {
          spell1Id: mySelection?.spell1Id || 4, // Default to Flash
          spell2Id: mySelection?.spell2Id || 14, // Default to Ignite
        },
      }));

      setPresets(transformedPresets);
    } catch (err) {
      console.error("Failed to fetch presets:", err);
      setError("Failed to load rune presets. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleApplyPreset = async (index: number) => {
    try {
      setApplying(true);
      setError(null);

      // Apply preset via API
      await api.selectPreset(index);

      // Mark as active
      setActivePresetIndex(index);

      // Show success feedback briefly, then close
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err) {
      console.error("Failed to apply preset:", err);
      setError("Failed to apply preset. Please try again.");
    } finally {
      setApplying(false);
    }
  };

  // Get champion name (placeholder - would need champion data)
  const getChampionName = () => {
    if (!mySelection?.championId) return "Champion";
    // TODO: Look up champion name from champion data
    return `Champion ${mySelection.championId}`;
  };

  return (
    <div className="rune-selection-overlay">
      <div className="rune-selection-container">
        {/* Header */}
        <div className="rune-selection-header">
          <div className="header-content">
            <h2 className="header-title">Rune Presets</h2>
            <p className="header-subtitle">{getChampionName()}</p>
          </div>
          <button
            className="close-button"
            onClick={onClose}
            aria-label="Close"
            disabled={applying}
          >
            ✕
          </button>
        </div>

        {/* Summoner Spells */}
        {mySelection && (
          <div className="summoner-spells-section">
            <h3 className="section-title">Summoner Spells</h3>
            <div className="summoner-spells-container">
              <SummonerSpellSlot
                spellId={mySelection.spell1Id}
                size="medium"
              />
              <SummonerSpellSlot
                spellId={mySelection.spell2Id}
                size="medium"
              />
            </div>
          </div>
        )}

        {/* Content */}
        <div className="rune-selection-content">
          {loading && (
            <div className="loading-state">
              <div className="loading-spinner" />
              <p>Loading presets...</p>
            </div>
          )}

          {error && (
            <div className="error-state">
              <p className="error-message">{error}</p>
              <button className="retry-button" onClick={fetchPresets}>
                Retry
              </button>
            </div>
          )}

          {!loading && !error && presets.length === 0 && (
            <div className="empty-state">
              <p>No presets available for this champion.</p>
            </div>
          )}

          {!loading && !error && presets.length > 0 && (
            <div className="presets-scroll-container">
              <div className="presets-grid">
                {presets.map((preset, index) => (
                  <RunePresetCard
                    key={index}
                    preset={preset}
                    isActive={activePresetIndex === index}
                    onApply={() => handleApplyPreset(index)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer with status */}
        {applying && (
          <div className="applying-overlay">
            <div className="applying-spinner" />
            <p>Applying preset...</p>
          </div>
        )}
      </div>
    </div>
  );
}
