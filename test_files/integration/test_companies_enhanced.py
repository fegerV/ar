"""
Integration tests for enhanced company API with full CRUD, pagination, and categories.
"""
import sys
import tempfile
from pathlib import Path

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "vertex-ar"))

from app.database import Database


def test_company_update():
    """Test updating company fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company
        db.create_company("company-1", "Test Company", storage_type="local")
        
        # Update company fields
        success = db.update_company(
            "company-1",
            name="Updated Company",
            storage_folder_path="new_folder"
        )
        assert success
        
        # Retrieve and verify
        company = db.get_company("company-1")
        assert company["name"] == "Updated Company"
        assert company["storage_folder_path"] == "new_folder"
        print("✓ Company update test passed")


def test_company_pagination():
    """Test paginated company listing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create multiple companies
        for i in range(15):
            db.create_company(f"company-{i}", f"Company {i}")
        
        # Get first page
        page1 = db.list_companies_paginated(limit=10, offset=0)
        assert len(page1) == 10
        
        # Get second page
        page2 = db.list_companies_paginated(limit=10, offset=10)
        assert len(page2) == 6  # 15 companies + 1 default = 16 total, page2 has 6
        
        print("✓ Company pagination test passed")


def test_company_filtering():
    """Test filtering companies by search and storage type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create companies with different storage types
        db.create_company("company-1", "Acme Corp", storage_type="local")
        db.create_company("company-2", "Beta LLC", storage_type="local_disk")
        db.create_company("company-3", "Acme Industries", storage_type="local")
        
        # Filter by search
        results = db.list_companies_paginated(search="Acme")
        names = [c["name"] for c in results]
        assert "Acme Corp" in names
        assert "Acme Industries" in names
        assert "Beta LLC" not in names
        
        # Filter by storage type
        results = db.list_companies_paginated(storage_type="local")
        assert len(results) == 2
        
        # Count filtered results
        count = db.count_companies_filtered(search="Acme")
        assert count == 2
        
        print("✓ Company filtering test passed")


def test_category_creation():
    """Test creating categories for a company."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company
        db.create_company("company-1", "Test Company")
        
        # Create a category
        category = db.create_category(
            category_id="cat-1",
            company_id="company-1",
            name="Portraits",
            slug="portraits",
            description="Portrait category"
        )
        
        assert category["id"] == "cat-1"
        assert category["name"] == "Portraits"
        assert category["slug"] == "portraits"
        assert category["description"] == "Portrait category"
        print("✓ Category creation test passed")


def test_category_slug_uniqueness():
    """Test that category slugs must be unique within a company."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company
        db.create_company("company-1", "Test Company")
        
        # Create first category
        db.create_category("cat-1", "company-1", "Portraits", "portraits")
        
        # Try to create another category with same slug
        try:
            db.create_category("cat-2", "company-1", "Portraits 2", "portraits")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already_exists" in str(e)
        
        print("✓ Category slug uniqueness test passed")


def test_category_slug_across_companies():
    """Test that category slugs can be reused across different companies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create two companies
        db.create_company("company-1", "Company 1")
        db.create_company("company-2", "Company 2")
        
        # Create category with same slug in each company
        cat1 = db.create_category("cat-1", "company-1", "Portraits", "portraits")
        cat2 = db.create_category("cat-2", "company-2", "Portraits", "portraits")
        
        assert cat1["slug"] == "portraits"
        assert cat2["slug"] == "portraits"
        assert cat1["company_id"] == "company-1"
        assert cat2["company_id"] == "company-2"
        
        print("✓ Category slug across companies test passed")


def test_list_categories():
    """Test listing categories for a company."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company
        db.create_company("company-1", "Test Company")
        
        # Create categories
        db.create_category("cat-1", "company-1", "Portraits", "portraits")
        db.create_category("cat-2", "company-1", "Diplomas", "diplomas")
        db.create_category("cat-3", "company-1", "Certificates", "certificates")
        
        # List categories
        categories = db.list_categories("company-1")
        assert len(categories) == 3
        
        slugs = [c["slug"] for c in categories]
        assert "portraits" in slugs
        assert "diplomas" in slugs
        assert "certificates" in slugs
        
        print("✓ List categories test passed")


def test_category_pagination():
    """Test paginated category listing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company
        db.create_company("company-1", "Test Company")
        
        # Create multiple categories
        for i in range(15):
            db.create_category(f"cat-{i}", "company-1", f"Category {i}", f"cat-{i}")
        
        # Get first page
        page1 = db.list_categories("company-1", limit=10, offset=0)
        assert len(page1) == 10
        
        # Get second page
        page2 = db.list_categories("company-1", limit=10, offset=10)
        assert len(page2) == 5
        
        # Count total
        total = db.count_categories("company-1")
        assert total == 15
        
        print("✓ Category pagination test passed")


