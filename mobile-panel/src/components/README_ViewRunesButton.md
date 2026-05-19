# ViewRunesButton Component

## Overview

The `ViewRunesButton` component is the entry point for the rune selection interface. It appears as a fixed button at the bottom of the screen when the user is in champion select and has selected a champion.

## Features

- **Conditional Display**: Only shows when all conditions are met:
  - Connected to LCU (`state.connected === true`)
  - In ChampSelect phase (`state.phase === "ChampSelect"`)
  - Champion is selected (`state.mySelection?.championId > 0`)

- **League of Legends Aesthetic**: 
  - Dark background with gold accents (#c89b3c)
  - Gradient background (#1e2328 to #0a1428)
  - Hover effects with glow
  - Smooth animations

- **Touch Optimized**:
  - Minimum 56px height (60px on touch devices)
  - Large touch targets
  - Responsive design for mobile screens

- **Accessibility**:
  - ARIA label for screen readers
  - Reduced motion support
  - High contrast colors

## Usage

```tsx
import { ViewRunesButton } from "@components/ViewRunesButton";

function App() {
  const [showRuneSelection, setShowRuneSelection] = useState(false);

  const handleViewRunesClick = () => {
    setShowRuneSelection((prev) => !prev);
  };

  return (
    <div>
      {/* Your app content */}
      <ViewRunesButton onClick={handleViewRunesClick} />
    </div>
  );
}
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `onClick` | `() => void` | Yes | Callback function when button is clicked |

## State Dependencies

The component reads from the Zustand store:
- `connected`: LCU connection status
- `phase`: Current gameflow phase
- `mySelection`: Current champion and spell selection

## Styling

The component uses a separate CSS file (`ViewRunesButton.css`) with:
- Fixed positioning at bottom of screen
- Gradient background overlay
- League of Legends color scheme
- Smooth animations and transitions
- Responsive breakpoints

## Animation

- **Slide Up**: Button slides up from bottom when appearing
- **Pulse**: Icon pulses subtly to draw attention
- **Hover**: Button lifts and glows on hover
- **Active**: Button presses down on click

## Requirements Satisfied

- **9.1**: Display button at bottom of screen when champion is selected
- **9.2**: Add League of Legends-style button design
- **12.3**: Touch-optimized controls
- **12.4**: Show/hide based on champion select state

## Future Enhancements

- Add champion icon to button
- Show rune preset count badge
- Add loading state during preset fetch
- Implement haptic feedback on mobile
