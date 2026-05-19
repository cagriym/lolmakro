# Summoner Spell Manager component
# Fetches, normalizes, and caches summoner spell data from LCU API
# Manages summoner spell selection and updates during champion select

from dataclasses import dataclass
from typing import Any

from .config import ENDPOINTS
from .lcu_connection import LCUConnection
from .lcu_monitor import GameflowPhase


@dataclass
class SummonerSpell:
    """Normalized summoner spell data"""
    id: int
    name: str
    description: str
    icon_path: str


@dataclass
class SummonerSpellSelection:
    """Current summoner spell selection"""
    spell1_id: int
    spell2_id: int


class SummonerSpellManager:
    """Manages summoner spell catalog from LCU API"""
    
    def __init__(self, lcu_connection: LCUConnection) -> None:
        """
        Initialize summoner spell manager.
        
        Args:
            lcu_connection: LCU connection instance for API calls
        """
        self._connection = lcu_connection
        self._spell_catalog: list[SummonerSpell] = []
        self._spell_map: dict[int, SummonerSpell] = {}
    
    async def load_spell_catalog(self) -> list[SummonerSpell]:
        """
        Fetch summoner spell data from LCU API and cache it.
        
        Returns:
            List of SummonerSpell objects sorted alphabetically by name
        
        Raises:
            RuntimeError: If LCU API call fails
        """
        # Fetch spell data from LCU API
        spell_data = await self._connection.get(ENDPOINTS.SUMMONER_SPELLS)
        
        if spell_data is None:
            raise RuntimeError("Failed to fetch summoner spell data from LCU API")
        
        # Normalize spell data
        spells = []
        for spell_id_str, spell_info in spell_data.items():
            try:
                spell = self._normalize_spell_data(spell_id_str, spell_info)
                if spell:
                    spells.append(spell)
            except Exception:
                # Skip invalid spell entries
                continue
        
        # Sort spells alphabetically by name
        spells.sort(key=lambda s: s.name)
        
        # Cache the spell catalog
        self._spell_catalog = spells
        self._spell_map = {spell.id: spell for spell in spells}
        
        return spells
    
    def _normalize_spell_data(self, spell_id_str: str, spell_info: dict[str, Any]) -> SummonerSpell | None:
        """
        Normalize spell data from LCU API format to SummonerSpell.
        
        Args:
            spell_id_str: Spell ID as string
            spell_info: Spell information dictionary from LCU API
        
        Returns:
            SummonerSpell object or None if data is invalid
        """
        try:
            # Extract spell ID
            spell_id = int(spell_id_str)
            
            # Extract spell name
            name = spell_info.get("name", "")
            if not name:
                return None
            
            # Extract description
            description = spell_info.get("description", "")
            
            # Extract icon path
            icon_path = spell_info.get("iconPath", "")
            
            return SummonerSpell(
                id=spell_id,
                name=name,
                description=description,
                icon_path=icon_path,
            )
        except (ValueError, KeyError):
            return None
    
    def get_spell_catalog(self) -> list[SummonerSpell]:
        """
        Get cached summoner spell catalog.
        
        Returns:
            List of SummonerSpell objects sorted alphabetically by name
        """
        return self._spell_catalog.copy()
    
    def get_spell_by_id(self, spell_id: int) -> SummonerSpell | None:
        """
        Get summoner spell by ID from cached catalog.
        
        Args:
            spell_id: Summoner spell ID
        
        Returns:
            SummonerSpell object or None if not found
        """
        return self._spell_map.get(spell_id)
    
    def is_catalog_loaded(self) -> bool:
        """
        Check if spell catalog has been loaded.
        
        Returns:
            True if catalog is loaded, False otherwise
        """
        return len(self._spell_catalog) > 0
    
    async def get_current_spell_selection(self) -> SummonerSpellSelection | None:
        """
        Fetch current summoner spell selection from champion select session.
        
        Returns:
            SummonerSpellSelection with current spell IDs, or None if not in champion select
        
        Raises:
            RuntimeError: If LCU API call fails
        """
        # Fetch champion select session
        session_data = await self._connection.get(ENDPOINTS.CHAMP_SELECT_SESSION)
        
        if session_data is None:
            return None
        
        # Extract local player cell ID
        local_cell_id = session_data.get("localPlayerCellId", -1)
        if local_cell_id < 0:
            return None
        
        # Find local player in myTeam
        my_team = session_data.get("myTeam", [])
        local_player = None
        for player in my_team:
            if player.get("cellId") == local_cell_id:
                local_player = player
                break
        
        if local_player is None:
            return None
        
        # Extract summoner spell IDs
        spell1_id = local_player.get("spell1Id", 0)
        spell2_id = local_player.get("spell2Id", 0)
        
        return SummonerSpellSelection(
            spell1_id=spell1_id,
            spell2_id=spell2_id,
        )
    
    async def update_summoner_spells(
        self,
        spell1_id: int | None = None,
        spell2_id: int | None = None,
        current_phase: GameflowPhase | None = None,
    ) -> None:
        """
        Update summoner spell selection in champion select session.
        
        Args:
            spell1_id: New spell ID for slot 1 (None to keep current)
            spell2_id: New spell ID for slot 2 (None to keep current)
            current_phase: Current gameflow phase for validation
        
        Raises:
            ValueError: If not in ChampSelect phase
            RuntimeError: If LCU API call fails
        """
        # Validate phase
        if current_phase != GameflowPhase.CHAMP_SELECT:
            raise ValueError("Summoner spell changes only allowed during ChampSelect phase")
        
        # Build update payload
        update_data: dict[str, Any] = {}
        
        if spell1_id is not None:
            update_data["spell1Id"] = spell1_id
        
        if spell2_id is not None:
            update_data["spell2Id"] = spell2_id
        
        # If no updates specified, return early
        if not update_data:
            return
        
        # Send PATCH request to update session
        result = await self._connection.patch(
            ENDPOINTS.CHAMP_SELECT_MY_SELECTION,
            update_data,
        )
        
        if result is None:
            raise RuntimeError("Failed to update summoner spells via LCU API")
