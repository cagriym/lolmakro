# Tests for Summoner Spell Manager component

import pytest
from unittest.mock import AsyncMock, MagicMock

from .summoner_spell_manager import SummonerSpell, SummonerSpellManager
from .lcu_connection import LCUConnection


@pytest.fixture
def mock_lcu_connection():
    """Create a mock LCU connection"""
    connection = AsyncMock(spec=LCUConnection)
    return connection


@pytest.fixture
def sample_spell_data():
    """Sample summoner spell data from LCU API"""
    return {
        "4": {
            "id": 4,
            "name": "Flash",
            "description": "Teleports your champion a short distance toward your cursor's location.",
            "iconPath": "/lol-game-data/assets/DATA/Spells/Icons2D/Summoner_Flash.png"
        },
        "14": {
            "id": 14,
            "name": "Ignite",
            "description": "Ignites target enemy champion, dealing damage over time.",
            "iconPath": "/lol-game-data/assets/DATA/Spells/Icons2D/Summoner_Ignite.png"
        },
        "12": {
            "id": 12,
            "name": "Teleport",
            "description": "After channeling for 4 seconds, teleports your champion to target allied structure.",
            "iconPath": "/lol-game-data/assets/DATA/Spells/Icons2D/Summoner_Teleport.png"
        },
        "11": {
            "id": 11,
            "name": "Smite",
            "description": "Deals damage to target monster or enemy minion.",
            "iconPath": "/lol-game-data/assets/DATA/Spells/Icons2D/Summoner_Smite.png"
        }
    }


@pytest.mark.asyncio
async def test_load_spell_catalog_success(mock_lcu_connection, sample_spell_data):
    """Test successful loading of summoner spell catalog"""
    # Arrange
    mock_lcu_connection.get.return_value = sample_spell_data
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    spells = await manager.load_spell_catalog()
    
    # Assert
    assert len(spells) == 4
    assert all(isinstance(spell, SummonerSpell) for spell in spells)
    
    # Verify spells are sorted alphabetically
    spell_names = [spell.name for spell in spells]
    assert spell_names == sorted(spell_names)
    assert spell_names == ["Flash", "Ignite", "Smite", "Teleport"]
    
    # Verify API was called with correct endpoint
    mock_lcu_connection.get.assert_called_once_with("/lol-game-data/assets/v1/summoner-spells.json")


@pytest.mark.asyncio
async def test_load_spell_catalog_normalizes_data(mock_lcu_connection, sample_spell_data):
    """Test that spell data is properly normalized"""
    # Arrange
    mock_lcu_connection.get.return_value = sample_spell_data
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    spells = await manager.load_spell_catalog()
    
    # Assert - Check Flash spell
    flash = next(s for s in spells if s.name == "Flash")
    assert flash.id == 4
    assert flash.name == "Flash"
    assert "Teleports your champion" in flash.description
    assert flash.icon_path == "/lol-game-data/assets/DATA/Spells/Icons2D/Summoner_Flash.png"


@pytest.mark.asyncio
async def test_load_spell_catalog_caches_data(mock_lcu_connection, sample_spell_data):
    """Test that spell catalog is cached after loading"""
    # Arrange
    mock_lcu_connection.get.return_value = sample_spell_data
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    await manager.load_spell_catalog()
    
    # Assert
    assert manager.is_catalog_loaded()
    cached_spells = manager.get_spell_catalog()
    assert len(cached_spells) == 4


@pytest.mark.asyncio
async def test_load_spell_catalog_api_failure(mock_lcu_connection):
    """Test handling of LCU API failure"""
    # Arrange
    mock_lcu_connection.get.return_value = None
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act & Assert
    with pytest.raises(RuntimeError, match="Failed to fetch summoner spell data"):
        await manager.load_spell_catalog()


