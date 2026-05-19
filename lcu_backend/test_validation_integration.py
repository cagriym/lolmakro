"""
Integration test demonstrating complete rune page validation (Task 4.4)

This test demonstrates that the RunePageController properly validates
rune pages according to Requirements 15.1-15.8.
"""

import pytest
from unittest.mock import MagicMock

from lcu_backend.rune_page_controller import RunePageController
from lcu_backend.lcu_connection import LCUConnection
from lcu_backend.preset_provider import RunePage, PresetProvider, RuneMetadata


def test_complete_validation_flow():
    """
    Integration test demonstrating complete validation flow
    
    This test verifies that all validation requirements (15.1-15.8) are met:
    - 15.1: Page name validation
    - 15.2: Primary style ID validation
    - 15.3: Sub style ID validation
    - 15.4: Exactly 6 perks validation
    - 15.5: First 4 perks belong to primary style
    - 15.6: Last 2 perks belong to sub style
    - 15.7: Exactly 3 stat shards validation
    - 15.8: Error thrown on validation failure
    """
    # Setup mock LCU connection
    mock_lcu = MagicMock(spec=LCUConnection)
    
    # Setup mock preset provider with rune metadata
    mock_provider = MagicMock(spec=PresetProvider)
    
    # Define rune metadata for validation
    # Primary style 8000 runes: 8005, 9111, 9104, 8014
    # Sub style 8100 runes: 8126, 8106
    rune_metadata = {
        8005: RuneMetadata(id=8005, key="PressTheAttack", name="Press the Attack", 
                          shortDesc="", icon="", styleId=8000, slot=0),
        9111: RuneMetadata(id=9111, key="Triumph", name="Triumph", 
                          shortDesc="", icon="", styleId=8000, slot=1),
        9104: RuneMetadata(id=9104, key="LegendAlacrity", name="Legend: Alacrity", 
                          shortDesc="", icon="", styleId=8000, slot=2),
        8014: RuneMetadata(id=8014, key="CoupDeGrace", name="Coup de Grace", 
                          shortDesc="", icon="", styleId=8000, slot=3),
        8126: RuneMetadata(id=8126, key="CheapShot", name="Cheap Shot", 
                          shortDesc="", icon="", styleId=8100, slot=0),
        8106: RuneMetadata(id=8106, key="UltimateHunter", name="Ultimate Hunter", 
                          shortDesc="", icon="", styleId=8100, slot=1),
    }
    
    mock_provider.get_rune_metadata.side_effect = lambda rune_id: rune_metadata.get(rune_id)
    
    # Create controller with preset provider for full validation
    controller = RunePageController(mock_lcu, preset_provider=mock_provider)
    
    # Test 1: Valid page passes all validation
    valid_page = RunePage(
        name="Valid Test Page",
        primaryStyleId=8000,
        subStyleId=8100,
        selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
        statShards=[5008, 5008, 5002]
    )
    controller._validate_page(valid_page)  # Should not raise
    
    # Test 2: Empty name fails (Requirement 15.1)
    with pytest.raises(ValueError, match="Page name must be non-empty"):
        invalid_page = RunePage(
            name="",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        controller._validate_page(invalid_page)
    
    # Test 3: Invalid primary style fails (Requirement 15.2)
    with pytest.raises(ValueError, match="Invalid primary style ID"):
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=9999,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        controller._validate_page(invalid_page)
    
    # Test 4: Same primary and sub style fails (Requirement 15.3)
    with pytest.raises(ValueError, match="must be different"):
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8000,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008, 5002]
        )
        controller._validate_page(invalid_page)
    
    # Test 5: Wrong perk count fails (Requirement 15.4)
    with pytest.raises(ValueError, match="exactly 6 rune IDs"):
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126],  # Only 5
            statShards=[5008, 5008, 5002]
        )
        controller._validate_page(invalid_page)
    
    # Test 6: Primary perk with wrong style fails (Requirement 15.5)
    with pytest.raises(ValueError, match="belongs to style 8100.*but primary style is 8000"):
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8126, 8126, 8106],  # 8126 is style 8100, not 8000
            statShards=[5008, 5008, 5002]
        )
        controller._validate_page(invalid_page)
    
    # Test 7: Secondary perk with wrong style fails (Requirement 15.6)
    with pytest.raises(ValueError, match="belongs to style 8000.*but sub style is 8100"):
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8014, 8106],  # 8014 is style 8000, not 8100
            statShards=[5008, 5008, 5002]
        )
        controller._validate_page(invalid_page)
    
    # Test 8: Wrong stat shard count fails (Requirement 15.7)
    with pytest.raises(ValueError, match="exactly 3 stat shard IDs"):
        invalid_page = RunePage(
            name="Test",
            primaryStyleId=8000,
            subStyleId=8100,
            selectedPerkIds=[8005, 9111, 9104, 8014, 8126, 8106],
            statShards=[5008, 5008]  # Only 2
        )
        controller._validate_page(invalid_page)
    
    print("✅ All validation requirements (15.1-15.8) verified successfully!")


if __name__ == "__main__":
    test_complete_validation_flow()
    print("\n✅ Task 4.4 validation implementation complete!")
