/**
 * RuneTreeSelector Component
 * 
 * Displays all 5 rune trees and handles primary/secondary tree selection.
 * Implements visual highlighting and validation to prevent selecting the same tree twice.
 */

import { RuneStyle } from "@/types";
import "./RuneTreeSelector.css";

// Data Dragon CDN base URL
const DDRAGON_VERSION = "14.1.1";
const DDRAGON_BASE = `https://ddragon.leagueoflegends.com/cdn/${DDRAGON_VERSION}/img`;

interface RuneTreeSelectorProps {
  runeStyles: RuneStyle[];
  primaryTreeId: number | null;
  secondaryTreeId: number | null;
  onSelectPrimary: (treeId: number) => void;
  onSelectSecondary: (treeId: number) => void;
}

export function RuneTreeSelector({
  runeStyles,
  primaryTreeId,
  secondaryTreeId,
  onSelectPrimary,
  onSelectSecondary,
}: RuneTreeSelectorProps) {
  const handleTreeClick = (treeId: number) => {
    // If clicking the current primary tree, do nothing
    if (treeId === primaryTreeId) {
      return;
    }

    // If no primary tree selected, set as primary
    if (primaryTreeId === null) {
      onSelectPrimary(treeId);
      return;
    }

    // If clicking the current secondary tree, do nothing
    if (treeId === secondaryTreeId) {
      return;
    }

    // If no secondary tree selected, set as secondary
    if (secondaryTreeId === null) {
      onSelectSecondary(treeId);
      return;
    }

    // If both are selected, replace the secondary tree
    onSelectSecondary(treeId);
  };

  const getTreeIconUrl = (iconPath: string) => {
    return `${DDRAGON_BASE}/perk-images/${iconPath}`;
  };

  const getTreeClassName = (treeId: number) => {
    const classes = ["rune-tree-item"];
    
    if (treeId === primaryTreeId) {
      classes.push("selected-primary");
    } else if (treeId === secondaryTreeId) {
      classes.push("selected-secondary");
    }
    
    return classes.join(" ");
  };

  return (
    <div className="rune-tree-selector">
      <div className="selector-header">
        <h3>Select Rune Trees</h3>
        <div className="selection-indicators">
          {primaryTreeId && (
            <span className="indicator primary-indicator">Primary Selected</span>
          )}
          {secondaryTreeId && (
            <span className="indicator secondary-indicator">Secondary Selected</span>
          )}
        </div>
      </div>

      <div className="rune-tree-grid">
        {runeStyles.map((style) => (
          <button
            key={style.id}
            className={getTreeClassName(style.id)}
            onClick={() => handleTreeClick(style.id)}
            aria-label={`Select ${style.name} as ${primaryTreeId === null ? 'primary' : 'secondary'} tree`}
          >
            <div className="tree-icon-wrapper">
              <img
                src={getTreeIconUrl(style.icon)}
                alt={style.name}
                className="tree-icon"
              />
            </div>
            <span className="tree-name">{style.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
