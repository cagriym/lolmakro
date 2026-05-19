"""
Verification script for the expanded preset database.
Shows statistics and sample data from the preset database.
"""

import json
from collections import defaultdict

def verify_preset_database():
    """Load and verify the preset database structure and content."""
    with open('lcu_backend/preset_database.json', 'r') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("PRESET DATABASE VERIFICATION")
    print("=" * 80)
    
    # Basic info
    print(f"\nVersion: {data['version']}")
    print(f"Last Updated: {data['lastUpdated']}")
    
    # Preset statistics
    print(f"\n{'PRESET STATISTICS':-^80}")
    print(f"Total Preset Entries: {len(data['presets'])}")
    
    # Group by champion
    champion_presets = defaultdict(list)
    for preset in data['presets']:
        champion_presets[preset['championId']].append(preset)
    
    print(f"Unique Champions: {len(champion_presets)}")
    
    # Champion breakdown
    champion_names = {
        1: "Annie",
        157: "Yasuo",
        238: "Zed",
        103: "Ahri",
        222: "Jinx",
        412: "Thresh",
        64: "Lee Sin",
        122: "Darius",
        99: "Lux"
    }
    
    print(f"\n{'CHAMPION BREAKDOWN':-^80}")
    for champ_id, presets in sorted(champion_presets.items()):
        champ_name = champion_names.get(champ_id, f"Champion {champ_id}")
        total_pages = sum(len(p['pages']) for p in presets)
        roles = set(p['role'] for p in presets)
        print(f"{champ_name:15} - {len(presets)} entries, {total_pages} total pages, roles: {', '.join(sorted(roles))}")
    
    # Rune metadata statistics
    print(f"\n{'RUNE METADATA STATISTICS':-^80}")
    print(f"Total Rune Entries: {len(data['runeMetadata'])}")
    
    # Group by style
    runes_by_style = defaultdict(list)
    for rune in data['runeMetadata']:
        runes_by_style[rune['styleId']].append(rune)
    
    style_names = {
        8000: "Precision",
        8100: "Domination",
        8200: "Sorcery",
        8300: "Inspiration",
        8400: "Resolve",
        0: "Stat Shards"
    }
    
    print(f"\n{'RUNES BY STYLE':-^80}")
    for style_id, runes in sorted(runes_by_style.items()):
        style_name = style_names.get(style_id, f"Style {style_id}")
        keystones = [r for r in runes if r['slot'] == 0]
        print(f"{style_name:15} - {len(runes)} runes ({len(keystones)} keystones)")
    
    # Style metadata
    print(f"\n{'STYLE METADATA':-^80}")
    print(f"Total Styles: {len(data['styleMetadata'])}")
    for style in data['styleMetadata']:
        print(f"{style['name']:15} - {len(style['slots'])} slots")
    
    # Sample presets
    print(f"\n{'SAMPLE PRESETS':-^80}")
    for i, preset_entry in enumerate(data['presets'][:3]):
        champ_name = champion_names.get(preset_entry['championId'], f"Champion {preset_entry['championId']}")
        print(f"\n{champ_name} ({preset_entry['role']}):")
        for page in preset_entry['pages']:
            primary_style = style_names.get(page['primaryStyleId'], f"Style {page['primaryStyleId']}")
            sub_style = style_names.get(page['subStyleId'], f"Style {page['subStyleId']}")
            spells = page.get('recommendedSpells', [])
            print(f"  - {page['name']}")
            print(f"    Primary: {primary_style}, Secondary: {sub_style}")
            print(f"    Recommended Spells: {spells}")
    
    # Validation checks
    print(f"\n{'VALIDATION CHECKS':-^80}")
    
    # Check all runes in presets have metadata
    all_rune_ids = set(r['id'] for r in data['runeMetadata'])
    missing_runes = set()
    
    for preset_entry in data['presets']:
        for page in preset_entry['pages']:
            for rune_id in page['selectedPerkIds']:
                if rune_id not in all_rune_ids:
                    missing_runes.add(rune_id)
            for shard_id in page['statShards']:
                if shard_id not in all_rune_ids:
                    missing_runes.add(shard_id)
    
    if missing_runes:
        print(f"⚠️  WARNING: {len(missing_runes)} rune IDs used in presets but missing metadata: {missing_runes}")
    else:
        print("✓ All runes used in presets have metadata")
    
    # Check all styles in presets have metadata
    all_style_ids = set(s['id'] for s in data['styleMetadata'])
    missing_styles = set()
    
    for preset_entry in data['presets']:
        for page in preset_entry['pages']:
            if page['primaryStyleId'] not in all_style_ids:
                missing_styles.add(page['primaryStyleId'])
            if page['subStyleId'] not in all_style_ids:
                missing_styles.add(page['subStyleId'])
    
    if missing_styles:
        print(f"⚠️  WARNING: {len(missing_styles)} style IDs used in presets but missing metadata: {missing_styles}")
    else:
        print("✓ All styles used in presets have metadata")
    
    # Check preset structure
    valid_presets = 0
    invalid_presets = []
    
    for preset_entry in data['presets']:
        for page in preset_entry['pages']:
            if (len(page['selectedPerkIds']) == 6 and 
                len(page['statShards']) == 3 and
                page['primaryStyleId'] != page['subStyleId']):
                valid_presets += 1
            else:
                invalid_presets.append(page['name'])
    
    print(f"✓ {valid_presets} valid preset pages")
    if invalid_presets:
        print(f"⚠️  WARNING: {len(invalid_presets)} invalid preset pages: {invalid_presets}")
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    verify_preset_database()
