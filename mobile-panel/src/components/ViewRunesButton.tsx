// ViewRunesButton component - Entry point for rune selection interface

import { useAppStore } from "@/store/useAppStore";
import "./ViewRunesButton.css";

interface ViewRunesButtonProps {
  onClick: () => void;
}

export function ViewRunesButton({ onClick }: ViewRunesButtonProps) {
  const connected = useAppStore((state) => state.connected);
  const phase = useAppStore((state) => state.phase);
  const mySelection = useAppStore((state) => state.mySelection);

  // Only show button when:
  // 1. Connected to LCU
  // 2. In ChampSelect phase
  // 3. Champion is selected (championId > 0)
  const shouldShow =
    connected &&
    phase === "ChampSelect" &&
    mySelection !== null &&
    mySelection.championId > 0;

  if (!shouldShow) {
    return null;
  }

  return (
    <div className="view-runes-button-container">
      <button
        className="view-runes-button"
        onClick={onClick}
        aria-label="View Runes"
      >
        <span className="view-runes-icon">⚡</span>
        <span className="view-runes-text">View Runes</span>
      </button>
    </div>
  );
}
