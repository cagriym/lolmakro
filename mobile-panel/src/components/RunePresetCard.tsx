// RunePresetCard component - Displays a single rune preset option

import { useState } from "react";
import type { PresetOption } from "@/types";
import "./RunePresetCard.css";

interface RunePresetCardProps {
  preset: PresetOption;
  isActive?: boolean;
  onApply: () => void;
}

// Rune style metadata for display
const RUNE_STYLES: Record<number, { name: string; icon: string }> = {
  8000: { name: "Precision", icon: "7201_Precision.png" },
  8100: { name: "Domination", icon: "7200_Domination.png" },
  8200: { name: "Sorcery", icon: "7202_Sorcery.png" },
  8300: { name: "Inspiration", icon: "7203_Whimsy.png" },
  8400: { name: "Resolve", icon: "7204_Resolve.png" },
};

// Data Dragon CDN base URL
const DDRAGON_VERSION = "14.1.1"; // TODO: Make this dynamic
const DDRAGON_BASE = `https://ddragon.leagueoflegends.com/cdn/${DDRAGON_VERSION}/img`;

/**
 * Get rune icon URL from Data Dragon
 */
function getRuneIconUrl(runeId: number | null): string {
  if (!runeId) return "";
  // For now, return a placeholder - will be enhanced with actual rune metadata
  return `${DDRAGON_BASE}/perk-images/Styles/RunesIcon.png`;
}

/**
 * Get style icon URL from Data Dragon
 */
function getStyleIconUrl(styleId: number | null): string {
  if (!styleId || !RUNE_STYLES[styleId]) return "";
  return `${DDRAGON_BASE}/perk-images/Styles/${RUNE_STYLES[styleId].icon}`;
}

/**
 * Get style name
 */
function getStyleName(styleId: number | null): string {
  if (!styleId || !RUNE_STYLES[styleId]) return "Unknown";
  return RUNE_STYLES[styleId].name;
}

export function RunePresetCard({ preset, isActive = false, onApply }: RunePresetCardProps) {
  const [imageErrors, setImageErrors] = useState<Set<string>>(new Set());

  const handleImageError = (key: string) => {
    setImageErrors((prev) => new Set(prev).add(key));
  };

  const primaryStyle = preset.primaryStyleId;
  const subStyle = preset.subStyleId;
  const perks = preset.selectedPerkIds || [];

  // Split perks: first 4 are primary (keystone + 3 perks), last 2 are secondary
  const keystone = perks[0] || null;
  const primaryPerks = perks.slice(1, 4);
  const secondaryPerks = perks.slice(4, 6);

  return (
    <div className={`rune-preset-card ${isActive ? "active" : ""}`}>
      <div className="preset-header">
        <h3 className="preset-name">{preset.name}</h3>
        {preset.slotLabel && (
          <span className="preset-slot-label">{preset.slotLabel}</span>
        )}
      </div>

      {/* Primary Style Section */}
      <div className="rune-section primary-section">
        <div className="style-header">
          {primaryStyle && !imageErrors.has(`primary-${primaryStyle}`) ? (
            <img
              src={getStyleIconUrl(primaryStyle)}
              alt={getStyleName(primaryStyle)}
              className="style-icon"
              onError={() => handleImageError(`primary-${primaryStyle}`)}
            />
          ) : (
            <div className="style-icon-placeholder" />
          )}
          <span className="style-name">{getStyleName(primaryStyle)}</span>
        </div>

        {/* Keystone Rune */}
        <div className="keystone-container">
          {keystone && !imageErrors.has(`keystone-${keystone}`) ? (
            <img
              src={getRuneIconUrl(keystone)}
              alt="Keystone"
              className="keystone-icon"
              onError={() => handleImageError(`keystone-${keystone}`)}
            />
          ) : (
            <div className="keystone-icon-placeholder" />
          )}
        </div>

        {/* Primary Perks */}
        <div className="perks-row">
          {primaryPerks.map((perkId, index) => (
            <div key={`primary-${index}`} className="perk-container">
              {perkId && !imageErrors.has(`perk-${perkId}`) ? (
                <img
                  src={getRuneIconUrl(perkId)}
                  alt={`Perk ${index + 1}`}
                  className="perk-icon"
                  onError={() => handleImageError(`perk-${perkId}`)}
                />
              ) : (
                <div className="perk-icon-placeholder" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Secondary Style Section */}
      <div className="rune-section secondary-section">
        <div className="style-header">
          {subStyle && !imageErrors.has(`sub-${subStyle}`) ? (
            <img
              src={getStyleIconUrl(subStyle)}
              alt={getStyleName(subStyle)}
              className="style-icon"
              onError={() => handleImageError(`sub-${subStyle}`)}
            />
          ) : (
            <div className="style-icon-placeholder" />
          )}
          <span className="style-name">{getStyleName(subStyle)}</span>
        </div>

        {/* Secondary Perks */}
        <div className="perks-row">
          {secondaryPerks.map((perkId, index) => (
            <div key={`secondary-${index}`} className="perk-container">
              {perkId && !imageErrors.has(`perk-${perkId}`) ? (
                <img
                  src={getRuneIconUrl(perkId)}
                  alt={`Secondary Perk ${index + 1}`}
                  className="perk-icon"
                  onError={() => handleImageError(`perk-${perkId}`)}
                />
              ) : (
                <div className="perk-icon-placeholder" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Stat Shards Section */}
      <div className="stat-shards-section">
        <div className="stat-shards-row">
          {[0, 1, 2].map((index) => (
            <div key={`shard-${index}`} className="stat-shard-container">
              <div className="stat-shard-placeholder" />
            </div>
          ))}
        </div>
      </div>

      {/* Apply Button */}
      <button
        className={`apply-button ${isActive ? "applied" : ""}`}
        onClick={onApply}
        disabled={isActive}
      >
        {isActive ? "Applied" : "Apply"}
      </button>
    </div>
  );
}
