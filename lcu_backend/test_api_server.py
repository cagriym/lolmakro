"""
Tests for API Server

Tests the FastAPI server endpoints and WebSocket functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from lcu_backend.api_server import APIServer
from lcu_backend.state_manager import StateManager, AppState, RuneSlotType, ChampSelectContext
from lcu_backend.preset_provider import RunePage
from lcu_backend.rune_page_controller import AppSlot


@pytest.fixture
def mock_state_manager():
    """Create a mock StateManager for testing."""
    manager = MagicMock(spec=StateManager)
    manager.is_initialized.return_value = True
    
    # Create a sample state
    sample_state = AppState(
        gameflow_phase="ChampSelect",
        champ_select_context=ChampSelectContext(
            champion_id=157,
            queue_id=420,
            role="middle",
            phase="BAN_PICK"
        ),
        available_presets=[
            RunePage(
                name="Test Preset",
                primaryStyleId=8000,
                subStyleId=8100,
                selectedPerkIds=[8005, 9111, 9104, 8014, 8139, 8135],
                statShards=[5008, 5008, 5002]
            )
        ],
        selected_preset_index=None,
        app_slots=[
            AppSlot(
                slotIndex=0,
                pageId=12345,
                name="App Slot 1",
                currentPage=None,
                isActive=False
            )
        ],
        active_slot_index=None,
        is_edit_mode=False
    )
    
    manager.get_current_state.return_value = sample_state
    manager.select_preset = AsyncMock()
    manager.edit_rune = AsyncMock()
    manager.set_edit_mode = AsyncMock()
    manager.initialize = AsyncMock()
    manager.shutdown = AsyncMock()
    manager.on_state_change = MagicMock()
    
    # Mock LCU monitor
    manager.lcu_monitor = MagicMock()
    manager.lcu_monitor.get_all_rune_pages = AsyncMock(return_value=[])
    
    return manager


@pytest.fixture
def api_server(mock_state_manager):
    """Create an APIServer instance for testing."""
    server = APIServer(mock_state_manager, host="127.0.0.1", port=8765)
    return server


@pytest.fixture
def client(api_server):
    """Create a TestClient for the API server."""
    return TestClient(api_server.app)


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] is True
    assert "timestamp" in data
    assert data["initialized"] is True


def test_get_state_endpoint(client, mock_state_manager):
    """Test the get state endpoint."""
    response = client.get("/api/state")
    assert response.status_code == 200
    
    data = response.json()
    assert data["gameflowPhase"] == "ChampSelect"
    assert data["champSelectContext"]["championId"] == 157
    assert len(data["availablePresets"]) == 1
    assert data["availablePresets"][0]["name"] == "Test Preset"


def test_get_presets_endpoint(client):
    """Test the get presets endpoint."""
    response = client.get("/api/presets")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Preset"
    assert data[0]["primaryStyleId"] == 8000


def test_select_preset_success(client, mock_state_manager):
    """Test successful preset selection."""
    response = client.post(
        "/api/preset/select",
        json={"preset_index": 0}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "applied successfully" in data["message"]
    
    # Verify state manager was called
    mock_state_manager.select_preset.assert_called_once_with(0)


def test_select_preset_invalid_index(client, mock_state_manager):
    """Test preset selection with invalid index."""
    mock_state_manager.select_preset.side_effect = ValueError("Invalid preset index")
    
    response = client.post(
        "/api/preset/select",
        json={"preset_index": 5}
    )
    # FastAPI returns 422 for validation errors on out-of-range values
    assert response.status_code == 422


def test_edit_rune_success(client, mock_state_manager):
    """Test successful rune editing."""
    response = client.patch(
        "/api/rune/edit",
        json={"rune_id": 8128, "slot_type": "keystone"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "8128" in data["message"]
    
    # Verify state manager was called
    mock_state_manager.edit_rune.assert_called_once_with(8128, RuneSlotType.KEYSTONE)


def test_edit_rune_invalid_slot_type(client):
    """Test rune editing with invalid slot type."""
    response = client.patch(
        "/api/rune/edit",
        json={"rune_id": 8128, "slot_type": "invalid_slot"}
    )
    assert response.status_code == 400


def test_set_edit_mode(client, mock_state_manager):
    """Test setting edit mode."""
    response = client.post(
        "/api/edit-mode",
        json={"enabled": True}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["editMode"] is True
    
    # Verify state manager was called
    mock_state_manager.set_edit_mode.assert_called_once_with(True)


def test_get_all_pages(client, mock_state_manager):
    """Test getting all rune pages."""
    mock_pages = [
        {
            "id": 12345,
            "name": "Test Page",
            "current": True,
            "primaryStyleId": 8000,
            "subStyleId": 8100,
        }
    ]
    mock_state_manager.lcu_monitor.get_all_rune_pages.return_value = mock_pages
    
    response = client.get("/api/pages")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Page"


def test_websocket_connection(client, mock_state_manager):
    """Test WebSocket connection and initial state."""
    with client.websocket_connect("/ws") as websocket:
        # Should receive initial state
        data = websocket.receive_json()
        assert data["gameflowPhase"] == "ChampSelect"
        assert data["champSelectContext"]["championId"] == 157


def test_serialize_state(api_server, mock_state_manager):
    """Test state serialization."""
    state = mock_state_manager.get_current_state()
    serialized = api_server._serialize_state(state)
    
    assert serialized["gameflowPhase"] == "ChampSelect"
    assert serialized["champSelectContext"]["championId"] == 157
    assert len(serialized["availablePresets"]) == 1
    assert len(serialized["appSlots"]) == 1


def test_websocket_manager_broadcast():
    """Test WebSocket manager broadcast functionality."""
    from lcu_backend.api_server import WebSocketManager
    
    manager = WebSocketManager()
    assert len(manager.connections) == 0
    
    # Test connection tracking
    mock_ws = MagicMock()
    manager.connections.add(mock_ws)
    assert len(manager.connections) == 1
    
    manager.disconnect(mock_ws)
    assert len(manager.connections) == 0


@pytest.mark.asyncio
async def test_handle_state_change(api_server, mock_state_manager):
    """Test state change handling and broadcasting."""
    state = mock_state_manager.get_current_state()
    
    # Mock WebSocket manager
    api_server.ws_manager.broadcast = AsyncMock()
    
    # Trigger state change
    await api_server._handle_state_change(state)
    
    # Verify broadcast was called
    api_server.ws_manager.broadcast.assert_called_once()
    call_args = api_server.ws_manager.broadcast.call_args[0][0]
    assert call_args["gameflowPhase"] == "ChampSelect"


def test_cors_enabled(client):
    """Test that CORS is enabled for all origins."""
    response = client.get("/api/health", headers={"Origin": "http://example.com"})
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_request_validation():
    """Test request validation with Pydantic models."""
    from lcu_backend.api_server import PresetSelectRequest, RuneEditRequest, EditModeRequest
    
    # Valid preset select request
    request = PresetSelectRequest(preset_index=0)
    assert request.preset_index == 0
    
    # Invalid preset index (negative)
    with pytest.raises(Exception):
        PresetSelectRequest(preset_index=-1)
    
    # Invalid preset index (too large)
    with pytest.raises(Exception):
        PresetSelectRequest(preset_index=3)
    
    # Valid rune edit request
    request = RuneEditRequest(rune_id=8128, slot_type="keystone")
    assert request.rune_id == 8128
    assert request.slot_type == "keystone"
    
    # Invalid rune ID (zero)
    with pytest.raises(Exception):
        RuneEditRequest(rune_id=0, slot_type="keystone")
    
    # Valid edit mode request
    request = EditModeRequest(enabled=True)
    assert request.enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
