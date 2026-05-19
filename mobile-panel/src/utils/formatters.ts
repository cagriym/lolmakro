// Utility functions for formatting data

import type { SummonerSpell } from "@/types";

export function formatTime(): string {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

export function spellNameById(spells: SummonerSpell[], id: number | undefined): string {
  if (!id) return "-";
  const spell = spells.find((s) => s.id === Number(id));
  return spell?.name || `Spell #${id}`;
}

export function formatKDA(kills: number, deaths: number, assists: number): string {
  return `${kills}/${deaths}/${assists}`;
}

export function formatGold(gold: number): string {
  if (gold >= 1000) {
    return `${(gold / 1000).toFixed(1)}k`;
  }
  return gold.toString();
}

export function calculateKDAScore(kills: number, deaths: number, assists: number): number {
  if (deaths === 0) {
    return kills + assists;
  }
  return (kills + assists) / deaths;
}

export function formatGameTime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}
