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
        
        # Initialize the NFT marker generator with the output directory as storage root
        generator = NFTMarkerGenerator(Path(output_dir))
        
        # Get the image filename without extension for naming the marker files
        output_name = Path(input_image_path).stem
        
        # Generate the NFT marker using the enhanced generator from Stogram
        logger.info(f"Generating NFT marker for {input_image_path} with name {output_name}")
        marker = generator.generate_marker(input_image_path, output_name, config)
        logger.info(f"NFT marker generated successfully: {marker.fset_path}, {marker.fset3_path}, {marker.iset_path}")
        
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