"""
Example usage of PresetProvider component
Demonstrates loading preset database and querying presets
"""

from pathlib import Path

from .preset_provider import PresetProvider, RuneContext


def main():
    """Example usage of PresetProvider"""
    
    # Create provider instance
    provider = PresetProvider()
    
    # Load preset database from JSON file
    db_path = Path(__file__).parent / "preset_database.json"
    
    print(f"Loading preset database from: {db_path}")
    provider.load_from_file(db_path)
    
    print(f"✓ Database loaded successfully")
    print(f"  Version: {provider.database_info['version']}")
    print(f"  Last Updated: {provider.database_info['lastUpdated']}")
    print(f"  Preset Entries: {provider.database_info['presetCount']}")
    print(f"  Rune Metadata: {provider.database_info['runeMetadataCount']}")
    print(f"  Style Metadata: {provider.database_info['styleMetadataCount']}")
    print()
    
    # Query presets for Annie (championId=1) in Ranked Solo (queueId=420) as mid
    context = RuneContext(championId=1, queueId=420, role="middle")
    
    print(f"Querying presets for context: {context}")
    presets = provider.get_presets(context)
    
    print(f"✓ Found {len(presets)} preset(s)")
    print()
    
    # Display each preset
    for i, preset in enumerate(presets, 1):
        print(f"Preset {i}: {preset.name}")
        print(f"  Primary Style: {preset.primaryStyleId}")
        print(f"  Sub Style: {preset.subStyleId}")
        print(f"  Selected Perks: {preset.selectedPerkIds}")
        print(f"  Stat Shards: {preset.statShards}")
        
        # Get rune metadata for keystone (first perk)
        keystone_id = preset.selectedPerkIds[0]
        keystone_meta = provider.get_rune_metadata(keystone_id)
        
        if keystone_meta:
            print(f"  Keystone: {keystone_meta.name} - {keystone_meta.shortDesc}")
        
        print()
    
    # Query presets for non-existent champion
    context_not_found = RuneContext(championId=999, queueId=420, role="middle")
    
    print(f"Querying presets for non-existent champion: {context_not_found}")
    presets_not_found = provider.get_presets(context_not_found)
    
    if not presets_not_found:
        print("✓ No presets found (as expected)")
    print()
    
    # Get style metadata
    sorcery_style = provider.get_style_metadata(8200)
    if sorcery_style:
        print(f"Style: {sorcery_style.name}")
        print(f"  Key: {sorcery_style.key}")
        print(f"  Icon: {sorcery_style.icon}")
        print(f"  Slots: {len(sorcery_style.slots)} slots")
        print()


if __name__ == "__main__":
    main()
