"""
Example usage of the State Manager component

This example demonstrates how to initialize and use the State Manager
to coordinate all components and handle state changes.
"""

import asyncio
from pathlib import Path

from lcu_backend.lcu_connection import LCUConnection
from lcu_backend.lcu_monitor import LCUMonitor
from lcu_backend.preset_provider import PresetProvider
from lcu_backend.rune_page_controller import RunePageController
from lcu_backend.state_manager import StateManager, AppState


async def on_state_change(state: AppState):
    """Callback for state changes"""
    print("\n=== State Changed ===")
    print(f"Gameflow Phase: {state.gameflow_phase}")
    print(f"Champion Select Context: {state.champ_select_context}")
    print(f"Available Presets: {len(state.available_presets)}")
    print(f"Selected Preset Index: {state.selected_preset_index}")
    print(f"Active Slot Index: {state.active_slot_index}")
    print(f"Edit Mode: {state.is_edit_mode}")
    print(f"App Slots: {len(state.app_slots)}")
    
    # Print preset details if available
    if state.available_presets:
        print("\nAvailable Presets:")
        for i, preset in enumerate(state.available_presets):
            print(f"  {i}. {preset.name}")
    
    # Print app slot details
    if state.app_slots:
        print("\nApp Slots:")
        for slot in state.app_slots:
            active_marker = " (ACTIVE)" if slot.isActive else ""
            current_page = slot.currentPage.name if slot.currentPage else "None"
            print(f"  Slot {slot.slotIndex}: {slot.name} - Page: {current_page}{active_marker}")


async def main():
    """Main example workflow"""
    print("=== State Manager Example ===\n")
    
    # Initialize components
    print("1. Initializing components...")
    
    # Create LCU connection
    lcu_connection = LCUConnection()
    
    # Try to connect to LCU
    try:
        await lcu_connection.connect()
        print("   ✓ Connected to League Client")
    except Exception as e:
        print(f"   ✗ Failed to connect to League Client: {e}")
        print("   Note: Make sure League of Legends client is running")
        return
    
    # Create LCU Monitor
    lcu_monitor = LCUMonitor(lcu_connection)
    
    # Create Preset Provider
    preset_provider = PresetProvider()
    
    # Load preset database
    preset_db_path = Path(__file__).parent / "preset_database.json"
    if preset_db_path.exists():
        preset_provider.load_from_file(preset_db_path)
        print(f"   ✓ Loaded preset database: {preset_provider.database_info}")
    else:
        print(f"   ⚠ Preset database not found at {preset_db_path}")
        print("   Creating minimal preset database for testing...")
        # Create minimal test database
        test_db = {
            "version": "1.0.0",
            "lastUpdated": "2024-01-01",
            "presets": [],
            "runeMetadata": [],
            "styleMetadata": []
        }
        preset_provider.initialize(test_db)
    
    # Create Rune Page Controller
    rune_page_controller = RunePageController(lcu_connection, preset_provider)
    
    # Create State Manager
    state_manager = StateManager(lcu_monitor, preset_provider, rune_page_controller)
    
    print("\n2. Initializing State Manager...")
    try:
        await state_manager.initialize()
        print("   ✓ State Manager initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize State Manager: {e}")
        return
    
    # Register state change callback
    state_manager.on_state_change(on_state_change)
    print("   ✓ Registered state change callback")
    
    # Get initial state
    print("\n3. Initial State:")
    initial_state = state_manager.get_current_state()
    await on_state_change(initial_state)
    
    # Monitor for state changes
    print("\n4. Monitoring for state changes...")
    print("   Waiting for champion select... (Press Ctrl+C to exit)")
    
    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
            # Example: If presets are available and none selected, auto-select first preset
            current_state = state_manager.get_current_state()
            if (current_state.available_presets and 
                current_state.selected_preset_index is None):
                print("\n   → Auto-selecting first preset...")
                try:
                    await state_manager.select_preset(0)
                    print("   ✓ Preset selected and applied")
                except Exception as e:
                    print(f"   ✗ Failed to select preset: {e}")
    
    except KeyboardInterrupt:
        print("\n\n5. Shutting down...")
        await state_manager.shutdown()
        await lcu_connection.disconnect()
        print("   ✓ Shutdown complete")


async def example_preset_selection():
    """Example of selecting a preset"""
    print("\n=== Preset Selection Example ===\n")
    
    # Assume state_manager is initialized and has presets available
    # This is a simplified example showing the API usage
    
    # Get current state
    # state = state_manager.get_current_state()
    
    # if state.available_presets:
    #     print(f"Available presets: {len(state.available_presets)}")
    #     
    #     # Select first preset
    #     await state_manager.select_preset(0)
    #     print("Selected preset 0")
    #     
    #     # Get updated state
    #     updated_state = state_manager.get_current_state()
    #     print(f"Active slot: {updated_state.active_slot_index}")
    
    print("(This is a code example - see main() for working implementation)")


async def example_rune_editing():
    """Example of editing a rune"""
    print("\n=== Rune Editing Example ===\n")
    
    # Assume state_manager is initialized and has an active slot
    # This is a simplified example showing the API usage
    
    # from lcu_backend.rune_page_controller import RuneSlotType
    
    # Edit keystone rune
    # await state_manager.edit_rune(8128, RuneSlotType.KEYSTONE)
    # print("Changed keystone to Dark Harvest (8128)")
    
    # Edit primary rune
    # await state_manager.edit_rune(8126, RuneSlotType.PRIMARY1)
    # print("Changed primary1 to Cheap Shot (8126)")
    
    print("(This is a code example - see main() for working implementation)")


if __name__ == "__main__":
    # Run main example
    asyncio.run(main())
    
    # Other examples (commented out - for reference only)
    # asyncio.run(example_preset_selection())
    # asyncio.run(example_rune_editing())