@pytest.mark.asyncio
async def test_load_spell_catalog_skips_invalid_entries(mock_lcu_connection):
    """Test that invalid spell entries are skipped"""
    # Arrange
    invalid_data = {
        "4": {
            "id": 4,
            "name": "Flash",
            "description": "Valid spell",
            "iconPath": "/path/to/flash.png"
        },
        "invalid": {
            # Missing required fields
            "description": "Invalid spell"
        },
        "14": {
            "id": 14,
            "name": "",  # Empty name
            "description": "Invalid spell",
            "iconPath": "/path/to/icon.png"
        },
        "11": {
            "id": 11,
            "name": "Smite",
            "description": "Valid spell",
            "iconPath": "/path/to/smite.png"
        }
    }
    mock_lcu_connection.get.return_value = invalid_data
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    spells = await manager.load_spell_catalog()
    
    # Assert - Only valid spells should be loaded
    assert len(spells) == 2
    spell_names = [spell.name for spell in spells]
    assert "Flash" in spell_names
    assert "Smite" in spell_names


def test_get_spell_catalog_returns_copy(mock_lcu_connection):
    """Test that get_spell_catalog returns a copy of the catalog"""
    # Arrange
    manager = SummonerSpellManager(mock_lcu_connection)
    manager._spell_catalog = [
        SummonerSpell(4, "Flash", "Description", "/path/to/flash.png")
    ]
    
    # Act
    catalog1 = manager.get_spell_catalog()
    catalog2 = manager.get_spell_catalog()
    
    # Assert - Should be different list objects
    assert catalog1 is not catalog2
    assert catalog1 == catalog2


def test_get_spell_by_id_found(mock_lcu_connection):
    """Test retrieving spell by ID when it exists"""
    # Arrange
    manager = SummonerSpellManager(mock_lcu_connection)
    flash = SummonerSpell(4, "Flash", "Description", "/path/to/flash.png")
    manager._spell_catalog = [flash]
    manager._spell_map = {4: flash}
    
    # Act
    result = manager.get_spell_by_id(4)
    
    # Assert
    assert result is not None
    assert result.id == 4
    assert result.name == "Flash"


def test_get_spell_by_id_not_found(mock_lcu_connection):
    """Test retrieving spell by ID when it doesn't exist"""
    # Arrange
    manager = SummonerSpellManager(mock_lcu_connection)
    manager._spell_catalog = []
    manager._spell_map = {}
    
    # Act
    result = manager.get_spell_by_id(999)
    
    # Assert
    assert result is None


def test_is_catalog_loaded_empty(mock_lcu_connection):
    """Test is_catalog_loaded returns False when catalog is empty"""
    # Arrange
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act & Assert
    assert not manager.is_catalog_loaded()


def test_is_catalog_loaded_with_data(mock_lcu_connection):
    """Test is_catalog_loaded returns True when catalog has data"""
    # Arrange
    manager = SummonerSpellManager(mock_lcu_connection)
    manager._spell_catalog = [
        SummonerSpell(4, "Flash", "Description", "/path/to/flash.png")
    ]
    
    # Act & Assert
    assert manager.is_catalog_loaded()


@pytest.mark.asyncio
async def test_load_spell_catalog_alphabetical_sorting(mock_lcu_connection):
    """Test that spells are sorted alphabetically regardless of input order"""
    # Arrange
    unordered_data = {
        "14": {"id": 14, "name": "Ignite", "description": "Desc", "iconPath": "/path1.png"},
        "4": {"id": 4, "name": "Flash", "description": "Desc", "iconPath": "/path2.png"},
        "12": {"id": 12, "name": "Teleport", "description": "Desc", "iconPath": "/path3.png"},
        "3": {"id": 3, "name": "Exhaust", "description": "Desc", "iconPath": "/path4.png"},
        "21": {"id": 21, "name": "Barrier", "description": "Desc", "iconPath": "/path5.png"},
    }
    mock_lcu_connection.get.return_value = unordered_data
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    spells = await manager.load_spell_catalog()
    
    # Assert
    spell_names = [spell.name for spell in spells]
    assert spell_names == ["Barrier", "Exhaust", "Flash", "Ignite", "Teleport"]


@pytest.mark.asyncio
async def test_normalize_spell_data_missing_optional_fields(mock_lcu_connection):
    """Test normalization handles missing optional fields"""
    # Arrange
    minimal_data = {
        "4": {
            "id": 4,
            "name": "Flash",
            # description and iconPath are optional
        }
    }
    mock_lcu_connection.get.return_value = minimal_data
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    spells = await manager.load_spell_catalog()
    
    # Assert
    assert len(spells) == 1
    flash = spells[0]
    assert flash.id == 4
    assert flash.name == "Flash"
    assert flash.description == ""
    assert flash.icon_path == ""


