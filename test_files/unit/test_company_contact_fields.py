"""
Tests for company contact fields extension.
"""
import json
import pytest
import tempfile
from pathlib import Path
from app.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    db = Database(db_path)
    yield db
    
    # Cleanup
    db_path.unlink(missing_ok=True)


class TestCompanyContactFields:
    """Test cases for company contact fields."""
    
    def test_default_company_has_contact_fields(self, temp_db):
        """Test that default company 'Vertex AR' is created with contact metadata."""
        company = temp_db.get_company_by_name("Vertex AR")
        
        assert company is not None
        assert company["name"] == "Vertex AR"
        assert company["email"] == "contact@vertex-ar.com"
        assert company["description"] == "Default company for Vertex AR platform"
        assert company["city"] == "Moscow"
        assert company["phone"] == "+7 (495) 000-00-00"
        assert company["website"] == "https://vertex-ar.com"
        assert company["manager_name"] == "System Administrator"
        assert company["manager_phone"] == "+7 (495) 000-00-00"
        assert company["manager_email"] == "admin@vertex-ar.com"
    
    def test_companies_table_has_new_columns(self, temp_db):
        """Test that companies table has all new contact columns."""
        cursor = temp_db._execute("PRAGMA table_info(companies)")
        columns = [row[1] for row in cursor.fetchall()]
        
        expected_columns = [
            'email', 'description', 'city', 'phone', 'website',
            'social_links', 'manager_name', 'manager_phone', 'manager_email'
        ]
        
        for col in expected_columns:
            assert col in columns, f"Column '{col}' not found in companies table"
    
    def test_create_company_with_contact_fields(self, temp_db):
        """Test creating company with contact fields."""
        social_links_json = json.dumps({
            "facebook": "https://facebook.com/testcompany",
            "twitter": "https://twitter.com/testcompany"
        })
        
        temp_db.create_company(
            company_id="test-company-1",
            name="Test Company",
            storage_type="local_disk",
            email="info@testcompany.com",
            description="A test company",
            city="New York",
            phone="+1 (555) 123-4567",
            website="https://testcompany.com",
            social_links=social_links_json,
            manager_name="John Manager",
            manager_phone="+1 (555) 987-6543",
            manager_email="john@testcompany.com"
        )
        
        company = temp_db.get_company("test-company-1")
        assert company is not None
        assert company["name"] == "Test Company"
        assert company["email"] == "info@testcompany.com"
        assert company["description"] == "A test company"
        assert company["city"] == "New York"
        assert company["phone"] == "+1 (555) 123-4567"
        assert company["website"] == "https://testcompany.com"
        assert company["social_links"] == social_links_json
        assert company["manager_name"] == "John Manager"
        assert company["manager_phone"] == "+1 (555) 987-6543"
        assert company["manager_email"] == "john@testcompany.com"
    
    def test_create_company_without_contact_fields(self, temp_db):
        """Test creating company without optional contact fields."""
        temp_db.create_company(
            company_id="test-company-2",
            name="Minimal Company",
            storage_type="local_disk"
        )
        
        company = temp_db.get_company("test-company-2")
        assert company is not None
        assert company["name"] == "Minimal Company"
        assert company.get("email") is None
        assert company.get("description") is None
        assert company.get("city") is None
        assert company.get("phone") is None
        assert company.get("website") is None
        assert company.get("social_links") is None
        assert company.get("manager_name") is None
        assert company.get("manager_phone") is None
        assert company.get("manager_email") is None
    
    def test_update_company_contact_fields(self, temp_db):
        """Test updating company contact fields."""
        temp_db.create_company(
            company_id="test-company-3",
            name="Update Test Company",
            storage_type="local_disk"
        )
        
        # Update contact fields
        success = temp_db.update_company(
            company_id="test-company-3",
            email="updated@test.com",
            description="Updated description",
            city="San Francisco",
            phone="+1 (555) 000-0000",
            website="https://updated.com",
            manager_name="Jane Manager",
            manager_phone="+1 (555) 111-1111",
            manager_email="jane@updated.com"
        )
        
        assert success is True
        
        company = temp_db.get_company("test-company-3")
        assert company["email"] == "updated@test.com"
        assert company["description"] == "Updated description"
        assert company["city"] == "San Francisco"
        assert company["phone"] == "+1 (555) 000-0000"
        assert company["website"] == "https://updated.com"
        assert company["manager_name"] == "Jane Manager"
        assert company["manager_phone"] == "+1 (555) 111-1111"
        assert company["manager_email"] == "jane@updated.com"
    
    def test_update_company_partial_contact_fields(self, temp_db):
        """Test partially updating contact fields."""
        temp_db.create_company(
            company_id="test-company-4",
            name="Partial Update Company",
            storage_type="local_disk",
            email="original@test.com",
            city="Boston"
        )
        
        # Update only some fields
        success = temp_db.update_company(
            company_id="test-company-4",
            city="Chicago",
            phone="+1 (555) 222-2222"
        )
        
        assert success is True
        
        company = temp_db.get_company("test-company-4")
        assert company["email"] == "original@test.com"  # Unchanged
        assert company["city"] == "Chicago"  # Changed
        assert company["phone"] == "+1 (555) 222-2222"  # Changed
    
    def test_get_companies_with_client_count_includes_contact_fields(self, temp_db):
        """Test that get_companies_with_client_count returns contact fields."""
        temp_db.create_company(
            company_id="test-company-5",
            name="List Test Company",
            storage_type="local_disk",
            email="list@test.com",
            city="Seattle"
        )
        
        companies = temp_db.get_companies_with_client_count()
        
        # Find our test company in the list
        test_company = next((c for c in companies if c["id"] == "test-company-5"), None)
        assert test_company is not None
        assert test_company["email"] == "list@test.com"
        assert test_company["city"] == "Seattle"
        assert "client_count" in test_company
    
    def test_list_companies_paginated_includes_contact_fields(self, temp_db):
        """Test that paginated listing includes contact fields."""
        temp_db.create_company(
            company_id="test-company-6",
            name="Paginated Test Company",
            storage_type="local_disk",
            email="paginated@test.com",
            description="Paginated test"
        )
        
        companies = temp_db.list_companies_paginated(limit=10, offset=0)
        
        # Find our test company in the list
        test_company = next((c for c in companies if c["id"] == "test-company-6"), None)
        assert test_company is not None
        assert test_company["email"] == "paginated@test.com"
        assert test_company["description"] == "Paginated test"
    
    def test_social_links_json_format(self, temp_db):
        """Test that social_links handles JSON correctly."""
        social_links = {
            "facebook": "https://facebook.com/company",
            "twitter": "https://twitter.com/company",
            "linkedin": "https://linkedin.com/company/company"
        }
        social_links_json = json.dumps(social_links)
        
        temp_db.create_company(
            company_id="test-company-7",
            name="Social Test Company",
            storage_type="local_disk",
            social_links=social_links_json
        )
        
        company = temp_db.get_company("test-company-7")
        assert company["social_links"] == social_links_json
        
        # Verify we can parse it back
        parsed_links = json.loads(company["social_links"])
        assert parsed_links == social_links
    
    def test_backward_compatibility(self, temp_db):
        """Test that existing code without contact fields still works."""
        # Create company using only original fields
        temp_db.create_company(
            company_id="test-company-8",
            name="Legacy Company",
            storage_type="local_disk"
        )
        
        company = temp_db.get_company("test-company-8")
        assert company is not None
        assert company["name"] == "Legacy Company"
        
        # Update using only original fields
        success = temp_db.update_company(
            company_id="test-company-8",
            name="Updated Legacy Company"
        )
        assert success is True
        
        updated = temp_db.get_company("test-company-8")
        assert updated["name"] == "Updated Legacy Company"
