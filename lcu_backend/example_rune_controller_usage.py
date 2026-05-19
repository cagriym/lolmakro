# Example usage of Rune Page Controller
# Demonstrates app slot initialization and management

import asyncio
from lcu_backend.lcu_connection import LCUConnection
from lcu_backend.rune_page_controller import RunePageController


async def main():
    """Example: Initialize and manage app slots"""
    
    # Create LCU connection
    lcu = LCUConnection()
    
    print("Connecting to League Client...")
    connected = await lcu.retry_until_connected(max_retries=3)
    
    if not connected:
        print("❌ Failed to connect to League Client")
        print("Make sure League of Legends is running")
        return
    
    print("✓ Connected to League Client")
    
    # Create Rune Page Controller
    controller = RunePageController(lcu)
    
    print("\nInitializing app slots...")
    try:
        await controller.initialize()
        print("✓ App slots initialized successfully")
    except RuntimeError as e:
        print(f"❌ Failed to initialize app slots: {e}")
        await lcu.close()
        return
    
    # Display app slots
    print("\n=== App Slots ===")
    slots = controller.get_app_slots()
    
    for slot in slots:
        status = "ACTIVE" if slot.isActive else "inactive"
        print(f"\n{slot.name}:")
        print(f"  - Page ID: {slot.pageId}")
        print(f"  - Status: {status}")
        print(f"  - Current Page: {slot.currentPage.name if slot.currentPage else 'None'}")
    
    # Check if controller is initialized
    print(f"\nController initialized: {controller.is_initialized()}")
    
    # Display controller info
    print(f"\nTotal app slots: {len(slots)}")
    active_slots = [s for s in slots if s.isActive]
    print(f"Active slots: {len(active_slots)}")
    
    if active_slots:
        print(f"Active slot: {active_slots[0].name}")
    
    # Close connection
    await lcu.close()
    print("\n✓ Connection closed")


if __name__ == "__main__":
    asyncio.run(main())
