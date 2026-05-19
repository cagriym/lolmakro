/**
 * Example usage of RuneTreeSelector component
 * 
 * This file demonstrates how to use the RuneTreeSelector component
 * in a parent component with state management.
 */

import { useState } from 'react';
import { RuneTreeSelector } from './RuneTreeSelector';
import { RuneStyle } from '@/types';

// Example rune styles data (would typically come from API)
const exampleRuneStyles: RuneStyle[] = [
  {
    id: 8000,
    key: 'Precision',
    name: 'Precision',
    icon: 'Styles/7201_Precision.png',
    slots: [
      {
        perks: [
          { id: 8005, name: 'Press the Attack', shortDesc: 'Attacking an enemy champion 3 times in a row deals bonus adaptive damage', icon: 'Styles/Precision/PressTheAttack/PressTheAttack.png' },
          { id: 8008, name: 'Lethal Tempo', shortDesc: 'Gain attack speed when attacking champions', icon: 'Styles/Precision/LethalTempo/LethalTempoTemp.png' },
        ],
      },
    ],
  },
  {
    id: 8100,
    key: 'Domination',
    name: 'Domination',
    icon: 'Styles/7200_Domination.png',
    slots: [],
  },
  {
    id: 8200,
    key: 'Sorcery',
    name: 'Sorcery',
    icon: 'Styles/7202_Sorcery.png',
    slots: [],
  },
  {
    id: 8400,
    key: 'Resolve',
    name: 'Resolve',
    icon: 'Styles/7204_Resolve.png',
    slots: [],
  },
  {
    id: 8300,
    key: 'Inspiration',
    name: 'Inspiration',
    icon: 'Styles/7203_Whimsy.png',
    slots: [],
  },
];

export function RuneTreeSelectorExample() {
  const [primaryTreeId, setPrimaryTreeId] = useState<number | null>(null);
  const [secondaryTreeId, setSecondaryTreeId] = useState<number | null>(null);

  const handleSelectPrimary = (treeId: number) => {
    console.log('Primary tree selected:', treeId);
    setPrimaryTreeId(treeId);
    
    // Clear secondary if it's the same as the new primary
    if (secondaryTreeId === treeId) {
      setSecondaryTreeId(null);
    }
  };

  const handleSelectSecondary = (treeId: number) => {
    console.log('Secondary tree selected:', treeId);
    
    // Prevent selecting the same tree as primary
    if (treeId === primaryTreeId) {
      console.warn('Cannot select the same tree for both primary and secondary');
      return;
    }
    
    setSecondaryTreeId(treeId);
  };

  return (
    <div style={{ padding: '20px', background: '#0a1428', minHeight: '100vh' }}>
      <h1 style={{ color: '#c8aa6e', marginBottom: '20px' }}>
        RuneTreeSelector Example
      </h1>

      <RuneTreeSelector
        runeStyles={exampleRuneStyles}
        primaryTreeId={primaryTreeId}
        secondaryTreeId={secondaryTreeId}
        onSelectPrimary={handleSelectPrimary}
        onSelectSecondary={handleSelectSecondary}
      />

      <div style={{ marginTop: '20px', color: '#fff' }}>
        <h3 style={{ color: '#c8aa6e' }}>Current Selection:</h3>
        <p>Primary Tree ID: {primaryTreeId || 'None'}</p>
        <p>Secondary Tree ID: {secondaryTreeId || 'None'}</p>
      </div>

      <div style={{ marginTop: '20px', color: '#a09b8c', fontSize: '14px' }}>
        <h4 style={{ color: '#c8aa6e' }}>Instructions:</h4>
        <ul>
          <li>Click any tree to select it as primary (if no primary is selected)</li>
          <li>Click another tree to select it as secondary (if primary is already selected)</li>
          <li>Clicking the same tree again has no effect</li>
          <li>Primary trees have a gold border, secondary trees have a blue border</li>
          <li>All touch targets are at least 44x44px for mobile accessibility</li>
        </ul>
      </div>
    </div>
  );
}
