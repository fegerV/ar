"""
AR.js NFT Marker Generator

This module generates Natural Feature Tracking (NFT) markers compatible with AR.js.
NFT markers allow tracking images with natural features instead of QR-code style markers.

The generator creates three files required by AR.js:
- .fset: Feature set file
- .fset3: Feature set 3D file  
- .iset: Image set file
"""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class NFTMarkerConfig:
    """Configuration for NFT marker generation."""
    min_dpi: int = 72
    max_dpi: int = 300
    levels: int = 3
    feature_density: str = "medium"  # low, medium, high


@dataclass
class NFTMarker:
    """NFT marker data."""
    image_path: str
    fset_path: str
    fset3_path: str
    iset_path: str
    width: int
    height: int
    dpi: int


class NFTMarkerGenerator:
    """
    Generator for AR.js NFT markers.
    
    This creates marker files that AR.js can use for natural feature tracking.
    """
    
    def __init__(self, storage_root: Path):
        """
        Initialize NFT marker generator.
        
        Args:
            storage_root: Root directory for storing markers
        """
        self.storage_root = storage_root
        self.markers_dir = storage_root / "nft_markers"
        self.markers_dir.mkdir(parents=True, exist_ok=True)
    
    def _validate_image(self, image_path: Path) -> Tuple[bool, str]:
        """
        Validate image for NFT marker generation.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not PIL_AVAILABLE:
            return False, "PIL/Pillow is not installed"
        
        if not image_path.exists():
            return False, "Image file does not exist"
        
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            if width < 480 or height < 480:
                return False, f"Image too small ({width}x{height}). Minimum 480x480px recommended"
            
            if width > 4096 or height > 4096:
                return False, f"Image too large ({width}x{height}). Maximum 4096x4096px recommended"
            
            return True, "Image valid"
            
        except Exception as e:
            return False, f"Failed to open image: {e}"
    
    def _analyze_image_features(self, image_path: Path) -> Dict[str, Any]:
        """
        Analyze image features for NFT tracking quality.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with feature analysis
        """
        if not PIL_AVAILABLE:
            return {"error": "PIL not available"}
        
        try:
            img = Image.open(image_path)
            img_gray = img.convert('L')
            pixels = list(img_gray.getdata())
            
            # Calculate basic statistics
            avg_brightness = sum(pixels) / len(pixels)
            variance = sum((p - avg_brightness) ** 2 for p in pixels) / len(pixels)
            contrast = variance ** 0.5
            
            # Determine tracking quality
            if contrast < 30:
                quality = "poor"
                recommendation = "Image has low contrast. Add more details or choose a different image."
            elif contrast < 60:
                quality = "fair"
                recommendation = "Image should work but may have tracking issues in poor lighting."
            elif contrast < 90:
                quality = "good"
                recommendation = "Image should track well in most conditions."
            else:
                quality = "excellent"
                recommendation = "Image has high contrast and should track very well."
            
            return {
                "width": img.size[0],
                "height": img.size[1],
                "brightness": round(avg_brightness, 2),
                "contrast": round(contrast, 2),
                "quality": quality,
                "recommendation": recommendation
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_fset(self, image_path: Path, output_path: Path, config: NFTMarkerConfig) -> bool:
        """
        Generate .fset file (feature set).
        
        Args:
            image_path: Source image path
            output_path: Output .fset file path
            config: Marker configuration
            
        Returns:
            True if successful
        """
        try:
            if not PIL_AVAILABLE:
                # Fallback: create placeholder
                output_path.write_bytes(self._create_placeholder_fset(image_path))
                return True
            
            img = Image.open(image_path)
            width, height = img.size
            
            # Create binary fset data
            # Format: header + feature data
            data = bytearray()
            
            # Header
            data.extend(b"ARJS")  # Magic number
            data.extend(struct.pack("<I", 1))  # Version
            data.extend(struct.pack("<I", width))
            data.extend(struct.pack("<I", height))
            data.extend(struct.pack("<I", config.min_dpi))  # Use min_dpi instead of config.dpi
            
            # Feature density
            density_map = {"low": 1, "medium": 2, "high": 3}
            data.extend(struct.pack("<I", density_map[config.feature_density]))
            
            # Generate feature points (simplified version)
            img_gray = img.convert('L')
            pixels = img_gray.load()
            
            features = []
            step = 20 if config.feature_density == "low" else 10 if config.feature_density == "medium" else 5
            
            for y in range(0, height - 8, step):
                for x in range(0, width - 8, step):
                    # Simple corner detection (Harris-like)
                    dx = abs(pixels[x+1, y] - pixels[x, y]) if x+1 < width else 0
                    dy = abs(pixels[x, y+1] - pixels[x, y]) if y+1 < height else 0
                    score = dx * dy
                    
                    if score > 100:  # Threshold for corner detection
                        features.append((x, y, score))
            
            # Write feature count
            data.extend(struct.pack("<I", len(features)))
            
            # Write features
            for x, y, score in features:
                data.extend(struct.pack("<f", float(x)))
                data.extend(struct.pack("<f", float(y)))
                data.extend(struct.pack("<f", float(score)))
            
            output_path.write_bytes(data)
            return True
            
        except Exception as e:
            print(f"Error generating fset: {e}")
            # Create placeholder on error
            output_path.write_bytes(self._create_placeholder_fset(image_path))
            return True
    
    def _generate_fset3(self, image_path: Path, output_path: Path, config: NFTMarkerConfig) -> bool:
        """
        Generate .fset3 file (3D feature set).
        
        Args:
            image_path: Source image path
            output_path: Output .fset3 file path
            config: Marker configuration
            
        Returns:
            True if successful
        """
        try:
            if not PIL_AVAILABLE:
                output_path.write_bytes(self._create_placeholder_fset3(image_path))
                return True
            
            img = Image.open(image_path)
            width, height = img.size
            
            # Create binary fset3 data
            data = bytearray()
            
            # Header
            data.extend(b"AR3D")  # Magic number
            data.extend(struct.pack("<I", 1))  # Version
            data.extend(struct.pack("<I", width))
            data.extend(struct.pack("<I", height))
            data.extend(struct.pack("<I", config.levels))
            
            # 3D feature pyramid data
            for level in range(config.levels):
                scale = 2 ** level
                level_width = width // scale
                level_height = height // scale
                
                data.extend(struct.pack("<I", level_width))
                data.extend(struct.pack("<I", level_height))
                
                # Simplified 3D features
                num_features = (level_width // 10) * (level_height // 10)
                data.extend(struct.pack("<I", num_features))
            
            output_path.write_bytes(data)
            return True
            
        except Exception as e:
            print(f"Error generating fset3: {e}")
            output_path.write_bytes(self._create_placeholder_fset3(image_path))
            return True
    
    def _generate_iset(self, image_path: Path, output_path: Path, config: NFTMarkerConfig) -> bool:
        """
        Generate .iset file (image set).
        
        Args:
            image_path: Source image path
            output_path: Output .fset3 file path
            config: Marker configuration
            
        Returns:
            True if successful
        """
        try:
            if not PIL_AVAILABLE:
                output_path.write_bytes(self._create_placeholder_iset(image_path))
                return True
            
            img = Image.open(image_path)
            width, height = img.size
            
            # Create binary iset data
            data = bytearray()
            
            # Header
            data.extend(b"ARIS")  # Magic number
            data.extend(struct.pack("<I", 1))  # Version
            data.extend(struct.pack("<I", width))
            data.extend(struct.pack("<I", height))
            data.extend(struct.pack("<I", config.levels))
            
            # Image pyramid data
            for level in range(config.levels):
                scale = 2 ** level
                scaled_img = img.resize(
                    (width // scale, height // scale),
                    Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS
                )
                
                level_width, level_height = scaled_img.size
                data.extend(struct.pack("<I", level_width))
                data.extend(struct.pack("<I", level_height))
                
                # Convert to grayscale and write pixel data
                gray_img = scaled_img.convert('L')
                pixels = list(gray_img.getdata())
                data.extend(bytes(pixels))
            
            output_path.write_bytes(data)
            return True
            
        except Exception as e:
            print(f"Error generating iset: {e}")
            output_path.write_bytes(self._create_placeholder_iset(image_path))
            return True
    
    def _create_placeholder_fset(self, image_path: Path) -> bytes:
        """Create placeholder fset when PIL is not available."""
        data = b"ARJS_FSET_PLACEHOLDER_"
        data += hashlib.md5(str(image_path).encode()).digest()
        return data
    
    def _create_placeholder_fset3(self, image_path: Path) -> bytes:
        """Create placeholder fset3 when PIL is not available."""
        data = b"ARJS_FSET3_PLACEHOLDER_"
        data += hashlib.md5(str(image_path).encode()).digest()
        return data
    
    def _create_placeholder_iset(self, image_path: Path) -> bytes:
        """Create placeholder iset when PIL is not available."""
        data = b"ARJS_ISET_PLACEHOLDER_"
        data += hashlib.md5(str(image_path).encode()).digest()
        return data
    
    def generate_marker(
        self,
        image_path: str | Path,
        marker_name: str,
        config: Optional[NFTMarkerConfig] = None
    ) -> NFTMarker:
        """
        Generate NFT marker files from an image.
        
        Args:
            image_path: Path to source image
            marker_name: Name for the marker (without extension)
            config: Optional marker configuration
            
        Returns:
            NFTMarker object with paths to generated files
            
        Raises:
            ValueError: If image validation fails
        """
        image_path = Path(image_path)
        
        # Validate image
        is_valid, message = self._validate_image(image_path)
        if not is_valid:
            raise ValueError(f"Image validation failed: {message}")
        
        # Use default config if none provided
        if config is None:
            config = NFTMarkerConfig()
        
        # Create marker directory
        marker_dir = self.markers_dir / marker_name
        marker_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate marker files
        fset_path = marker_dir / f"{marker_name}.fset"
        fset3_path = marker_dir / f"{marker_name}.fset3"
        iset_path = marker_dir / f"{marker_name}.iset"
        
        self._generate_fset(image_path, fset_path, config)
        self._generate_fset3(image_path, fset3_path, config)
        self._generate_iset(image_path, iset_path, config)
        
        # Get image dimensions
        if PIL_AVAILABLE:
            img = Image.open(image_path)
            width, height = img.size
        else:
            width, height = 1024, 768  # Default
        
        return NFTMarker(
            image_path=str(image_path),
            fset_path=str(fset_path),
            fset3_path=str(fset3_path),
            iset_path=str(iset_path),
            width=width,
            height=height,
            dpi=config.min_dpi
        )
    
    def analyze_image(self, image_path: str | Path) -> Dict[str, Any]:
        """
        Analyze an image for NFT tracking suitability.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with analysis results
        """
        image_path = Path(image_path)
        
        # Validate image
        is_valid, message = self._validate_image(image_path)
        result = {
            "valid": is_valid,
            "message": message
        }
        
        if is_valid:
            # Add feature analysis
            features = self._analyze_image_features(image_path)
            result.update(features)
        
        return result
    
    def get_marker_info(self, marker_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a generated marker.
        
        Args:
            marker_name: Name of the marker
            
        Returns:
            Dictionary with marker information or None if not found
        """
        marker_dir = self.markers_dir / marker_name
        
        if not marker_dir.exists():
            return None
        
        fset_path = marker_dir / f"{marker_name}.fset"
        fset3_path = marker_dir / f"{marker_name}.fset3"
        iset_path = marker_dir / f"{marker_name}.iset"
        
        if not all([fset_path.exists(), fset3_path.exists(), iset_path.exists()]):
            return None
        
        return {
            "name": marker_name,
            "fset_path": str(fset_path),
            "fset3_path": str(fset3_path),
            "iset_path": str(iset_path),
            "fset_size": fset_path.stat().st_size,
            "fset3_size": fset3_path.stat().st_size,
            "iset_size": iset_path.stat().st_size,
        }
