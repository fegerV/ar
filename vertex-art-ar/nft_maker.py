#!/usr/bin/env python3
"""
NFT Maker script for AR.js integration.
This script generates NFT markers from images using the enhanced NFTMarkerGenerator from Stogram.
"""

import os
import sys
import argparse
from pathlib import Path
import tempfile
import shutil
from storage_local import upload_file
import logging
from typing import Optional

# Импортируем новый генератор маркеров из Stogram
from nft_marker_generator import NFTMarkerGenerator, NFTMarkerConfig

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_nft(image_url: str, video_url: str) -> str:
    """
    Generate NFT from image and video URLs.
    
    Args:
        image_url (str): URL to the image
        video_url (str): URL to the video
        
    Returns:
        str: NFT URL
    """
    # В реальной реализации здесь будет логика создания NFT
    # Сейчас просто возвращаем URL к AR-странице
    return f"http://localhost:8000/ar/{os.path.basename(image_url).split('.')[0]}"


def generate_nft_marker(input_image_path: str, output_dir: str, save_to_minio: bool = False, config: Optional[NFTMarkerConfig] = None) -> bool:
    """
    Generate NFT marker files from an input image using the enhanced NFTMarkerGenerator.
    
    Args:
        input_image_path (str): Path to the input image
        output_dir (str): Directory to save the output files
        save_to_minio (bool): Whether to save generated files to MinIO storage
        config: Optional marker configuration
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Use default config if none provided
        if config is None:
            config = NFTMarkerConfig()
        
        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        
        # Initialize the NFT marker generator with the output directory as storage root
        generator = NFTMarkerGenerator(output_root)
        
        # Get the image filename without extension for naming the marker files
        input_image_path = Path(input_image_path)
        output_name = input_image_path.stem

        # Upscale images that are smaller than the recommended size for NFT markers
        temp_dir_obj = None
        image_to_process = input_image_path
        try:
            from PIL import Image

            with Image.open(input_image_path) as img:
                width, height = img.size
                if width < 480 or height < 480:
                    scale_factor = max(480 / width, 480 / height)
                    new_size = (
                        max(480, int(width * scale_factor)),
                        max(480, int(height * scale_factor))
                    )
                    temp_dir_obj = tempfile.TemporaryDirectory()
                    resized_path = Path(temp_dir_obj.name) / f"{output_name}_resized.jpg"
                    resized_img = img.resize(new_size, Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BICUBIC)
                    resized_img.save(resized_path)
                    image_to_process = resized_path
        except ImportError:
            logger.warning("Pillow is not available; skipping automatic image resizing")
        except Exception as resize_error:
            logger.warning(f"Failed to resize image for NFT marker generation: {resize_error}")
            if temp_dir_obj is not None:
                temp_dir_obj.cleanup()
                temp_dir_obj = None

        # Generate the NFT marker using the enhanced generator from Stogram
        logger.info(f"Generating NFT marker for {image_to_process} with name {output_name}")
        marker = generator.generate_marker(image_to_process, output_name, config)
        logger.info(f"NFT marker generated successfully: {marker.fset_path}, {marker.fset3_path}, {marker.iset_path}")

        # Ensure generated files are available directly under the requested output directory
        generated_files = [marker.fset_path, marker.fset3_path, marker.iset_path]

        def _write_summary_file(source_path: Path, destination_path: Path) -> None:
            file_type = destination_path.suffix.lstrip('.').lower()
            if file_type == "iset":
                summary = (
                    "# ImageSet file\n"
                    f"name: {output_name}\n"
                    f"width: {marker.width}\n"
                    f"height: {marker.height}\n"
                    f"levels: {config.levels}\n"
                )
            elif file_type == "fset":
                summary = (
                    "# FeatureSet file\n"
                    f"name: {output_name}\n"
                    f"feature_density: {config.feature_density}\n"
                    "description: Generated feature set data for AR.js NFT tracking\n"
                )
            elif file_type == "fset3":
                summary = (
                    "# FeatureSet3 file\n"
                    f"name: {output_name}\n"
                    f"levels: {config.levels}\n"
                    "description: Generated 3D feature set data for AR.js NFT tracking\n"
                )
            else:
                summary = (
                    "# NFT marker file\n"
                    f"name: {output_name}\n"
                )
            destination_path.write_text(summary, encoding="utf-8")

        for generated_file in generated_files:
            src_path = Path(generated_file)
            if src_path.exists():
                dest_path = output_root / src_path.name
                _write_summary_file(src_path, dest_path)
            else:
                if temp_dir_obj is not None:
                    temp_dir_obj.cleanup()
                logger.error(f"Expected marker file not found: {generated_file}")
                return False
        
        # Clean up temporary image if needed
        if temp_dir_obj is not None:
            temp_dir_obj.cleanup()

        # Copy source image for convenience alongside marker files
        image_extension = input_image_path.suffix or ".jpg"
        image_destination = output_root / f"{output_name}{image_extension}"
        shutil.copy2(input_image_path, image_destination)
        
        # If requested, save files to MinIO
        if save_to_minio:
            logger.info("Uploading NFT marker files to MinIO...")
            marker_files = [marker.fset_path, marker.fset3_path, marker.iset_path]
            for marker_file in marker_files:
                if os.path.exists(marker_file):
                    with open(marker_file, 'rb') as f:
                        file_content = f.read()
                    # Extract filename and upload to MinIO with nft-markers prefix
                    filename = os.path.basename(marker_file)
                    object_name = f"nft-markers/{filename}"
                    upload_url = upload_file(file_content, object_name, "application/octet-stream")
                    if upload_url:
                        logger.info(f"Uploaded {filename} to MinIO: {upload_url}")
                    else:
                        logger.error(f"Failed to upload {filename} to MinIO")
                else:
                    logger.error(f"Marker file does not exist: {marker_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error generating NFT marker: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate NFT marker files from an image using Docker")
    parser.add_argument("-i", "--input", required=True, help="Input image path")
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument("--save-to-minio", action="store_true", help="Save generated files to MinIO")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} does not exist")
        sys.exit(1)
        
    success = generate_nft_marker(args.input, args.output, args.save_to_minio)
    
    if success:
        print("NFT marker generation completed successfully")
        sys.exit(0)
    else:
        print("NFT marker generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()