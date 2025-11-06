import os
import sys
import unittest
from datetime import datetime

from pydantic import ValidationError

# Add the parent directory to the path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import AREntry, AREntryBase, AREntryCreate, AREntryInDB, AREntryInDBBase, AREntryUpdate


class TestModels(unittest.TestCase):
    def test_ar_entry_base(self):
        """Test AREntryBase model creation with valid data."""
        data = {"image_key": "test_image.jpg", "video_key": "test_video.mp4", "nft_prefix": "test_nft"}

        entry = AREntryBase(**data)

        self.assertEqual(entry.image_key, "test_image.jpg")
        self.assertEqual(entry.video_key, "test_video.mp4")
        self.assertEqual(entry.nft_prefix, "test_nft")

    def test_ar_entry_base_required_fields(self):
        """Test that AREntryBase requires all fields."""
        # Missing image_key
        with self.assertRaises(ValidationError):
            AREntryBase(video_key="test_video.mp4", nft_prefix="test_nft")

        # Missing video_key
        with self.assertRaises(ValidationError):
            AREntryBase(image_key="test_image.jpg", nft_prefix="test_nft")

        # Missing nft_prefix
        with self.assertRaises(ValidationError):
            AREntryBase(image_key="test_image.jpg", video_key="test_video.mp4")

    def test_ar_entry_create(self):
        """Test AREntryCreate model (should be same as base)."""
        data = {"image_key": "test_image.jpg", "video_key": "test_video.mp4", "nft_prefix": "test_nft"}

        entry = AREntryCreate(**data)

        self.assertEqual(entry.image_key, "test_image.jpg")
        self.assertEqual(entry.video_key, "test_video.mp4")
        self.assertEqual(entry.nft_prefix, "test_nft")

    def test_ar_entry_update_partial(self):
        """Test AREntryUpdate model with partial data."""
        # Update only image_key
        update_data = {"image_key": "updated_image.jpg"}
        update = AREntryUpdate(**update_data)
        self.assertEqual(update.image_key, "updated_image.jpg")
        self.assertIsNone(update.video_key)
        self.assertIsNone(update.nft_prefix)
        self.assertIsNone(update.status)

        # Update only status
        update_data = {"status": "inactive"}
        update = AREntryUpdate(**update_data)
        self.assertEqual(update.status, "inactive")
        self.assertIsNone(update.image_key)
        self.assertIsNone(update.video_key)
        self.assertIsNone(update.nft_prefix)

    def test_ar_entry_update_all_fields(self):
        """Test AREntryUpdate model with all optional fields."""
        update_data = {
            "image_key": "updated_image.jpg",
            "video_key": "updated_video.mp4",
            "nft_prefix": "updated_nft",
            "status": "inactive",
        }

        update = AREntryUpdate(**update_data)

        self.assertEqual(update.image_key, "updated_image.jpg")
        self.assertEqual(update.video_key, "updated_video.mp4")
        self.assertEqual(update.nft_prefix, "updated_nft")
        self.assertEqual(update.status, "inactive")

    def test_ar_entry_in_db_base(self):
        """Test AREntryInDBBase model with required database fields."""
        data = {
            "id": 1,
            "uuid": "test-uuid-123",
            "image_key": "test_image.jpg",
            "video_key": "test_video.mp4",
            "nft_prefix": "test_nft",
            "created_at": datetime.now(),
            "status": "active",
        }

        entry = AREntryInDBBase(**data)

        self.assertEqual(entry.id, 1)
        self.assertEqual(entry.uuid, "test-uuid-123")
        self.assertEqual(entry.image_key, "test_image.jpg")
        self.assertEqual(entry.video_key, "test_video.mp4")
        self.assertEqual(entry.nft_prefix, "test_nft")
        self.assertEqual(entry.status, "active")

    def test_ar_entry_in_db_base_required_fields(self):
        """Test that AREntryInDBBase requires all database fields."""
        base_data = {
            "id": 1,
            "uuid": "test-uuid-123",
            "image_key": "test_image.jpg",
            "video_key": "test_video.mp4",
            "nft_prefix": "test_nft",
            "created_at": datetime.now(),
            "status": "active",
        }

        # Test that all required fields are needed
        required_fields = ["id", "uuid", "image_key", "video_key", "nft_prefix", "created_at", "status"]

        for field in required_fields:
            partial_data = {k: v for k, v in base_data.items() if k != field}
            with self.assertRaises(ValidationError):
                AREntryInDBBase(**partial_data)

    def test_ar_entry_model(self):
        """Test AREntry model (should be same as AREntryInDBBase)."""
        data = {
            "id": 1,
            "uuid": "test-uuid-123",
            "image_key": "test_image.jpg",
            "video_key": "test_video.mp4",
            "nft_prefix": "test_nft",
            "created_at": datetime.now(),
            "status": "active",
        }

        entry = AREntry(**data)

        self.assertEqual(entry.id, 1)
        self.assertEqual(entry.uuid, "test-uuid-123")
        self.assertEqual(entry.image_key, "test_image.jpg")
        self.assertEqual(entry.video_key, "test_video.mp4")
        self.assertEqual(entry.nft_prefix, "test_nft")
        self.assertEqual(entry.status, "active")

    def test_ar_entry_in_db_model(self):
        """Test AREntryInDB model (should be same as AREntryInDBBase)."""
        data = {
            "id": 1,
            "uuid": "test-uuid-123",
            "image_key": "test_image.jpg",
            "video_key": "test_video.mp4",
            "nft_prefix": "test_nft",
            "created_at": datetime.now(),
            "status": "active",
        }

        entry = AREntryInDB(**data)

        self.assertEqual(entry.id, 1)
        self.assertEqual(entry.uuid, "test-uuid-123")
        self.assertEqual(entry.image_key, "test_image.jpg")
        self.assertEqual(entry.video_key, "test_video.mp4")
        self.assertEqual(entry.nft_prefix, "test_nft")
        self.assertEqual(entry.status, "active")


if __name__ == "__main__":
    unittest.main()
