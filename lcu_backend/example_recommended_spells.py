#!/usr/bin/env python3
"""
Example usage of recommended summoner spells in preset system.

This script demonstrates how to:
1. Load presets with recommended summoner spells
2. Access recommended spell IDs from presets
3. Look up spell details using SummonerSpellManager
4. Display recommended spells alongside rune presets
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lcu_backend.lcu_connection import LCUConnection
from lcu_backend.preset_provider import PresetProvider, RuneContext
from lcu_backend.summoner_spell_manager import SummonerSpellManager


async def main():
    """Main example function"""
    print("=== Recommended Summoner Spells Example ===\n")
    
    # Step 1: Initialize preset provider
    print("1. Loading preset database...")
    preset_provider = PresetProvider()
    preset_provider.load_from_file("lcu_backend/preset_database.json")
    print(f"   ✓ Loaded {preset_provider.database_info['presetCount']} presets\n")
    
    # Step 2: Initialize LCU connection and spell manager
    print("2. Connecting to League Client...")
    connection = LCUConnection()
    connected = await connection.retry_until_connected(max_retries=10)
    
    if not connected:
        print("   ❌ Failed to connect to League Client")
        print("   Continuing with offline example...\n")
        spell_manager = None
    else:
        print("   ✓ Connected to League Client")
        spell_manager = SummonerSpellManager(connection)
        
        # Load spell catalog
        print("   Loading summoner spell catalog...")
        try:
            await spell_manager.load_spell_catalog()
            print(f"   ✓ Loaded {len(spell_manager.get_spell_catalog())} summoner spells\n")
        except Exception as e:
            print(f"   ⚠️  Could not load spell catalog: {e}")
            print("   Continuing without spell name lookup...\n")
            spell_manager = None
    
    # Step 3: Query presets for a champion
    print("3. Querying presets for Annie (middle lane, ranked solo)...")
    context = RuneContext(
        championId=1,      # Annie
        queueId=420,       # Ranked Solo/Duo
        role="middle"
    )
    
    presets = preset_provider.get_presets(context)
    print(f"   ✓ Found {len(presets)} presets\n")
    
    # Step 4: Display presets with recommended spells
    print("4. Preset Details with Recommended Summoner Spells:")
    print("   " + "=" * 70)
    
    for i, preset in enumerate(presets, 1):
        print(f"\n   Preset {i}: {preset.name}")
        print(f"   Primary Style: {preset.primaryStyleId}")
        print(f"   Sub Style: {preset.subStyleId}")
        
        # Display recommended spells
        if preset.recommendedSpells:
            print(f"   Recommended Spells: {preset.recommendedSpells}")
            
            # If spell manager is available, show spell names
            if spell_manager:
                spell_names = []
                for spell_id in preset.recommendedSpells:
                    spell = spell_manager.get_spell_by_id(spell_id)
                    if spell:
                        spell_names.append(spell.name)
                    else:
                        spell_names.append(f"Unknown (ID: {spell_id})")
                
                print(f"   Spell Names: {' + '.join(spell_names)}")
        else:
            print("   Recommended Spells: None specified")
    
    print("\n")
    
    # Step 5: Demonstrate spell ID mapping
    print("5. Common Summoner Spell IDs:")
    print("   " + "=" * 70)
    
    common_spells = {
        4: "Flash",
        14: "Ignite",
        12: "Teleport",
        11: "Smite",
        7: "Heal",
        21: "Barrier",
        3: "Exhaust",
        1: "Cleanse",
    }
    
    for spell_id, spell_name in common_spells.items():
        print(f"   [{spell_id:3d}] {spell_name}")
    
    print("\n")
    
    # Step 6: Show how to use recommended spells in UI
    print("6. UI Integration Example:")
    print("   " + "=" * 70)
    print("""
   When displaying a preset in the UI:
   
   1. Get the preset from PresetProvider
   2. Check if preset.recommendedSpells is not None
   3. If available, display the recommended spell icons
   4. Allow user to override with different spells
   5. When applying preset, optionally auto-select recommended spells
   
   Example code:
   
   preset = presets[0]
   if preset.recommendedSpells:
       spell1_id, spell2_id = preset.recommendedSpells
       
       # Get spell details
       spell1 = spell_manager.get_spell_by_id(spell1_id)
       spell2 = spell_manager.get_spell_by_id(spell2_id)
       
       # Display in UI
       display_spell_icon(spell1.icon_path)
       display_spell_icon(spell2.icon_path)
       
       # Optionally auto-apply during champion select
       await spell_manager.update_summoner_spells(
           spell1_id=spell1_id,
           spell2_id=spell2_id,
           current_phase=GameflowPhase.CHAMP_SELECT
       )
   """)
    
    # Step 7: Show preset without recommended spells
    print("\n7. Handling Presets Without Recommended Spells:")
    print("   " + "=" * 70)
    print("""
   Some presets may not have recommended spells (recommendedSpells=None).
   In this case:
   
   1. Don't display recommended spell icons
   2. Let user select spells manually
   3. Use default spells for the role (e.g., Flash + Ignite for mid)
   
   Example code:
   
   if preset.recommendedSpells is None:
       # Use role-based defaults
       default_spells = get_default_spells_for_role(context.role)
       display_spell_selection(default_spells)
   """)
    
    # Cleanup
    if spell_manager:
        print("\n8. Cleaning up...")
        await connection.close()
        print("   ✓ Connection closed")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
