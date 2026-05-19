# Unit tests for context_extractor module

import pytest
from .context_extractor import (
    ChampSelectContext,
    extract_champ_select_context,
    _normalize_role,
    _infer_queue_id,
)
from .lcu_monitor import ChampSelectSession


def test_extract_context_with_valid_session():
    """Test extracting context from a valid champion select session"""
    session = ChampSelectSession(
        local_player_cell_id=1,
        my_team=[
            {"cellId": 0, "championId": 100, "assignedPosition": "top"},
            {"cellId": 1, "championId": 64, "assignedPosition": "jungle"},
            {"cellId": 2, "championId": 103, "assignedPosition": "middle"},
        ],
        timer={"phase": "BAN_PICK"},
        actions=[],
        raw_data={"queueId": 420},
    )
    
    context = extract_champ_select_context(session)
    
    assert context is not None
    assert context.champion_id == 64
    assert context.queue_id == 420
    assert context.role == "jungle"
    assert context.phase == "BAN_PICK"


def test_extract_context_champion_not_selected():
    """Test that None is returned when champion is not selected (championId = 0)"""
    session = ChampSelectSession(
        local_player_cell_id=1,
        my_team=[
            {"cellId": 1, "championId": 0, "assignedPosition": "jungle"},
        ],
        timer={"phase": "PLANNING"},
        actions=[],
        raw_data={"queueId": 420},
    )
    
    context = extract_champ_select_context(session)
    
    assert context is None


def test_extract_context_champion_id_none():
    """Test that None is returned when championId is None"""
    session = ChampSelectSession(
        local_player_cell_id=1,
        my_team=[
            {"cellId": 1, "championId": None, "assignedPosition": "jungle"},
        ],
        timer={"phase": "PLANNING"},
        actions=[],
        raw_data={"queueId": 420},
    )
    
    context = extract_champ_select_context(session)
    
    assert context is None


def test_extract_context_local_player_not_found():
    """Test that None is returned when local player is not in team"""
    session = ChampSelectSession(
        local_player_cell_id=5,
        my_team=[
            {"cellId": 1, "championId": 64, "assignedPosition": "jungle"},
            {"cellId": 2, "championId": 103, "assignedPosition": "middle"},
        ],
        timer={"phase": "BAN_PICK"},
        actions=[],
        raw_data={"queueId": 420},
    )
    
    context = extract_champ_select_context(session)
    
    assert context is None


def test_extract_context_empty_role():
    """Test that role defaults to 'none' when assignedPosition is empty"""
    session = ChampSelectSession(
        local_player_cell_id=1,
        my_team=[
            {"cellId": 1, "championId": 64, "assignedPosition": ""},
        ],
        timer={"phase": "BAN_PICK"},
        actions=[],
        raw_data={"queueId": 450},
    )
    
    context = extract_champ_select_context(session)
    
    assert context is not None
    assert context.role == "none"


def test_extract_context_missing_role():
    """Test that role defaults to 'none' when assignedPosition is missing"""
    session = ChampSelectSession(
        local_player_cell_id=1,
        my_team=[
            {"cellId": 1, "championId": 64},
        ],
        timer={"phase": "BAN_PICK"},
        actions=[],
        raw_data={"queueId": 450},
    )
    
    context = extract_champ_select_context(session)
    
    assert context is not None
    assert context.role == "none"


def test_extract_context_none_session():
    """Test that None is returned when session is None"""
    context = extract_champ_select_context(None)
    
    assert context is None


def test_normalize_role_standard_roles():
    """Test role normalization for standard roles"""
    assert _normalize_role("top") == "top"
    assert _normalize_role("jungle") == "jungle"
    assert _normalize_role("middle") == "middle"
    assert _normalize_role("bottom") == "bottom"
    assert _normalize_role("utility") == "utility"


def test_normalize_role_variations():
    """Test role normalization for common variations"""
    assert _normalize_role("mid") == "middle"
    assert _normalize_role("bot") == "bottom"
    assert _normalize_role("adc") == "bottom"
    assert _normalize_role("support") == "utility"


def test_normalize_role_case_insensitive():
    """Test that role normalization is case-insensitive"""
    assert _normalize_role("TOP") == "top"
    assert _normalize_role("Jungle") == "jungle"
    assert _normalize_role("MIDDLE") == "middle"
    assert _normalize_role("BoTtOm") == "bottom"


def test_normalize_role_empty():
    """Test that empty role returns 'none'"""
    assert _normalize_role("") == "none"
    assert _normalize_role(None) == "none"


def test_normalize_role_unknown():
    """Test that unknown role returns 'none'"""
    assert _normalize_role("unknown") == "none"
    assert _normalize_role("invalid") == "none"


def test_infer_queue_id_from_raw_data():
    """Test inferring queue ID from raw session data"""
    session = ChampSelectSession(
        local_player_cell_id=1,
        my_team=[],
        timer={},
        actions=[],
        raw_data={"queueId": 420},
    )
    
    queue_id = _infer_queue_id(session)
    
    assert queue_id == 420


def test_infer_queue_id_missing():
    """Test that queue ID defaults to 0 when not found"""
    session = ChampSelectSession(
        local_player_cell_id=1,
        my_team=[],
        timer={},
        actions=[],
        raw_data={},
    )
    
    queue_id = _infer_queue_id(session)
    
    assert queue_id == 0


def test_extract_context_default_phase():
    """Test that phase defaults to 'PLANNING' when not in timer"""
    session = ChampSelectSession(
        local_player_cell_id=1,
        my_team=[
            {"cellId": 1, "championId": 64, "assignedPosition": "jungle"},
        ],
        timer={},
        actions=[],
        raw_data={"queueId": 420},
    )
    
    context = extract_champ_select_context(session)
    
    assert context is not None
    assert context.phase == "PLANNING"


def test_extract_context_all_roles():
    """Test context extraction with all standard roles"""
    roles = ["top", "jungle", "middle", "bottom", "utility"]
    
    for idx, role in enumerate(roles):
        session = ChampSelectSession(
            local_player_cell_id=idx,
            my_team=[
                {"cellId": idx, "championId": 100 + idx, "assignedPosition": role},
            ],
            timer={"phase": "BAN_PICK"},
            actions=[],
            raw_data={"queueId": 420},
        )
        
        context = extract_champ_select_context(session)
        
        assert context is not None
        assert context.champion_id == 100 + idx
        assert context.role == role


def test_extract_context_multiple_queue_types():
    """Test context extraction with different queue types"""
    queue_ids = [420, 440, 450, 400]  # Ranked Solo, Ranked Flex, ARAM, Draft
    
    for queue_id in queue_ids:
        session = ChampSelectSession(
            local_player_cell_id=1,
            my_team=[
                {"cellId": 1, "championId": 64, "assignedPosition": "jungle"},
            ],
            timer={"phase": "BAN_PICK"},
            actions=[],
            raw_data={"queueId": queue_id},
        )
        
        context = extract_champ_select_context(session)
        
        assert context is not None
        assert context.queue_id == queue_id
