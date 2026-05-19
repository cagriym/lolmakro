# Mobile Panel Project Structure

## Directory Overview

```
mobile-panel/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── StatusIndicator.tsx
│   │   ├── ProgressStepper.tsx
│   │   └── LogViewer.tsx
│   │
│   ├── pages/              # Main view components
│   │   ├── HomePage.tsx
│   │   └── LiveStatsPage.tsx
│   │
│   ├── hooks/              # Custom React hooks
│   │   ├── useWebSocket.ts
│   │   └── useLogger.ts
│   │
│   ├── services/           # API and WebSocket services
│   │   ├── api.ts
│   │   └── websocket.ts
│   │
│   ├── store/              # Zustand state management
│   │   └── useAppStore.ts
│   │
│   ├── utils/              # Utility functions
│   │   ├── formatters.ts
│   │   ├── gameflow.ts
│   │   └── storage.ts
│   │
│   ├── types/              # TypeScript type definitions
│   │   └── index.ts
│   │
│   ├── App.jsx             # Legacy main component (to be migrated)
│   ├── main.jsx            # Legacy entry point (to be migrated)
│   ├── styles.css          # Global styles
│   └── vite-env.d.ts       # Vite environment type definitions
│
├── public/                 # Static assets (empty for now)
├── dist/                   # Build output (generated)
├── node_modules/           # Dependencies (generated)
│
├── .eslintrc.cjs          # ESLint configuration
├── .gitignore             # Git ignore rules
├── .env.example           # Environment variables template
├── index.html             # HTML template
├── package.json           # Dependencies and scripts
├── tsconfig.json          # TypeScript configuration
├── tsconfig.node.json     # TypeScript config for Node files
├── vite.config.ts         # Vite configuration
├── README.md              # Project documentation
└── STRUCTURE.md           # This file
```

## Component Descriptions

### Components (`src/components/`)
- **StatusIndicator.tsx** - Displays connection status pills (LCU, WebSocket, Phase)
- **ProgressStepper.tsx** - Shows draft flow progress (Ready → Ban → Pick → Setup)
- **LogViewer.tsx** - Displays action logs with timestamps
- **ConnectionStatus.tsx** - Real-time connection status indicator with visual feedback

### Pages (`src/pages/`)
- **HomePage.tsx** - Main draft assistant interface (placeholder)
- **LiveStatsPage.tsx** - Real-time game statistics dashboard (placeholder)

### Hooks (`src/hooks/`)
- **useWebSocket.ts** - Manages WebSocket connection and real-time state updates
- **useLogger.ts** - Manages action logs with timestamps and max entries

### Services (`src/services/`)
- **api.ts** - REST API client for backend communication
- **websocket.ts** - WebSocket service class for real-time updates with exponential backoff reconnection
- **README_websocket.md** - Documentation for WebSocket service usage and integration

### Store (`src/store/`)
- **useAppStore.ts** - Zustand store for global application state

### Utils (`src/utils/`)
- **formatters.ts** - Data formatting (KDA, gold, time, spell names)
- **gameflow.ts** - Gameflow state management utilities
- **storage.ts** - Local storage helpers

### Types (`src/types/`)
- **index.ts** - TypeScript type definitions for the entire application

## Path Aliases

The project uses TypeScript path aliases for cleaner imports:

```typescript
import { api } from "@services/api";
import { useWebSocket } from "@hooks/useWebSocket";
import type { AppState } from "@/types";
import { StatusIndicator } from "@components/StatusIndicator";
```

Configured in:
- `tsconfig.json` - TypeScript path resolution
- `vite.config.ts` - Vite build-time resolution

## State Management

The application uses Zustand for state management. The main store (`useAppStore`) contains:

- **Connection state**: `connected`, `phase`, `champSelect`
- **Static data**: `champions`, `spells`, `runeStyles`, `runePages`
- **UI state**: `isBusy`
- **Actions**: `setState`, `setChampions`, `setSpells`, etc.

## API Integration

### REST API (`src/services/api.ts`)
- Champion select actions (ban, hover, lock)
- Rune and spell management
- Data fetching (champions, spells, runes)
- Live game stats

### WebSocket (`src/services/websocket.ts`)
- Real-time state synchronization
- Automatic reconnection
- Event-based updates

## Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm run type-check   # Run TypeScript type checking
npm run lint         # Run ESLint
```

## Next Steps

1. **Migrate legacy code**: Move functionality from `App.jsx` to TypeScript components
2. **Implement routing**: Add React Router for navigation between pages
3. **Build UI components**: Create rune selection, champion picker, spell selector
4. **Live stats**: Implement real-time statistics dashboard
5. **Mobile optimization**: Add touch gestures and responsive design improvements
6. **Testing**: Add unit tests and integration tests

## Configuration Files

- **tsconfig.json** - TypeScript compiler options, path aliases, strict mode
- **vite.config.ts** - Vite build configuration, dev server, path aliases
- **.eslintrc.cjs** - ESLint rules for code quality
- **package.json** - Dependencies, scripts, project metadata
