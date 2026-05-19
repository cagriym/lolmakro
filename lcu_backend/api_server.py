"""
API Server for LoL Rune Page Manager

This module provides a FastAPI-based HTTP server with WebSocket support for the mobile interface.
It exposes REST endpoints for querying state and triggering actions, plus WebSocket for real-time updates.

Requirements: 12.1, 13.1
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .state_manager import StateManager, AppState, RuneSlotType

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts state updates to all connected clients."""
    
    def __init__(self):
        self.connections: set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.connections)}")
    
    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self.connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.connections)}")
    
    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        stale: list[WebSocket] = []
        
        for ws in self.connections:
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                stale.append(ws)
        
        # Remove stale connections
        for ws in stale:
            self.disconnect(ws)


# Pydantic models for request validation
class PresetSelectRequest(BaseModel):
    """Request to select a preset by index."""
    preset_index: int = Field(ge=0, le=2, description="Preset index (0-2)")


class RuneEditRequest(BaseModel):
    """Request to edit a rune in the active slot."""
    rune_id: int = Field(gt=0, description="Rune ID to apply")
    slot_type: str = Field(description="Slot type (keystone, primary1-3, secondary1-2, statShard1-3)")


class EditModeRequest(BaseModel):
    """Request to toggle edit mode."""
    enabled: bool = Field(description="Enable or disable edit mode")


