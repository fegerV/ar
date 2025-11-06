import os
import shutil

# Assuming nft_maker.py is in the parent directory
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nft_maker import generate_nft_marker


class TestNFTGeneration(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

        # Create a sample image for testing
        self.sample_image_path = os.path.join(self.test_dir, "test_image.jpg")
        self.create_sample_image(self.sample_image_path)

        # Output directory for generated markers
        self.output_dir = os.path.join(self.test_dir, "markers")

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.test_dir)

    def create_sample_image(self, path):
        """Create a sample image for testing."""
        # Create a 500x500 blue image (minimum 480x480 required for NFT markers)
        image = np.zeros((500, 500, 3), dtype=np.uint8)
        image[:, :] = [255, 0, 0]  # Blue in BGR format

        # Add some shapes to make it more interesting
        cv2.rectangle(image, (50, 50), (450, 450), (0, 255, 0), 3)  # Green rectangle
        cv2.circle(image, (250, 250), 125, (0, 0, 255), 3)  # Red circle

        # Save the image
        cv2.imwrite(path, image)

    def test_generate_nft_marker_success(self):
        """Test successful NFT marker generation."""
        # Run the NFT marker generation
        result = generate_nft_marker(self.sample_image_path, self.output_dir)

        # Check that the function returned True (success)
        self.assertTrue(result)

        # Check that output directory was created
        self.assertTrue(os.path.exists(self.output_dir))
        self.assertTrue(os.path.isdir(self.output_dir))

        # Check that marker files were created
        marker_name = Path(self.sample_image_path).stem
        expected_files = [f"{marker_name}.jpg", f"{marker_name}.iset", f"{marker_name}.fset", f"{marker_name}.fset3"]

        for filename in expected_files:
            file_path = os.path.join(self.output_dir, filename)
            self.assertTrue(os.path.exists(file_path), f"Expected file {filename} was not created")

    def test_generate_nft_marker_invalid_input(self):
        """Test NFT marker generation with invalid input."""
        # Try to generate marker with non-existent input file
        invalid_path = os.path.join(self.test_dir, "non_existent.jpg")
        result = generate_nft_marker(invalid_path, self.output_dir)

        # Check that the function returned False (failure)
        self.assertFalse(result)

    def test_generate_nft_marker_output_files_content(self):
        """Test content of generated NFT marker files."""
        # Run the NFT marker generation
        result = generate_nft_marker(self.sample_image_path, self.output_dir)
        self.assertTrue(result)

        # Check that .iset file exists and has content
        marker_name = Path(self.sample_image_path).stem
        iset_path = os.path.join(self.output_dir, f"{marker_name}.iset")
        self.assertTrue(os.path.exists(iset_path))

        with open(iset_path, "rb") as f:
            iset_content = f.read()

        # Check that .iset file is not empty and starts with expected magic number
        self.assertGreater(len(iset_content), 0)
        self.assertTrue(iset_content.startswith(b"ARIS"))

        # Check content of .fset file
        fset_path = os.path.join(self.output_dir, f"{marker_name}.fset")
        self.assertTrue(os.path.exists(fset_path))

        with open(fset_path, "rb") as f:
            fset_content = f.read()

        # Check that .fset file is not empty and starts with expected magic number
        self.assertGreater(len(fset_content), 0)
        self.assertTrue(fset_content.startswith(b"ARJS"))

        # Check content of .fset3 file
        fset3_path = os.path.join(self.output_dir, f"{marker_name}.fset3")
        self.assertTrue(os.path.exists(fset3_path))

        with open(fset3_path, "rb") as f:
            fset3_content = f.read()

        # Check that .fset3 file is not empty and starts with expected magic number
        self.assertGreater(len(fset3_content), 0)
        self.assertTrue(fset3_content.startswith(b"AR3D"))


if __name__ == "__main__":
    unittest.main()
