# ViewRunesButton Visual Example

## Button Appearance

```
┌─────────────────────────────────────────────┐
│                                             │
│  [Gradient dark background overlay]         │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │  ⚡  VIEW RUNES                       │ │
│  │  [Dark bg with gold border]           │ │
│  └───────────────────────────────────────┘ │
│                                             │
└─────────────────────────────────────────────┘
```

## Color Scheme

- **Background**: Linear gradient from #1e2328 to #0a1428
- **Border**: 2px solid #c89b3c (League gold)
- **Text**: #f0e6d2 (League cream)
- **Icon**: ⚡ with gold glow effect
- **Shadow**: Multiple layers for depth

## States

### Default
- Dark background with gold border
- Subtle shadow
- Icon pulses gently

### Hover
- Lighter background
- Brighter gold border (#d4af37)
- Lifts up 2px
- Stronger shadow and glow

### Active (Pressed)
- Returns to original position
- Reduced shadow
- Immediate visual feedback

## Responsive Behavior

### Desktop (> 560px)
- Max width: 400px
- Font size: 18px
- Padding: 16px 24px
- Icon size: 24px

### Mobile (≤ 560px)
- Full width with 12px margin
- Font size: 16px
- Padding: 14px 20px
- Icon size: 20px

## Animation Timeline

1. **Entry** (0.3s): Slides up from bottom with fade-in
2. **Idle**: Icon pulses every 2 seconds
3. **Hover**: Lifts and glows (0.2s transition)
4. **Click**: Presses down instantly

## Accessibility Features

- Minimum touch target: 56px height (60px on mobile)
- High contrast text and border
- ARIA label: "View Runes"
- Reduced motion support (disables animations)
- Keyboard accessible (can be focused and activated)

## Integration Example

When integrated into the app:

```
┌─────────────────────────────────────────────┐
│  LoL Rune Page Manager                      │
│  [Connection Status]                        │
├─────────────────────────────────────────────┤
│                                             │
│  Game Status                                │
│  Phase: ChampSelect                         │
│                                             │
│  Champion Select                            │
│  Timer Phase: BAN_PICK                      │
│  Team Size: 5                               │
│                                             │
│  My Selection                               │
│  Champion ID: 157 (Yasuo)                   │
│  Spell 1: 4 (Flash)                         │
│  Spell 2: 14 (Ignite)                       │
│                                             │
│                                             │
│  [Scrollable content area]                  │
│                                             │
│                                             │
├─────────────────────────────────────────────┤
│  [Gradient overlay]                         │
│  ┌───────────────────────────────────────┐ │
│  │  ⚡  VIEW RUNES                       │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

## CSS Classes

- `.view-runes-button-container`: Fixed container with gradient overlay
- `.view-runes-button`: Main button with League styling
- `.view-runes-icon`: Icon with pulse animation
- `.view-runes-text`: Text with shadow

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile browsers (iOS Safari, Chrome Mobile)
- CSS Grid and Flexbox support required
- CSS animations and transitions
