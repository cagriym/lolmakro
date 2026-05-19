# Context Extractor component
# Extracts champion select context from ChampSelectSession data

from dataclasses import dataclass
from typing import Any

from .lcu_monitor import ChampSelectSession


@dataclass
class ChampSelectContext:
    """Champion select context containing champion, queue, role, and phase information"""
    champion_id: int
    queue_id: int
    role: str
    phase: str


def extract_champ_select_context(session: ChampSelectSession) -> ChampSelectContext | None:
    """
    Extract champion select context from ChampSelectSession.
    
    Args:
        session: ChampSelectSession object containing session data
    
    Returns:
        ChampSelectContext if champion is selected, None otherwise
    
    Preconditions:
        - session is non-null ChampSelectSession object
        - session.local_player_cell_id is valid integer
        - session.my_team is non-empty array
    
    Postconditions:
        - Returns ChampSelectContext if local player has selected champion
        - Returns None if champion not yet selected
        - Returned context has valid champion_id > 0
        - Returned role matches assigned position or defaults to "none"
    """
    if session is None:
        return None
    
    # Step 1: Find local player in team
    local_player = None
    for player in session.my_team:
        if player.get("cellId") == session.local_player_cell_id:
            local_player = player
            break
    
    if local_player is None:
        return None
    
    # Step 2: Check if champion selected
    champion_id = local_player.get("championId", 0)
    if champion_id == 0 or champion_id is None:
        return None
    
    # Step 3: Extract queue ID from session
    queue_id = _infer_queue_id(session)
    
    # Step 4: Get assigned role
    role = local_player.get("assignedPosition", "")
    if not role or role == "":
        role = "none"
    else:
        role = _normalize_role(role)
    
    # Step 5: Get phase from timer
    phase = session.timer.get("phase", "PLANNING")
    
    # Step 6: Construct context
    return ChampSelectContext(
        champion_id=champion_id,
        queue_id=queue_id,
        role=role,
        phase=phase,
    )


def _infer_queue_id(session: ChampSelectSession) -> int:
    """
    Infer queue ID from champion select session.
    
    The queue ID is typically found in the raw session data under various keys.
    Common locations: queueId, gameMode, or derived from other session properties.
    
    Args:
        session: ChampSelectSession object
    
    Returns:
        Queue ID as integer, defaults to 0 if not found
    """
    # Try to get queue ID from raw data
    raw_data = session.raw_data
    
    # Check common locations for queue ID
    if "queueId" in raw_data:
        return raw_data["queueId"]
    
    # Fallback: try to infer from game mode or other fields
    # For now, default to 0 (unknown queue)
    return 0


def _normalize_role(role: str) -> str:
    """
    Normalize role string to standard format.
    
    Converts various role representations to standardized values:
    - "top" -> "top"
    - "jungle" -> "jungle"
    - "middle" / "mid" -> "middle"
    - "bottom" / "bot" / "adc" -> "bottom"
    - "utility" / "support" -> "utility"
    - "" / None -> "none"
    
    Args:
        role: Role string from LCU API
    
    Returns:
        Normalized role string
    """
    if not role:
        return "none"
    
    role_lower = role.lower()
    
    # Map common variations to standard roles
    role_map = {
        "top": "top",
        "jungle": "jungle",
        "middle": "middle",
        "mid": "middle",
        "bottom": "bottom",
        "bot": "bottom",
        "adc": "bottom",
        "utility": "utility",
        "support": "utility",
    }
    
    return role_map.get(role_lower, "none")
