"""
Example demonstrating preset query and retrieval (Task 3.2)

This example shows:
1. Loading the preset database
2. Querying presets with context (championId, queueId, role)
3. Retrieving rune metadata
4. Retrieving style metadata
5. Fallback behavior when exact match not found
"""

from preset_provider import PresetProvider, RuneContext


def main():
    # Initialize provider
    provider = PresetProvider()
    
    # Load preset database from JSON file
    print("Loading preset database...")
    provider.load_from_file("lcu_backend/preset_database.json")
    
    # Display database info
    info = provider.database_info
    print(f"\nDatabase loaded successfully!")
    print(f"  Version: {info['version']}")
    print(f"  Last Updated: {info['lastUpdated']}")
    print(f"  Presets: {info['presetCount']}")
    print(f"  Rune Metadata: {info['runeMetadataCount']}")
    print(f"  Style Metadata: {info['styleMetadataCount']}")
    
    # Example 1: Query presets with exact match
    print("\n" + "="*60)
    print("Example 1: Query presets for Annie middle (exact match)")
    print("="*60)
    
    context = RuneContext(championId=1, queueId=420, role="middle")
    presets = provider.get_presets(context)
    
    print(f"\nFound {len(presets)} preset(s) for Annie middle:")
    for i, preset in enumerate(presets, 1):
        print(f"\n{i}. {preset.name}")
        
        # Get primary style metadata
        primary_style = provider.get_style_metadata(preset.primaryStyleId)
        print(f"   Primary: {primary_style.name if primary_style else 'Unknown'}")
        
        # Get sub style metadata
        sub_style = provider.get_style_metadata(preset.subStyleId)
        print(f"   Secondary: {sub_style.name if sub_style else 'Unknown'}")
        
        # Display runes with metadata
        print(f"   Runes:")
        for j, rune_id in enumerate(preset.selectedPerkIds):
            rune_meta = provider.get_rune_metadata(rune_id)
            if rune_meta:
                slot_type = "Keystone" if j == 0 else f"Slot {j}"
                print(f"     - {slot_type}: {rune_meta.name}")
        
        # Display stat shards
        print(f"   Stat Shards:")
        for shard_id in preset.statShards:
            shard_meta = provider.get_rune_metadata(shard_id)
            if shard_meta:
                print(f"     - {shard_meta.name}")
    
    # Example 2: Query with fallback
    print("\n" + "="*60)
    print("Example 2: Query presets for Annie jungle (fallback)")
    print("="*60)
    
    context_fallback = RuneContext(championId=1, queueId=420, role="jungle")
    presets_fallback = provider.get_presets(context_fallback)
    
    print(f"\nNo exact match for Annie jungle, using fallback...")
    print(f"Found {len(presets_fallback)} fallback preset(s):")
    for i, preset in enumerate(presets_fallback, 1):
        print(f"  {i}. {preset.name}")
    
    # Example 3: Query for non-existent champion
    print("\n" + "="*60)
    print("Example 3: Query presets for unknown champion")
    print("="*60)
    
    context_unknown = RuneContext(championId=99999, queueId=420, role="middle")
    presets_unknown = provider.get_presets(context_unknown)
    
    print(f"\nFound {len(presets_unknown)} preset(s) for unknown champion")
    if not presets_unknown:
        print("  (No presets available)")
    
    # Example 4: Demonstrate metadata retrieval
    print("\n" + "="*60)
    print("Example 4: Detailed metadata for first preset")
    print("="*60)
    
    if presets:
        first_preset = presets[0]
        print(f"\nPreset: {first_preset.name}")
        
        # Primary style details
        primary = provider.get_style_metadata(first_preset.primaryStyleId)
        if primary:
            print(f"\nPrimary Style: {primary.name}")
            print(f"  Icon: {primary.icon}")
            print(f"  Slots: {len(primary.slots)} rows")
        
        # Sub style details
        sub = provider.get_style_metadata(first_preset.subStyleId)
        if sub:
            print(f"\nSecondary Style: {sub.name}")
            print(f"  Icon: {sub.icon}")
            print(f"  Slots: {len(sub.slots)} rows")
        
        # Detailed rune information
        print(f"\nDetailed Rune Information:")
        for i, rune_id in enumerate(first_preset.selectedPerkIds):
            rune = provider.get_rune_metadata(rune_id)
            if rune:
                print(f"\n  Rune {i+1}: {rune.name}")
                print(f"    Description: {rune.shortDesc}")
                print(f"    Icon: {rune.icon}")
                print(f"    Style ID: {rune.styleId}")
                print(f"    Slot: {rune.slot}")


if __name__ == "__main__":
    main()