class APIServer:
    """
    FastAPI server for the LoL Rune Page Manager.
    
    Provides REST endpoints for mobile interface and WebSocket for real-time updates.
    Integrates with StateManager to coordinate backend operations.
    """
    
    def __init__(self, state_manager: StateManager, host: str = "0.0.0.0", port: int = 8765):
        """
        Initialize the API server.
        
        Args:
            state_manager: StateManager instance to coordinate backend operations
            host: Host address to bind to (default: 0.0.0.0 for local network access)
            port: Port to listen on (default: 8765)
        """
        self.state_manager = state_manager
        self.host = host
        self.port = port
        self.ws_manager = WebSocketManager()
        self.app = self._create_app()
        self._server_task: Optional[asyncio.Task] = None
    
    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Lifespan context manager for startup and shutdown."""
            # Startup: Register state change callback
            logger.info("Starting API server...")
            self.state_manager.on_state_change(self._handle_state_change)
            
            # Initialize state manager if not already initialized
            if not self.state_manager.is_initialized():
                await self.state_manager.initialize()
            
            yield
            
            # Shutdown
            logger.info("Shutting down API server...")
            await self.state_manager.shutdown()
        
        app = FastAPI(
            title="LoL Rune Page Manager API",
            version="1.0.0",
            description="REST API and WebSocket server for mobile rune page management",
            lifespan=lifespan
        )
        
        # Enable CORS for local network access
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins for local network
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes(app)
        
        return app
    
    async def _handle_state_change(self, state: AppState) -> None:
        """
        Handle state changes from StateManager and broadcast to WebSocket clients.
        
        Args:
            state: Updated application state
        """
        try:
            state_dict = self._serialize_state(state)
            await self.ws_manager.broadcast(state_dict)
        except Exception as e:
            logger.error(f"Error broadcasting state change: {e}")
    
    def _serialize_state(self, state: AppState) -> dict[str, Any]:
        """
        Serialize AppState to JSON-compatible dictionary.
        
        Args:
            state: Application state to serialize
            
        Returns:
            Dictionary representation of state
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gameflowPhase": state.gameflow_phase,
            "champSelectContext": {
                "championId": state.champ_select_context.champion_id,
                "queueId": state.champ_select_context.queue_id,
                "role": state.champ_select_context.role,
                "phase": state.champ_select_context.phase,
            } if state.champ_select_context else None,
            "availablePresets": [
                {
                    "name": preset.name,
                    "primaryStyleId": preset.primaryStyleId,
                    "subStyleId": preset.subStyleId,
                    "selectedPerkIds": preset.selectedPerkIds,
                    "statShards": preset.statShards,
                }
                for preset in state.available_presets
            ],
            "selectedPresetIndex": state.selected_preset_index,
            "appSlots": [
                {
                    "slotIndex": slot.slotIndex,
                    "pageId": slot.pageId,
                    "name": slot.name,
                    "isActive": slot.isActive,
                    "currentPage": {
                        "name": slot.currentPage.name,
                        "primaryStyleId": slot.currentPage.primaryStyleId,
                        "subStyleId": slot.currentPage.subStyleId,
                        "selectedPerkIds": slot.currentPage.selectedPerkIds,
                        "statShards": slot.currentPage.statShards,
                    } if slot.currentPage else None,
                }
                for slot in state.app_slots
            ],
            "activeSlotIndex": state.active_slot_index,
            "isEditMode": state.is_edit_mode,
        }
    
    def _register_routes(self, app: FastAPI) -> None:
        """Register all API routes."""
        
        @app.get("/api/health")
        async def health() -> dict[str, Any]:
            """Health check endpoint."""
            return {
                "ok": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "initialized": self.state_manager.is_initialized(),
            }
        
        @app.get("/api/state")
        async def get_state() -> dict[str, Any]:
            """
            Get current application state.
            
            Returns current gameflow phase, champion select context, available presets,
            app slots, and edit mode status.
            """
            state = self.state_manager.get_current_state()
            return self._serialize_state(state)
        
        @app.get("/api/presets")
        async def get_presets() -> list[dict[str, Any]]:
            """
            Get available presets for current champion select context.
            
            Returns list of preset rune pages with full configuration.
            """
            state = self.state_manager.get_current_state()
            return [
                {
                    "name": preset.name,
                    "primaryStyleId": preset.primaryStyleId,
                    "subStyleId": preset.subStyleId,
                    "selectedPerkIds": preset.selectedPerkIds,
                    "statShards": preset.statShards,
                }
                for preset in state.available_presets
            ]
        
        @app.post("/api/preset/select")
        async def select_preset(request: PresetSelectRequest) -> dict[str, Any]:
            """
            Select and apply a preset to an app slot.
            
            Args:
                request: Preset selection request with index
                
            Returns:
                Success message with applied preset details
            """
            try:
                await self.state_manager.select_preset(request.preset_index)
                return {
                    "success": True,
                    "message": f"Preset {request.preset_index} applied successfully",
                }
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"Error selecting preset: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to apply preset: {str(e)}")
        
        @app.patch("/api/rune/edit")
        async def edit_rune(request: RuneEditRequest) -> dict[str, Any]:
            """
            Edit a rune in the active slot.
            
            Args:
                request: Rune edit request with rune ID and slot type
                
            Returns:
                Success message with updated rune details
            """
            try:
                # Convert string slot type to enum
                slot_type = RuneSlotType(request.slot_type)
                await self.state_manager.edit_rune(request.rune_id, slot_type)
                return {
                    "success": True,
                    "message": f"Rune {request.rune_id} applied to {request.slot_type}",
                }
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"Error editing rune: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to edit rune: {str(e)}")
        
        @app.post("/api/edit-mode")
        async def set_edit_mode(request: EditModeRequest) -> dict[str, Any]:
            """
            Toggle edit mode on/off.
            
            Args:
                request: Edit mode request with enabled flag
                
            Returns:
                Success message with new edit mode status
            """
            try:
                await self.state_manager.set_edit_mode(request.enabled)
                return {
                    "success": True,
                    "editMode": request.enabled,
                }
            except Exception as e:
                logger.error(f"Error setting edit mode: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to set edit mode: {str(e)}")
        
        @app.get("/api/pages")
        async def get_all_pages() -> list[dict[str, Any]]:
            """
            Get all rune pages from LCU.
            
            Returns list of all rune pages including user-created and app-managed slots.
            """
            try:
                # Access LCU monitor through state manager
                pages = await self.state_manager.lcu_monitor.get_all_rune_pages()
                return pages if pages else []
            except Exception as e:
                logger.error(f"Error fetching rune pages: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to fetch rune pages: {str(e)}")
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket) -> None:
            """
            WebSocket endpoint for real-time state updates.
            
            Clients connect here to receive automatic state change notifications.
            """
            await self.ws_manager.connect(websocket)
            try:
                # Send initial state
                state = self.state_manager.get_current_state()
                await websocket.send_json(self._serialize_state(state))
                
                # Keep connection alive and handle incoming messages
                while True:
                    # Wait for messages (ping/pong or client requests)
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.ws_manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.ws_manager.disconnect(websocket)
    
    async def start(self) -> None:
        """Start the API server."""
        import uvicorn
        
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        
        logger.info(f"Starting API server on {self.host}:{self.port}")
        await server.serve()
    
    def run(self) -> None:
        """Run the API server (blocking)."""
        import uvicorn
        
        logger.info(f"Running API server on {self.host}:{self.port}")
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )


async def create_server(
    state_manager: StateManager,
    host: str = "0.0.0.0",
    port: int = 8765
) -> APIServer:
    """
    Factory function to create and configure an API server.
    
    Args:
        state_manager: StateManager instance
        host: Host address to bind to
        port: Port to listen on
        
    Returns:
        Configured APIServer instance
    """
    server = APIServer(state_manager, host, port)
    return server
