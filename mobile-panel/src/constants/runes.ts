/**
 * Rune and Stat Shard Constants
 * 
 * This file contains constant values for stat shard IDs and rune metadata
 * used throughout the mobile rune editor.
 */

/**
 * Stat Shard IDs organized by row
 */
export const STAT_SHARDS = {
  // Offense row (row 0)
  offense: [
    5008, // +9 Adaptive Force
    5005, // +10% Attack Speed
    5007, // +8 Ability Haste
  ],
  // Flex row (row 1)
  flex: [
    5008, // +9 Adaptive Force
    5002, // +6 Armor
    5003, // +8 Magic Resist
  ],
  // Defense row (row 2)
  defense: [
    5001, // +15-140 Health (based on level)
    5002, // +6 Armor
    5003, // +8 Magic Resist
  ],
} as const;

/**
 * Stat Shard Descriptions
 */
export const STAT_SHARD_DESCRIPTIONS: Record<number, string> = {
  5008: "+9 Adaptive Force",
  5005: "+10% Attack Speed",
  5007: "+8 Ability Haste",
  5002: "+6 Armor",
  5003: "+8 Magic Resist",
  5001: "+15-140 Health (based on level)",
};

/**
 * Rune Tree IDs
 */
export const RUNE_TREE_IDS = {
  PRECISION: 8000,
  DOMINATION: 8100,
  SORCERY: 8200,
  RESOLVE: 8400,
  INSPIRATION: 8300,
} as const;

/**
 * Rune Tree Names
 */
export const RUNE_TREE_NAMES: Record<number, string> = {
  [RUNE_TREE_IDS.PRECISION]: "Precision",
  [RUNE_TREE_IDS.DOMINATION]: "Domination",
  [RUNE_TREE_IDS.SORCERY]: "Sorcery",
  [RUNE_TREE_IDS.RESOLVE]: "Resolve",
  [RUNE_TREE_IDS.INSPIRATION]: "Inspiration",
};

/**
 * Minimum touch target size for mobile accessibility (in pixels)
 */
export const MIN_TOUCH_TARGET_SIZE = 44;

/**
 * Minimum spacing between touch elements (in pixels)
 */
export const MIN_TOUCH_SPACING = 8;

/**
 * Rune icon minimum size (in pixels)
 */
export const MIN_RUNE_ICON_SIZE = 48;

/**
 * Number of runes required for a complete configuration
 */
export const REQUIRED_RUNE_COUNTS = {
  KEYSTONE: 1,
  PRIMARY_RUNES: 3, // rows 2-4
  SECONDARY_RUNES: 2, // any 2 from rows 2-4
  STAT_SHARDS: 3, // offense, flex, defense
} as const;

/**
 * Slot types for rune editing
 */
export const RUNE_SLOT_TYPES = {
  KEYSTONE: "keystone",
  PRIMARY_1: "primary1",
  PRIMARY_2: "primary2",
  PRIMARY_3: "primary3",
  SECONDARY_1: "secondary1",
  SECONDARY_2: "secondary2",
  STAT_SHARD_1: "statShard1",
  STAT_SHARD_2: "statShard2",
  STAT_SHARD_3: "statShard3",
} as const;

/**
 * Default summoner spell IDs
 */
export const DEFAULT_SPELL_IDS = {
  FLASH: 4,
  TELEPORT: 12,
  IGNITE: 14,
  SMITE: 11,
  GHOST: 6,
  HEAL: 7,
  BARRIER: 21,
  EXHAUST: 3,
  CLEANSE: 1,
} as const;
