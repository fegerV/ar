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
from storage_adapter import upload_file
from typing import Optional
from dotenv import load_dotenv

from logging_setup import get_logger

# Импортируем новый генератор маркеров из Stogram
from nft_marker_generator import NFTMarkerGenerator, NFTMarkerConfig

logger = get_logger(__name__)

# Load environment variables
load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


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
    return f"{BASE_URL}/ar/{os.path.basename(image_url).split('.')[0]}"


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
        
        # Create a temporary directory for the generator
        temp_dir_obj = tempfile.TemporaryDirectory()
        temp_storage_root = Path(temp_dir_obj.name)
        
        # Initialize the NFT marker generator with temporary storage
        generator = NFTMarkerGenerator(temp_storage_root)
        
        # Get the image filename without extension for naming the marker files
        input_image_path = Path(input_image_path)
        output_name = input_image_path.stem
        
        # Generate the NFT marker using the enhanced generator from Stogram
        logger.info(f"Generating NFT marker for {input_image_path} with name {output_name}")
        marker = generator.generate_marker(input_image_path, output_name, config)
        logger.info(f"NFT marker generated successfully: {marker.fset_path}, {marker.fset3_path}, {marker.iset_path}")
        
        # Copy generated files to output directory
        generated_files = [
            (Path(marker.fset_path), output_root / f"{output_name}.fset"),
            (Path(marker.fset3_path), output_root / f"{output_name}.fset3"),
            (Path(marker.iset_path), output_root / f"{output_name}.iset")
        ]
        
        for src_path, dest_path in generated_files:
            if src_path.exists():
                shutil.copy2(src_path, dest_path)
                logger.info(f"Copied {src_path.name} to {dest_path}")
            else:
                logger.error(f"Expected marker file not found: {src_path}")
                temp_dir_obj.cleanup()
                return False
        
        # Copy source image to output directory
        image_extension = input_image_path.suffix or ".jpg"
        image_destination = output_root / f"{output_name}{image_extension}"
        shutil.copy2(input_image_path, image_destination)
        logger.info(f"Copied source image to {image_destination}")
        
        # Clean up temporary directory
        temp_dir_obj.cleanup()
        
        # If requested, save files to MinIO
        if save_to_minio:
            logger.info("Uploading NFT marker files to MinIO...")
            marker_files = [f"{output_name}.fset", f"{output_name}.fset3", f"{output_name}.iset"]
            for marker_file in marker_files:
                file_path = output_root / marker_file
                if file_path.exists():
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    # Upload to MinIO with nft-markers prefix
                    object_name = f"nft-markers/{marker_file}"
                    upload_url = upload_file(file_content, object_name, "application/octet-stream")
                    if upload_url:
                        logger.info(f"Uploaded {marker_file} to MinIO: {upload_url}")
                    else:
                        logger.error(f"Failed to upload {marker_file} to MinIO")
                else:
                    logger.error(f"Marker file does not exist: {file_path}")
        
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
