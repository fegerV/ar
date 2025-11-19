"""
Tests for company management functionality.
"""
import tempfile
from pathlib import Path
from app.database import Database


def test_company_creation():
    """Test creating a company."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company
        db.create_company("company-1", "Test Company")
        
        # Retrieve it
        company = db.get_company("company-1")
        assert company is not None
        assert company["id"] == "company-1"
        assert company["name"] == "Test Company"
        print("✓ Company creation test passed")


def test_default_company_creation():
    """Test that default company is created automatically."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Check that default company exists
        default_company = db.get_company("vertex-ar-default")
        assert default_company is not None
        assert default_company["name"] == "Vertex AR"
        print("✓ Default company creation test passed")


def test_list_companies():
    """Test listing companies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create companies
        db.create_company("company-1", "Company 1")
        db.create_company("company-2", "Company 2")
        
        # List them
        companies = db.list_companies()
        assert len(companies) == 3  # Default + 2 new
        names = [c["name"] for c in companies]
        assert "Vertex AR" in names
        assert "Company 1" in names
        assert "Company 2" in names
        print("✓ List companies test passed")


def test_delete_company():
    """Test deleting a company."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create and delete a company
        db.create_company("company-delete", "Delete Me")
        success = db.delete_company("company-delete")
        assert success
        
        # Verify it's gone
        company = db.get_company("company-delete")
        assert company is None
        print("✓ Delete company test passed")


def test_get_company_by_name():
    """Test getting company by name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company
        db.create_company("company-1", "Unique Name")
        
        # Get by name
        company = db.get_company_by_name("Unique Name")
        assert company is not None
        assert company["id"] == "company-1"
        print("✓ Get company by name test passed")


def test_company_unique_name():
    """Test that company names must be unique."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create a company
        db.create_company("company-1", "Duplicate")
        
        # Try to create another with same name
        try:
            db.create_company("company-2", "Duplicate")
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✓ Company unique name test passed")


def test_companies_with_client_count():
    """Test getting companies with client count."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create companies
        db.create_company("company-1", "Company 1")
        db.create_company("company-2", "Company 2")
        
        # Create clients for each
        db.create_client("client-1", "79990001111", "Client 1", "company-1")
        db.create_client("client-2", "79990002222", "Client 2", "company-1")
        db.create_client("client-3", "79990003333", "Client 3", "company-2")
        
        # Get companies with counts
        companies = db.get_companies_with_client_count()
        
        # Find our companies and check counts
        company1 = next((c for c in companies if c["id"] == "company-1"), None)
        company2 = next((c for c in companies if c["id"] == "company-2"), None)
        
        assert company1 is not None
        assert company1["client_count"] == 2
        assert company2 is not None
        assert company2["client_count"] == 1
        print("✓ Companies with client count test passed")


def test_client_company_filtering():
    """Test that clients are correctly filtered by company."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create companies
        db.create_company("company-1", "Company 1")
        db.create_company("company-2", "Company 2")
        
        # Create clients with same phone in different companies
        db.create_client("client-1", "79990001111", "Client 1", "company-1")
        db.create_client("client-2", "79990001111", "Client 2", "company-2")  # Same phone, different company
        
        # Get by phone and company
        client1 = db.get_client_by_phone("79990001111", "company-1")
        client2 = db.get_client_by_phone("79990001111", "company-2")
        
        assert client1 is not None
        assert client1["id"] == "client-1"
        assert client2 is not None
        assert client2["id"] == "client-2"
        print("✓ Client company filtering test passed")


def test_cascade_delete():
    """Test that deleting a company deletes all its data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        # Create company with client
        db.create_company("company-cascade", "Company to Delete")
        db.create_client("client-cascade", "79990001111", "Client", "company-cascade")
        
        # Verify client exists
        client = db.get_client("client-cascade")
        assert client is not None
        
        # Delete company
        db.delete_company("company-cascade")
        
        # Verify client is gone
        client = db.get_client("client-cascade")
        assert client is None
        print("✓ Cascade delete test passed")


if __name__ == "__main__":
    test_company_creation()
    test_default_company_creation()
    test_list_companies()
    test_delete_company()
    test_get_company_by_name()
    test_company_unique_name()
    test_companies_with_client_count()
    test_client_company_filtering()
    test_cascade_delete()
    print("\n✓ All company tests passed!")
