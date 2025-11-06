#!/usr/bin/env python3
"""
Test script for NFT Marker improvements.
Verifies that all new features are working correctly.
"""

import sys
from pathlib import Path

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))

from nft_marker_generator import NFTAnalysisCache, NFTMarkerConfig, NFTMarkerGenerator


def test_imports():
    """Test that all imports work correctly."""
    print("✓ All imports successful")


def test_config_serialization():
    """Test NFTMarkerConfig serialization."""
    config = NFTMarkerConfig(
        min_dpi=150, max_dpi=300, levels=4, feature_density="high", auto_enhance_contrast=True, contrast_factor=1.8
    )

    # Test to_dict
    config_dict = config.to_dict()
    assert config_dict["min_dpi"] == 150
    assert config_dict["feature_density"] == "high"
    assert config_dict["auto_enhance_contrast"] is True

    # Test from_dict
    config2 = NFTMarkerConfig.from_dict(config_dict)
    assert config2.min_dpi == 150
    assert config2.contrast_factor == 1.8

    print("✓ Config serialization working")


def test_cache_initialization():
    """Test NFTAnalysisCache initialization."""
    cache_dir = Path("/tmp/test_nft_cache")
    cache = NFTAnalysisCache(cache_dir, ttl_days=7)

    assert cache.cache_dir == cache_dir
    assert cache.cache_dir.exists()

    print("✓ Cache initialization working")


def test_generator_initialization():
    """Test NFTMarkerGenerator initialization with caching."""
    storage_root = Path("/tmp/test_nft_storage")
    storage_root.mkdir(parents=True, exist_ok=True)

    # With cache
    generator = NFTMarkerGenerator(storage_root, enable_cache=True)
    assert generator.cache is not None
    assert generator.markers_dir.exists()

    # Without cache
    generator2 = NFTMarkerGenerator(storage_root, enable_cache=False)
    assert generator2.cache is None

    print("✓ Generator initialization working")


def test_metrics():
    """Test metrics tracking."""
    storage_root = Path("/tmp/test_nft_storage")
    generator = NFTMarkerGenerator(storage_root)

    metrics = generator.get_metrics()
    assert "total_generated" in metrics
    assert "cache_hits" in metrics
    assert "cache_misses" in metrics
    assert "avg_time_per_marker" in metrics

    print("✓ Metrics tracking working")


def test_preset_operations():
    """Test config preset operations."""
    storage_root = Path("/tmp/test_nft_storage")
    generator = NFTMarkerGenerator(storage_root)

    # Create preset
    config = NFTMarkerConfig(min_dpi=150, feature_density="high", levels=4)

    preset_path = generator.export_config(config, "test_preset")
    assert preset_path.exists()

    # List presets
    presets = generator.list_presets()
    assert len(presets) > 0
    assert any(p["name"] == "test_preset" for p in presets)

    # Import preset
    imported_config = generator.import_config("test_preset")
    assert imported_config.min_dpi == 150
    assert imported_config.feature_density == "high"

    print("✓ Preset operations working")


def test_cleanup_simulation():
    """Test cleanup operations (dry run only)."""
    storage_root = Path("/tmp/test_nft_storage")
    generator = NFTMarkerGenerator(storage_root)

    # Dry run - should not delete anything
    result = generator.cleanup_unused_markers(used_marker_names=[], dry_run=True)

    assert "total_markers" in result
    assert "deleted_count" in result
    assert result["dry_run"] is True

    print("✓ Cleanup operations working")


def main():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("Testing NFT Marker Improvements")
    print("=" * 50 + "\n")

    try:
        test_imports()
        test_config_serialization()
        test_cache_initialization()
        test_generator_initialization()
        test_metrics()
        test_preset_operations()
        test_cleanup_simulation()

        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50 + "\n")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
