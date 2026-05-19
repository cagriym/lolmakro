"""
Example: Using the API Server

This example demonstrates how to start the API server with the StateManager
to provide REST and WebSocket endpoints for the mobile interface.

Requirements: 12.1, 13.1
"""

import asyncio
import logging

from lcu_backend.lcu_monitor import LCUMonitor
from lcu_backend.preset_provider import PresetProvider
from lcu_backend.rune_page_controller import RunePageController
from lcu_backend.state_manager import StateManager
from lcu_backend.api_server import APIServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """
    Main function demonstrating API server usage.
    
    This sets up all backend components and starts the API server
    to expose functionality to the mobile interface.
    """
    logger.info("Starting LoL Rune Page Manager API Server...")
    
    # Initialize backend components
    lcu_monitor = LCUMonitor()
    preset_provider = PresetProvider()
    rune_controller = RunePageController(lcu_monitor)
    
    # Create state manager to coordinate components
    state_manager = StateManager(
        lcu_monitor=lcu_monitor,
        preset_provider=preset_provider,
        rune_controller=rune_controller
    )
    
    # Create API server
    # Listen on 0.0.0.0 to allow mobile devices on local network to connect
    api_server = APIServer(
        state_manager=state_manager,
        host="0.0.0.0",  # Listen on all network interfaces
        port=8765        # Default port
    )
    
    logger.info("API server configured:")
    logger.info(f"  - Host: {api_server.host}")
    logger.info(f"  - Port: {api_server.port}")
    logger.info(f"  - REST API: http://{api_server.host}:{api_server.port}/api")
    logger.info(f"  - WebSocket: ws://{api_server.host}:{api_server.port}/ws")
    logger.info("")
    logger.info("Available endpoints:")
    logger.info("  GET  /api/health          - Health check")
    logger.info("  GET  /api/state           - Get current application state")
    logger.info("  GET  /api/presets         - Get available presets")
    logger.info("  POST /api/preset/select   - Select and apply a preset")
    logger.info("  PATCH /api/rune/edit      - Edit a rune in active slot")
    logger.info("  POST /api/edit-mode       - Toggle edit mode")
    logger.info("  GET  /api/pages           - Get all rune pages")
    logger.info("  WS   /ws                  - WebSocket for real-time updates")
    logger.info("")
    logger.info("Mobile devices on the local network can connect to:")
    logger.info(f"  http://<your-local-ip>:{api_server.port}")
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    
    try:
        # Start the server (blocking)
        await api_server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


def run_server():
    """Convenience function to run the server."""
    asyncio.run(main())


if __name__ == "__main__":
    run_server()
