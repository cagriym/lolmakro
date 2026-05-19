#!/usr/bin/env python3
"""
Example usage of Summoner Spell Manager component.

This script demonstrates how to:
1. Initialize the summoner spell manager
2. Load spell catalog from LCU API
3. Access and display spell information
4. Look up specific spells by ID
5. Get current summoner spell selection
6. Update summoner spells during champion select
"""

import asyncio
from lcu_connection import LCUConnection
from summoner_spell_manager import SummonerSpellManager
from lcu_monitor import LCUMonitor, GameflowPhase


async def main():
    """Main example function"""
    print("=== Summoner Spell Manager Example ===\n")
    
    # Step 1: Initialize LCU connection
    print("1. Initializing LCU connection...")
    connection = LCUConnection()
    
    # Wait for connection
    print("   Waiting for League Client...")
    connected = await connection.retry_until_connected(max_retries=10)
    
    if not connected:
        print("   ❌ Failed to connect to League Client")
        print("   Please make sure League of Legends is running")
        return
    
    print("   ✓ Connected to League Client\n")
    
    # Step 2: Initialize spell manager and monitor
    print("2. Initializing Summoner Spell Manager...")
    spell_manager = SummonerSpellManager(connection)
    monitor = LCUMonitor(connection)
    print("   ✓ Spell manager initialized\n")
    
    # Step 3: Load spell catalog
    print("3. Loading summoner spell catalog from LCU API...")
    try:
        spells = await spell_manager.load_spell_catalog()
        print(f"   ✓ Loaded {len(spells)} summoner spells\n")
    except RuntimeError as e:
        print(f"   ❌ Failed to load spell catalog: {e}")
        await connection.close()
        return
    
    # Step 4: Display all spells
    print("4. Available Summoner Spells (alphabetically sorted):")
    print("   " + "=" * 70)
    for spell in spells:
        print(f"   [{spell.id:3d}] {spell.name:15s} - {spell.description[:50]}...")
    print()
    
    # Step 5: Look up specific spells
    print("5. Looking up common summoner spells:")
    common_spell_ids = [4, 14, 12, 11, 7, 21]
    
    for spell_id in common_spell_ids:
        spell = spell_manager.get_spell_by_id(spell_id)
        if spell:
            print(f"   • {spell.name} (ID: {spell.id})")
            print(f"     Description: {spell.description}")
            print(f"     Icon: {spell.icon_path}")
            print()
    
    # Step 6: Demonstrate caching
    print("6. Demonstrating caching:")
    print(f"   Catalog loaded: {spell_manager.is_catalog_loaded()}")
    
    # Get catalog without API call (uses cache)
    cached_spells = spell_manager.get_spell_catalog()
    print(f"   Retrieved {len(cached_spells)} spells from cache")
    print()
    
    # Step 7: Search for specific spell
    print("7. Searching for 'Flash':")
    flash_spells = [s for s in spells if "Flash" in s.name]
    for spell in flash_spells:
        print(f"   Found: {spell.name} (ID: {spell.id})")
    print()
    
    # Step 8: Display spell statistics
    print("8. Spell Catalog Statistics:")
    total_spells = len(spells)
    spells_with_desc = sum(1 for s in spells if s.description)
    spells_with_icon = sum(1 for s in spells if s.icon_path)
    
    print(f"   Total spells: {total_spells}")
    print(f"   Spells with description: {spells_with_desc}")
    print(f"   Spells with icon path: {spells_with_icon}")
    print()
    
    # Step 9: Check current gameflow phase
    print("9. Checking gameflow phase...")
    await monitor.start()
    await asyncio.sleep(1)  # Wait for initial poll
    current_phase = await monitor.get_gameflow_phase()
    print(f"   Current phase: {current_phase}")
    print()
    
    # Step 10: Get current spell selection (if in champion select)
    print("10. Getting current summoner spell selection...")
    if current_phase == GameflowPhase.CHAMP_SELECT:
        try:
            selection = await spell_manager.get_current_spell_selection()
            if selection:
                spell1 = spell_manager.get_spell_by_id(selection.spell1_id)
                spell2 = spell_manager.get_spell_by_id(selection.spell2_id)
                print(f"   Current spells:")
                print(f"   • Spell 1: {spell1.name if spell1 else 'Unknown'} (ID: {selection.spell1_id})")
                print(f"   • Spell 2: {spell2.name if spell2 else 'Unknown'} (ID: {selection.spell2_id})")
            else:
                print("   No spell selection available (champion not selected yet)")
        except Exception as e:
            print(f"   ❌ Failed to get spell selection: {e}")
    else:
        print("   Not in champion select phase - spell selection not available")
    print()
    
    # Step 11: Demonstrate spell update (only if in champion select)
    print("11. Demonstrating spell update:")
    if current_phase == GameflowPhase.CHAMP_SELECT:
        print("   ⚠️  In champion select - spell updates are allowed")
        print("   Example: Updating to Flash + Ignite")
        print("   (Uncomment the code below to actually update spells)")
        print()
        # Uncomment to actually update spells:
        # try:
        #     await spell_manager.update_summoner_spells(
        #         spell1_id=4,   # Flash
        #         spell2_id=14,  # Ignite
        #         current_phase=current_phase
        #     )
        #     print("   ✓ Spells updated successfully")
        # except Exception as e:
        #     print(f"   ❌ Failed to update spells: {e}")
    else:
        print("   Not in champion select - spell updates are blocked")
        print("   Attempting update outside champion select will raise ValueError")
        try:
            await spell_manager.update_summoner_spells(
                spell1_id=4,
                spell2_id=14,
                current_phase=current_phase
            )
        except ValueError as e:
            print(f"   ✓ Update correctly blocked: {e}")
    print()
    
    # Cleanup
    print("12. Cleaning up...")
    await monitor.stop()
    await connection.close()
    print("   ✓ Connection closed")
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
