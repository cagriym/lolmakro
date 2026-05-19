# RuneTreeSelector Component

## Overview

The `RuneTreeSelector` component displays all 5 League of Legends rune trees and handles primary and secondary tree selection with visual highlighting and validation.

## Features

- **Display All 5 Rune Trees**: Shows Precision, Domination, Sorcery, Resolve, and Inspiration with icons and names
- **Primary Tree Selection**: Click to select a tree as the primary rune tree (gold border)
- **Secondary Tree Selection**: Click to select a different tree as secondary (blue border)
- **Visual Highlighting**: Distinct styling for primary (gold) and secondary (blue) selections
- **Validation**: Prevents selecting the same tree for both primary and secondary
- **Touch-Optimized**: Minimum 44x44px touch targets for mobile accessibility
- **Responsive Design**: Adapts layout for different screen sizes (320px-768px)

## Requirements Validated

This component validates the following requirements from the spec:

- **1.1**: Display all five rune trees
- **1.3**: Display each tree with icon and name
- **1.5**: Render icons at minimum 48x48 pixels
- **2.1**: Set tree as primary when tapped
- **2.2**: Visually highlight selected primary tree
- **3.1**: Set tree as secondary when tapped
- **3.2**: Prevent selecting same tree for both primary and secondary
- **3.4**: Visually distinguish secondary from primary selection
- **12.1**: Minimum 44x44px touch targets
- **13.1**: Use same color scheme as existing components
- **13.4**: Maintain dark theme aesthetic

## Props

```typescript
interface RuneTreeSelectorProps {
  runeStyles: RuneStyle[];           // Array of all rune tree data
  primaryTreeId: number | null;      // Currently selected primary tree ID
  secondaryTreeId: number | null;    // Currently selected secondary tree ID
  onSelectPrimary: (treeId: number) => void;   // Callback when primary tree selected
  onSelectSecondary: (treeId: number) => void; // Callback when secondary tree selected
}
```

## Usage Example

```tsx
import { useState } from 'react';
import { RuneTreeSelector } from '@/components/RuneTreeSelector';
import { RuneStyle } from '@/types';

function MyComponent() {
  const [primaryTreeId, setPrimaryTreeId] = useState<number | null>(null);
  const [secondaryTreeId, setSecondaryTreeId] = useState<number | null>(null);
  const [runeStyles, setRuneStyles] = useState<RuneStyle[]>([]);

  // Fetch rune styles from API
  useEffect(() => {
    api.getRuneStyles().then(setRuneStyles);
  }, []);

  const handleSelectPrimary = (treeId: number) => {
    setPrimaryTreeId(treeId);
    // Clear dependent rune selections here
  };

  const handleSelectSecondary = (treeId: number) => {
    setSecondaryTreeId(treeId);
    // Clear dependent rune selections here
  };

  return (
    <RuneTreeSelector
      runeStyles={runeStyles}
      primaryTreeId={primaryTreeId}
      secondaryTreeId={secondaryTreeId}
      onSelectPrimary={handleSelectPrimary}
      onSelectSecondary={handleSelectSecondary}
    />
  );
}
```

## Selection Logic

The component implements the following selection logic:

1. **No Primary Selected**: First click selects primary tree
2. **Primary Selected, No Secondary**: Second click selects secondary tree (if different from primary)
3. **Both Selected**: Clicking a new tree replaces the secondary tree
4. **Clicking Selected Tree**: No action (prevents deselection)
5. **Same Tree Prevention**: Cannot select the same tree for both primary and secondary

## Styling

The component uses CSS classes for styling:

- `.rune-tree-selector`: Main container
- `.rune-tree-item`: Individual tree button
- `.selected-primary`: Applied to primary tree (gold border)
- `.selected-secondary`: Applied to secondary tree (blue border)
- `.tree-icon-wrapper`: Icon container (48x48px)
- `.tree-icon`: Tree icon image (32x32px)
- `.tree-name`: Tree name label

## Accessibility

- **Touch Targets**: All interactive elements are at least 44x44px
- **Visual Feedback**: Hover and active states provide clear feedback
- **ARIA Labels**: Buttons include descriptive aria-labels
- **Touch Action**: `touch-action: manipulation` prevents double-tap zoom
- **Tap Highlight**: Custom tap highlight color for better UX

## Responsive Behavior

- **Desktop (>768px)**: 5-column grid layout
- **Tablet (480-768px)**: 3-column grid layout
- **Mobile (<480px)**: 2-column grid layout

## Color Scheme

Consistent with Blitz.gg dark theme:

- **Background**: `rgba(0, 0, 0, 0.3)`
- **Border**: `rgba(200, 170, 110, 0.2)` (gold)
- **Primary Selection**: `#c8aa6e` (gold)
- **Secondary Selection**: `#6496c8` (blue)
- **Text**: `#a09b8c` (light gray)
- **Hover**: `rgba(200, 170, 110, 0.5)`

## Data Dragon CDN

The component uses Riot's Data Dragon CDN for rune tree icons:

```
https://ddragon.leagueoflegends.com/cdn/14.1.1/img/perk-images/{iconPath}
```

Icon paths are provided in the `RuneStyle.icon` field.

## Files

- `RuneTreeSelector.tsx` - Component implementation
- `RuneTreeSelector.css` - Component styles
- `RuneTreeSelector.example.tsx` - Usage example
- `README_RuneTreeSelector.md` - This documentation

## Integration Notes

This component is designed to be used within the larger `RuneSpellEditor` component as part of the mobile rune and spell editor feature. It handles only tree selection; rune slot selection is handled by separate components.

## Future Enhancements

Potential improvements for future iterations:

- Long-press to show tree description
- Animation transitions for selection changes
- Keyboard navigation support
- Tree compatibility validation (some trees can't be paired)