@pytest.mark.asyncio
async def test_load_spell_catalog_updates_spell_map(mock_lcu_connection, sample_spell_data):
    """Test that loading catalog updates the spell map for quick lookups"""
    # Arrange
    mock_lcu_connection.get.return_value = sample_spell_data
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    await manager.load_spell_catalog()
    
    # Assert
    assert len(manager._spell_map) == 4
    assert 4 in manager._spell_map
    assert 14 in manager._spell_map
    assert 12 in manager._spell_map
    assert 11 in manager._spell_map
    
    # Verify spell map entries
    assert manager._spell_map[4].name == "Flash"
    assert manager._spell_map[14].name == "Ignite"


# Tests for summoner spell selection functionality


@pytest.fixture
def sample_champ_select_session():
    """Sample champion select session data"""
    return {
        "localPlayerCellId": 0,
        "myTeam": [
            {
                "cellId": 0,
                "championId": 157,  # Yasuo
                "spell1Id": 4,      # Flash
                "spell2Id": 14,     # Ignite
                "assignedPosition": "middle"
            },
            {
                "cellId": 1,
                "championId": 64,   # Lee Sin
                "spell1Id": 11,     # Smite
                "spell2Id": 4,      # Flash
                "assignedPosition": "jungle"
            }
        ],
        "timer": {"phase": "BAN_PICK"}
    }


@pytest.mark.asyncio
async def test_get_current_spell_selection_success(mock_lcu_connection, sample_champ_select_session):
    """Test fetching current summoner spell selection"""
    # Arrange
    mock_lcu_connection.get.return_value = sample_champ_select_session
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    selection = await manager.get_current_spell_selection()
    
    # Assert
    assert selection is not None
    assert selection.spell1_id == 4   # Flash
    assert selection.spell2_id == 14  # Ignite
    mock_lcu_connection.get.assert_called_once_with("/lol-champ-select/v1/session")


@pytest.mark.asyncio
async def test_get_current_spell_selection_no_session(mock_lcu_connection):
    """Test fetching spell selection when not in champion select"""
    # Arrange
    mock_lcu_connection.get.return_value = None
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    selection = await manager.get_current_spell_selection()
    
    # Assert
    assert selection is None


@pytest.mark.asyncio
async def test_get_current_spell_selection_invalid_cell_id(mock_lcu_connection):
    """Test fetching spell selection with invalid local player cell ID"""
    # Arrange
    invalid_session = {
        "localPlayerCellId": -1,
        "myTeam": [],
        "timer": {"phase": "BAN_PICK"}
    }
    mock_lcu_connection.get.return_value = invalid_session
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    selection = await manager.get_current_spell_selection()
    
    # Assert
    assert selection is None


@pytest.mark.asyncio
async def test_get_current_spell_selection_player_not_found(mock_lcu_connection):
    """Test fetching spell selection when local player not in team"""
    # Arrange
    session_without_player = {
        "localPlayerCellId": 5,  # Cell ID not in team
        "myTeam": [
            {
                "cellId": 0,
                "championId": 157,
                "spell1Id": 4,
                "spell2Id": 14,
                "assignedPosition": "middle"
            }
        ],
        "timer": {"phase": "BAN_PICK"}
    }
    mock_lcu_connection.get.return_value = session_without_player
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    selection = await manager.get_current_spell_selection()
    
    # Assert
    assert selection is None


@pytest.mark.asyncio
async def test_get_current_spell_selection_default_spells(mock_lcu_connection):
    """Test fetching spell selection with missing spell IDs (defaults to 0)"""
    # Arrange
    session_no_spells = {
        "localPlayerCellId": 0,
        "myTeam": [
            {
                "cellId": 0,
                "championId": 157,
                # spell1Id and spell2Id missing
                "assignedPosition": "middle"
            }
        ],
        "timer": {"phase": "BAN_PICK"}
    }
    mock_lcu_connection.get.return_value = session_no_spells
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    selection = await manager.get_current_spell_selection()
    
    # Assert
    assert selection is not None
    assert selection.spell1_id == 0
    assert selection.spell2_id == 0


