"""
Example usage of rune metadata management with asset caching
Demonstrates the complete workflow for task 3.3
"""

from pathlib import Path
from asset_manager import AssetManager
from preset_provider import PresetProvider, RuneContext


def main():
    """Demonstrate metadata management functionality"""
    
    print("=== Rune Metadata Management Example ===\n")
    
    # 1. Create asset manager with caching
    print("1. Initializing Asset Manager...")
    asset_manager = AssetManager(
        cache_dir=Path("asset_cache"),
        version="14.1.1"
    )
    print(f"   Cache directory: {asset_manager.cache_dir}")
    print(f"   League version: {asset_manager.version}\n")
    
    # 2. Create preset provider with asset manager
    print("2. Initializing Preset Provider...")
    provider = PresetProvider(asset_manager=asset_manager)
    
    # 3. Load preset database
    print("3. Loading preset database...")
    provider.load_from_file("preset_database.json")
    print(f"   Database initialized: {provider.is_initialized}")
    
    # 4. Display database info
    info = provider.database_info
    print(f"   Version: {info['version']}")
    print(f"   Preset entries: {info['presetCount']}")
    print(f"   Rune metadata entries: {info['runeMetadataCount']}")
    print(f"   Style metadata entries: {info['styleMetadataCount']}\n")
    
    # 5. Preload common assets
    print("4. Preloading common assets...")
    print("   (This may take a moment on first run)")
    provider.preload_common_assets()
    
    cache_stats = asset_manager.get_cache_stats()
    print(f"   Cached rune icons: {cache_stats['runes']}")
    print(f"   Cached spell icons: {cache_stats['spells']}")
    print(f"   Cached champion icons: {cache_stats['champions']}\n")
    
    # 6. Get presets for a champion
    print("5. Getting presets for Annie (championId=1) in ranked solo queue...")
    context = RuneContext(championId=1, queueId=420, role="middle")
    presets = provider.get_presets(context)
    print(f"   Found {len(presets)} preset(s)\n")
    
    # 7. Display preset details with metadata
    for i, preset in enumerate(presets, 1):
        print(f"   Preset {i}: {preset.name}")
        
        # Get primary style metadata
        primary_style = provider.get_style_metadata(preset.primaryStyleId)
        if primary_style:
            print(f"   Primary Style: {primary_style.name} (ID: {primary_style.id})")
            style_icon = provider.get_style_icon_path(preset.primaryStyleId)
            if style_icon:
                print(f"   Primary Style Icon: {style_icon}")
        
        # Get sub style metadata
        sub_style = provider.get_style_metadata(preset.subStyleId)
        if sub_style:
            print(f"   Sub Style: {sub_style.name} (ID: {sub_style.id})")
        
        # Display runes with metadata
        print(f"   Runes:")
        for j, rune_id in enumerate(preset.selectedPerkIds):
            rune_meta = provider.get_rune_metadata(rune_id)
            if rune_meta:
                slot_name = ["Keystone", "Slot 1", "Slot 2", "Slot 3", "Secondary 1", "Secondary 2"][j]
                print(f"     {slot_name}: {rune_meta.name} (ID: {rune_id})")
                
                # Get cached icon path
                icon_path = provider.get_rune_icon_path(rune_id)
                if icon_path:
                    print(f"       Icon cached at: {icon_path}")
        
        print()
    
    # 8. Demonstrate metadata lookup
    print("6. Looking up specific rune metadata...")
    rune_id = 8214  # Summon Aery
    rune_meta = provider.get_rune_metadata(rune_id)
    if rune_meta:
        print(f"   Rune ID: {rune_meta.id}")
        print(f"   Name: {rune_meta.name}")
        print(f"   Key: {rune_meta.key}")
        print(f"   Description: {rune_meta.shortDesc}")
        print(f"   Style ID: {rune_meta.styleId}")
        print(f"   Slot: {rune_meta.slot}")
        print(f"   Icon path: {rune_meta.icon}")
        
        # Get cached icon
        icon_path = provider.get_rune_icon_path(rune_id)
        if icon_path:
            print(f"   Cached icon: {icon_path}")
    
    print("\n=== Metadata Management Complete ===")
    print("\nKey Features Demonstrated:")
    print("✓ Load rune metadata from embedded JSON")
    print("✓ Implement rune metadata lookup by rune ID")
    print("✓ Add style metadata with slot configurations")
    print("✓ Cache rune icons and metadata for performance")
    print("✓ Data Dragon integration for asset fetching")


if __name__ == "__main__":
    main()
