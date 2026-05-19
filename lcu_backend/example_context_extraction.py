#!/usr/bin/env python3
"""
Example demonstrating champion select context extraction.

This example shows how to use the LCU Monitor and Context Extractor
to detect when a player selects a champion and extract the relevant context.
"""

import asyncio
from lcu_backend.lcu_connection import LCUConnection
from lcu_backend.lcu_monitor import LCUMonitor, GameflowPhase, ChampSelectSession
from lcu_backend.context_extractor import extract_champ_select_context, ChampSelectContext


async def on_gameflow_change(phase: GameflowPhase | None) -> None:
    """Handle gameflow phase changes"""
    if phase is None:
        print("❌ LCU connection lost")
    else:
        print(f"🎮 Gameflow phase changed: {phase.value}")


async def on_champ_select_change(session: ChampSelectSession | None) -> None:
    """Handle champion select session changes"""
    if session is None:
        print("⏳ Champion select session ended or not available")
        return
    
    # Extract context from session
    context = extract_champ_select_context(session)
    
    if context is None:
        print("⏳ Waiting for champion selection...")
    else:
        print(f"✅ Champion selected!")
        print(f"   Champion ID: {context.champion_id}")
        print(f"   Queue ID: {context.queue_id}")
        print(f"   Role: {context.role}")
        print(f"   Phase: {context.phase}")


async def main():
    """Main example function"""
    print("🚀 Starting LCU Monitor with Context Extraction Example")
    print("=" * 60)
    
    # Create LCU connection
    connection = LCUConnection()
    
    try:
        # Connect to LCU
        print("🔌 Connecting to League Client...")
        await connection.connect()
        print("✅ Connected to League Client")
        
        # Create and configure monitor
        monitor = LCUMonitor(connection)
        monitor.on_gameflow_change(on_gameflow_change)
        monitor.on_champ_select_change(on_champ_select_change)
        
        # Start monitoring
        print("👀 Monitoring gameflow and champion select...")
        print("   Enter champion select and pick a champion to see context extraction")
        print("   Press Ctrl+C to stop")
        print("=" * 60)
        
        await monitor.start()
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️  Stopping monitor...")
        
        # Stop monitoring
        await monitor.stop()
        print("✅ Monitor stopped")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await connection.disconnect()
        print("👋 Disconnected from League Client")


if __name__ == "__main__":
    asyncio.run(main())
