# Configuration management for LCU endpoints and polling intervals

import os
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class LCUEndpoints:
    """LCU API endpoint constants"""
    
    # Gameflow endpoints
    GAMEFLOW_PHASE: Final[str] = "/lol-gameflow/v1/gameflow-phase"
    GAMEFLOW_SESSION: Final[str] = "/lol-gameflow/v1/session"
    
    # Champion select endpoints
    CHAMP_SELECT_SESSION: Final[str] = "/lol-champ-select/v1/session"
    CHAMP_SELECT_ACTION: Final[str] = "/lol-champ-select/v1/session/actions/{action_id}"
    CHAMP_SELECT_MY_SELECTION: Final[str] = "/lol-champ-select/v1/session/my-selection"
    
    # Rune pages endpoints
    PERKS_PAGES: Final[str] = "/lol-perks/v1/pages"
    PERKS_PAGE_BY_ID: Final[str] = "/lol-perks/v1/pages/{page_id}"
    PERKS_CURRENT_PAGE: Final[str] = "/lol-perks/v1/currentpage"
    PERKS_STYLES: Final[str] = "/lol-perks/v1/styles"
    
    # Champion and spell data
    OWNED_CHAMPIONS: Final[str] = "/lol-champions/v1/owned-champions-minimal"
    SUMMONER_SPELLS: Final[str] = "/lol-game-data/assets/v1/summoner-spells.json"
    
    # Summoner info
    CURRENT_SUMMONER: Final[str] = "/lol-summoner/v1/current-summoner"
    
    # Ready check
    READY_CHECK_ACCEPT: Final[str] = "/lol-matchmaking/v1/ready-check/accept"


@dataclass(frozen=True)
class PollingConfig:
    """Polling interval configuration"""
    
    # Gameflow phase polling interval (seconds)
    GAMEFLOW_POLL_INTERVAL: Final[float] = 1.0
    
    # Champion select session polling interval (seconds)
    CHAMP_SELECT_POLL_INTERVAL: Final[float] = 0.5
    
    # Live game stats polling interval (seconds)
    LIVE_STATS_POLL_INTERVAL: Final[float] = 5.0
    
    # LCU connection retry interval (seconds)
    CONNECTION_RETRY_INTERVAL: Final[float] = 5.0
    
    # Active window detection interval (seconds)
    ACTIVE_WINDOW_POLL_INTERVAL: Final[float] = 1.0


@dataclass(frozen=True)
class AppConfig:
    """Application configuration"""
    
    # App slot names
    APP_SLOT_NAMES: Final[tuple[str, str, str]] = ("App Slot 1", "App Slot 2", "App Slot 3")
    
    # Maximum rune pages allowed by LCU
    MAX_RUNE_PAGES: Final[int] = 25
    
    # Rune page name max length
    MAX_PAGE_NAME_LENGTH: Final[int] = 50
    
    # Valid rune style IDs
    VALID_STYLE_IDS: Final[tuple[int, ...]] = (8000, 8100, 8200, 8300, 8400)
    
    # Required perks count
    REQUIRED_PERKS_COUNT: Final[int] = 6
    
    # Required stat shards count
    REQUIRED_STAT_SHARDS_COUNT: Final[int] = 3
    
    # Data Dragon CDN base URL
    DATA_DRAGON_BASE_URL: Final[str] = "https://ddragon.leagueoflegends.com/cdn"
    
    # Asset cache directory
    ASSET_CACHE_DIR: Final[str] = os.path.join(os.path.dirname(__file__), "..", "asset_cache")
    
    # External preset provider URL (optional)
    EXTERNAL_PRESET_PROVIDER_URL: Final[str | None] = os.environ.get("BUILD_PROVIDER_URL")


# Global configuration instances
ENDPOINTS = LCUEndpoints()
POLLING = PollingConfig()
CONFIG = AppConfig()