def test_get_category_by_slug():
    """Test getting a category by its slug."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company
        db.create_company("company-1", "Test Company")
        
        # Create a category
        db.create_category("cat-1", "company-1", "Portraits", "portraits")
        
        # Get by slug
        category = db.get_category_by_slug("company-1", "portraits")
        assert category is not None
        assert category["id"] == "cat-1"
        assert category["name"] == "Portraits"
        
        # Non-existent slug
        category = db.get_category_by_slug("company-1", "nonexistent")
        assert category is None
        
        print("✓ Get category by slug test passed")


def test_rename_category():
    """Test renaming a category."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company and category
        db.create_company("company-1", "Test Company")
        db.create_category("cat-1", "company-1", "Portraits", "portraits")
        
        # Rename category
        success = db.rename_category("cat-1", "Updated Portraits", "updated-portraits")
        assert success
        
        # Verify
        category = db.get_project("cat-1")
        assert category["name"] == "Updated Portraits"
        assert category["slug"] == "updated-portraits"
        
        print("✓ Rename category test passed")


def test_delete_category():
    """Test deleting a category."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company and category
        db.create_company("company-1", "Test Company")
        db.create_category("cat-1", "company-1", "Portraits", "portraits")
        
        # Delete category
        success = db.delete_category("cat-1")
        assert success
        
        # Verify it's gone
        category = db.get_project("cat-1")
        assert category is None
        
        print("✓ Delete category test passed")


def test_category_folder_assignment():
    """Test assigning portraits to category folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company, client, and category
        db.create_company("company-1", "Test Company")
        db.create_client("client-1", "79990001111", "Client 1", "company-1")
        db.create_category("cat-1", "company-1", "Portraits", "portraits")
        
        # Create a folder in the category
        db.create_folder("folder-1", "cat-1", "Folder 1")
        
        # Create a portrait
        portrait = db.create_portrait(
            portrait_id="portrait-1",
            client_id="client-1",
            image_path="/path/to/image.jpg",
            marker_fset="fset",
            marker_fset3="fset3",
            marker_iset="iset",
            permanent_link="https://example.com/ar/1"
        )
        
        # Assign portrait to category folder
        success = db.assign_category_folder("portrait-1", "folder-1")
        assert success
        
        # Verify assignment
        portrait = db.get_portrait("portrait-1")
        assert portrait["folder_id"] == "folder-1"
        
        print("✓ Category folder assignment test passed")


def test_company_count_filtered():
    """Test counting filtered companies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create companies
        db.create_company("company-1", "Acme Corp", storage_type="local")
        db.create_company("company-2", "Beta LLC", storage_type="local_disk")
        db.create_company("company-3", "Acme Industries", storage_type="local")
        
        # Count all
        total = db.count_companies_filtered()
        assert total == 4  # 3 created + 1 default
        
        # Count with search
        count = db.count_companies_filtered(search="Acme")
        assert count == 2
        
        # Count with storage type
        count = db.count_companies_filtered(storage_type="local")
        assert count == 2
        
        # Count with both filters
        count = db.count_companies_filtered(search="Acme", storage_type="local")
        assert count == 2
        
        print("✓ Company count filtered test passed")


if __name__ == "__main__":
    test_company_update()
    test_company_pagination()
    test_company_filtering()
    test_category_creation()
    test_category_slug_uniqueness()
    test_category_slug_across_companies()
    test_list_categories()
    test_category_pagination()
    test_get_category_by_slug()
    test_rename_category()
    test_delete_category()
    test_category_folder_assignment()
    test_company_count_filtered()
    print("\n✅ All enhanced company tests passed!")
