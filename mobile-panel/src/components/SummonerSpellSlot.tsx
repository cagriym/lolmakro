// SummonerSpellSlot component - Displays a summoner spell slot

import { useState } from "react";
import "./SummonerSpellSlot.css";

interface SummonerSpellSlotProps {
  spellId: number;
  spellName?: string;
  size?: "small" | "medium" | "large";
}

// Summoner spell metadata (common spells)
const SUMMONER_SPELLS: Record<number, { name: string; icon: string }> = {
  1: { name: "Cleanse", icon: "SummonerBoost.png" },
  3: { name: "Exhaust", icon: "SummonerExhaust.png" },
  4: { name: "Flash", icon: "SummonerFlash.png" },
  6: { name: "Ghost", icon: "SummonerHaste.png" },
  7: { name: "Heal", icon: "SummonerHeal.png" },
  11: { name: "Smite", icon: "SummonerSmite.png" },
  12: { name: "Teleport", icon: "SummonerTeleport.png" },
  13: { name: "Clarity", icon: "SummonerMana.png" },
  14: { name: "Ignite", icon: "SummonerDot.png" },
  21: { name: "Barrier", icon: "SummonerBarrier.png" },
  32: { name: "Mark", icon: "SummonerSnowball.png" },
};

// Data Dragon CDN base URL
const DDRAGON_VERSION = "14.1.1"; // TODO: Make this dynamic
const DDRAGON_BASE = `https://ddragon.leagueoflegends.com/cdn/${DDRAGON_VERSION}/img`;

/**
 * Get summoner spell icon URL from Data Dragon
 */
function getSpellIconUrl(spellId: number): string {
  const spell = SUMMONER_SPELLS[spellId];
  if (!spell) return "";
  return `${DDRAGON_BASE}/spell/${spell.icon}`;
}

/**
 * Get summoner spell name
 */
function getSpellName(spellId: number, fallbackName?: string): string {
  const spell = SUMMONER_SPELLS[spellId];
  if (spell) return spell.name;
  if (fallbackName) return fallbackName;
  return `Spell ${spellId}`;
}

export function SummonerSpellSlot({
  spellId,
  spellName,
  size = "medium",
}: SummonerSpellSlotProps) {
  const [imageError, setImageError] = useState(false);

  const displayName = getSpellName(spellId, spellName);
  const iconUrl = getSpellIconUrl(spellId);

  return (
    <div className={`summoner-spell-slot ${size}`}>
      <div className="spell-icon-container">
        {iconUrl && !imageError ? (
          <img
            src={iconUrl}
            alt={displayName}
            className="spell-icon"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="spell-icon-placeholder">
            <span className="spell-placeholder-text">?</span>
          </div>
        )}
      </div>
      <span className="spell-name">{displayName}</span>
    </div>
  );
}