@pytest.mark.asyncio
async def test_update_summoner_spells_both_spells(mock_lcu_connection):
    """Test updating both summoner spells"""
    # Arrange
    from .lcu_monitor import GameflowPhase
    mock_lcu_connection.patch.return_value = {"success": True}
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    await manager.update_summoner_spells(
        spell1_id=4,   # Flash
        spell2_id=14,  # Ignite
        current_phase=GameflowPhase.CHAMP_SELECT
    )
    
    # Assert
    mock_lcu_connection.patch.assert_called_once_with(
        "/lol-champ-select/v1/session/my-selection",
        {"spell1Id": 4, "spell2Id": 14}
    )


@pytest.mark.asyncio
async def test_update_summoner_spells_single_spell(mock_lcu_connection):
    """Test updating only one summoner spell"""
    # Arrange
    from .lcu_monitor import GameflowPhase
    mock_lcu_connection.patch.return_value = {"success": True}
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act - Update only spell1
    await manager.update_summoner_spells(
        spell1_id=12,  # Teleport
        spell2_id=None,
        current_phase=GameflowPhase.CHAMP_SELECT
    )
    
    # Assert
    mock_lcu_connection.patch.assert_called_once_with(
        "/lol-champ-select/v1/session/my-selection",
        {"spell1Id": 12}
    )


@pytest.mark.asyncio
async def test_update_summoner_spells_wrong_phase(mock_lcu_connection):
    """Test that spell updates are rejected outside ChampSelect phase"""
    # Arrange
    from .lcu_monitor import GameflowPhase
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act & Assert - Try to update in Lobby phase
    with pytest.raises(ValueError, match="only allowed during ChampSelect phase"):
        await manager.update_summoner_spells(
            spell1_id=4,
            spell2_id=14,
            current_phase=GameflowPhase.LOBBY
        )
    
    # Verify no API call was made
    mock_lcu_connection.patch.assert_not_called()


@pytest.mark.asyncio
async def test_update_summoner_spells_none_phase(mock_lcu_connection):
    """Test that spell updates are rejected when phase is None"""
    # Arrange
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act & Assert
    with pytest.raises(ValueError, match="only allowed during ChampSelect phase"):
        await manager.update_summoner_spells(
            spell1_id=4,
            spell2_id=14,
            current_phase=None
        )
    
    # Verify no API call was made
    mock_lcu_connection.patch.assert_not_called()


@pytest.mark.asyncio
async def test_update_summoner_spells_no_changes(mock_lcu_connection):
    """Test that no API call is made when no spells are specified"""
    # Arrange
    from .lcu_monitor import GameflowPhase
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    await manager.update_summoner_spells(
        spell1_id=None,
        spell2_id=None,
        current_phase=GameflowPhase.CHAMP_SELECT
    )
    
    # Assert - No API call should be made
    mock_lcu_connection.patch.assert_not_called()


@pytest.mark.asyncio
async def test_update_summoner_spells_api_failure(mock_lcu_connection):
    """Test handling of LCU API failure during spell update"""
    # Arrange
    from .lcu_monitor import GameflowPhase
    mock_lcu_connection.patch.return_value = None
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act & Assert
    with pytest.raises(RuntimeError, match="Failed to update summoner spells"):
        await manager.update_summoner_spells(
            spell1_id=4,
            spell2_id=14,
            current_phase=GameflowPhase.CHAMP_SELECT
        )


@pytest.mark.asyncio
async def test_update_summoner_spells_immediate_sync(mock_lcu_connection):
    """Test that spell updates are synchronized immediately to LCU"""
    # Arrange
    from .lcu_monitor import GameflowPhase
    mock_lcu_connection.patch.return_value = {"success": True}
    manager = SummonerSpellManager(mock_lcu_connection)
    
    # Act
    await manager.update_summoner_spells(
        spell1_id=4,
        spell2_id=14,
        current_phase=GameflowPhase.CHAMP_SELECT
    )
    
    # Assert - Verify PATCH was called (immediate synchronization)
    assert mock_lcu_connection.patch.call_count == 1
    call_args = mock_lcu_connection.patch.call_args
    assert call_args[0][0] == "/lol-champ-select/v1/session/my-selection"
    assert call_args[0][1] == {"spell1Id": 4, "spell2Id": 14}
