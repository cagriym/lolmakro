// Type definitions for the LoL Rune Page Manager mobile interface

export type GameflowPhase = 
  | "None" 
  | "Lobby" 
  | "ReadyCheck"
  | "ChampSelect" 
  | "InProgress" 
  | "EndOfGame";

export interface ChampSelectSession {
  localPlayerCellId: number;
  myTeam: Array<{
    cellId: number;
    championId: number;
    assignedPosition: string;
  }>;
  timer: {
    phase: string;
  };
  actions: Array<Array<{
    actorCellId: number;
    championId: number;
    type: string;
    completed?: boolean;
  }>>;
}

export interface RunePage {
  id?: number;
  name: string;
  primaryStyleId: number;
  subStyleId: number;
  selectedPerkIds: number[];
  current?: boolean;
  isActive?: boolean;
  isDeletable?: boolean;
  isEditable?: boolean;
  isValid?: boolean;
  order?: number;
}

export interface Rune {
  id: number;
  name: string;
  shortDesc: string;
  longDesc?: string;
  icon: string;
}

export interface RuneSlot {
  perks: Rune[];
}

export interface RuneStyle {
  id: number;
  key: string;
  name: string;
  icon: string;
  slots: RuneSlot[];
  allowedSubStyles?: number[];
}

export interface Champion {
  id: number;
  name: string;
  key: string;
  title?: string;
}

export interface SummonerSpell {
  id: number;
  name: string;
  description: string;
  icon?: string;
  cooldown?: number;
  modes?: string[];
}

export interface StatShard {
  id: number;
  row: 0 | 1 | 2; // Offense, Flex, Defense
  icon: string;
  description: string;
}

export interface EditorState {
  // Tree selection
  primaryTreeId: number | null;
  secondaryTreeId: number | null;
  
  // Rune selection
  keystoneId: number | null;
  primaryRunes: [number | null, number | null, number | null]; // rows 2-4
  secondaryRunes: [number | null, number | null]; // any 2 from rows 2-4
  
  // Stat shards
  statShards: [number | null, number | null, number | null]; // offense, flex, defense
  
  // Summoner spells
  spell1Id: number;
  spell2Id: number;
  
  // UI state
  loading: boolean;
  applying: boolean;
  error: string | null;
  showSpellPicker: 1 | 2 | null; // which slot is being edited
  showRuneDetails: number | null; // which rune to show details for
  
  // Data
  runeStyles: RuneStyle[];
  availableSpells: SummonerSpell[];
}

export interface EditorValidation {
  isValid: boolean;
  missingSelections: string[]; // e.g., ["Keystone", "Primary Rune Row 2"]
  errors: string[]; // e.g., ["Primary and secondary trees must be different"]
}

export interface AppState {
  connected: boolean;
  phase: GameflowPhase;
  champSelect: ChampSelectSession | null;
  mySelection: {
    championId: number;
    spell1Id: number;
    spell2Id: number;
  } | null;
  currentRunePage: RunePage | null;
  isLolWindowActive?: boolean;
}

export interface LiveGameStats {
  gameId: number;
  gameMode: string;
  gameTime: number;
  participants: Array<{
    summonerName: string;
    championId: number;
    team: number;
    kills: number;
    deaths: number;
    assists: number;
    cs: number;
    gold: number;
    level: number;
  }>;
}

export interface PresetOption {
  slotLabel: string;
  name: string;
  primaryStyleId: number | null;
  subStyleId: number | null;
  selectedPerkIds: (number | null)[];
  spells: {
    spell1Id: number;
    spell2Id: number;
  };
}
