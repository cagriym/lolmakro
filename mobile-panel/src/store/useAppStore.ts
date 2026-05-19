// Zustand store for global application state

import { create } from "zustand";
import type { 
  AppState, 
  Champion, 
  SummonerSpell, 
  RuneStyle, 
  RunePage 
} from "@/types";
import { ConnectionStatus } from "@services/websocket";

interface AppStore extends AppState {
  // Static data
  champions: Champion[];
  spells: SummonerSpell[];
  runeStyles: RuneStyle[];
  runePages: RunePage[];
  
  // UI state
  isBusy: boolean;
  connectionStatus: ConnectionStatus;
  
  // Actions
  setState: (state: Partial<AppState>) => void;
  setChampions: (champions: Champion[]) => void;
  setSpells: (spells: SummonerSpell[]) => void;
  setRuneStyles: (styles: RuneStyle[]) => void;
  setRunePages: (pages: RunePage[]) => void;
  setBusy: (busy: boolean) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
}

export const useAppStore = create<AppStore>((set) => ({
  // Initial state
  connected: false,
  phase: "None",
  champSelect: null,
  mySelection: null,
  currentRunePage: null,
  
  champions: [],
  spells: [],
  runeStyles: [],
  runePages: [],
  
  isBusy: false,
  connectionStatus: ConnectionStatus.DISCONNECTED,
  
  // Actions
  setState: (state) => set((prev) => ({ ...prev, ...state })),
  setChampions: (champions) => set({ champions }),
  setSpells: (spells) => set({ spells }),
  setRuneStyles: (runeStyles) => set({ runeStyles }),
  setRunePages: (runePages) => set({ runePages }),
  setBusy: (isBusy) => set({ isBusy }),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
}));
