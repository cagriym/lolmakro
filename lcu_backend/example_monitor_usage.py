"""Example usage of LCU Monitor component"""

import asyncio
from lcu_connection import LCUConnection
from lcu_monitor import LCUMonitor, GameflowPhase


async def main():
    """Example demonstrating LCU Monitor usage"""
    
    # Create connection and monitor
    connection = LCUConnection()
    monitor = LCUMonitor(connection)
    
    # Register callbacks for gameflow phase changes
    async def on_gameflow_change(phase: GameflowPhase | None):
        if phase is None:
            print("❌ League Client disconnected")
        else:
            print(f"🎮 Gameflow phase changed to: {phase.value}")
    
    # Register callbacks for champion select changes
    async def on_champ_select_change(session):
        if session is None:
            print("📋 Champion select ended or not available")
        else:
            print(f"🏆 Champion select session updated:")
            print(f"   Local player cell ID: {session.local_player_cell_id}")
            print(f"   Team size: {len(session.my_team)}")
            
            # Find local player's champion
            for player in session.my_team:
                if player.get("cellId") == session.local_player_cell_id:
                    champion_id = player.get("championId", 0)
                    role = player.get("assignedPosition", "none")
                    if champion_id > 0:
                        print(f"   Selected champion ID: {champion_id}")
                        print(f"   Assigned role: {role}")
                    else:
                        print("   No champion selected yet")
                    break
    
    monitor.on_gameflow_change(on_gameflow_change)
    monitor.on_champ_select_change(on_champ_select_change)
    
    # Start monitoring
    print("🚀 Starting LCU Monitor...")
    print("📡 Waiting for League Client connection...")
    print("   (Make sure League of Legends client is running)")
    print()
    
    # Wait for connection
    await connection.retry_until_connected()
    
    lockfile_info = await connection.get_lockfile_info()
    print(f"✅ Connected to League Client")
    print(f"   Port: {lockfile_info['port']}")
    print(f"   Lockfile: {lockfile_info['lockfilePath']}")
    print()
    
    # Start monitoring
    await monitor.start()
    
    print("👀 Monitoring gameflow state...")
    print("   Try entering champion select to see updates!")
    print("   Press Ctrl+C to stop")
    print()
    
    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping monitor...")
    finally:
        await monitor.stop()
        await connection.close()
        print("✅ Monitor stopped")


if __name__ == "__main__":
    asyncio.run(main())
