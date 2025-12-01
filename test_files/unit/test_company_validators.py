"""
Tests for company contact field validators.
"""
import json
import pytest
from pydantic import ValidationError
from app.models import CompanyCreate, CompanyUpdate
from app.validators import validate_social_links


class TestCompanyValidators:
    """Test cases for company field validators."""
    
    def test_valid_email(self):
        """Test valid email validation."""
        company = CompanyCreate(
            name="Test Company",
            email="test@example.com"
        )
        assert company.email == "test@example.com"
    
    def test_invalid_email(self):
        """Test invalid email raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyCreate(
                name="Test Company",
                email="invalid-email"
            )
        assert "email" in str(exc_info.value).lower()
    
    def test_valid_phone(self):
        """Test valid phone validation."""
        company = CompanyCreate(
            name="Test Company",
            phone="+1 (555) 123-4567"
        )
        assert company.phone == "+1 (555) 123-4567"
    
    def test_invalid_phone_too_short(self):
        """Test invalid phone (too short) raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyCreate(
                name="Test Company",
                phone="123"
            )
        assert "phone" in str(exc_info.value).lower()
    
    def test_valid_website(self):
        """Test valid website URL validation."""
        company = CompanyCreate(
            name="Test Company",
            website="https://example.com"
        )
        assert company.website == "https://example.com"
    
    def test_invalid_website(self):
        """Test invalid website URL raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyCreate(
                name="Test Company",
                website="not-a-url"
            )
        assert "website" in str(exc_info.value).lower() or "url" in str(exc_info.value).lower()
    
    def test_valid_social_links_dict(self):
        """Test valid social links as dict."""
        social_links = {
            "facebook": "https://facebook.com/company",
            "twitter": "https://twitter.com/company"
        }
        social_links_json = json.dumps(social_links)
        
        company = CompanyCreate(
            name="Test Company",
            social_links=social_links_json
        )
        assert company.social_links == social_links_json
    
    def test_valid_social_links_json_string(self):
        """Test valid social links as JSON string."""
        social_links_json = '{"linkedin": "https://linkedin.com/company/test"}'
        
        company = CompanyCreate(
            name="Test Company",
            social_links=social_links_json
        )
        assert company.social_links == social_links_json
    
    def test_invalid_social_links_json(self):
        """Test invalid JSON in social_links raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyCreate(
                name="Test Company",
                social_links="not valid json"
            )
        assert "social" in str(exc_info.value).lower() or "json" in str(exc_info.value).lower()
    
    def test_invalid_social_links_url(self):
        """Test invalid URL in social_links raises validation error."""
        invalid_social_links = json.dumps({
            "facebook": "not-a-valid-url"
        })
        
        with pytest.raises(ValidationError) as exc_info:
            CompanyCreate(
                name="Test Company",
                social_links=invalid_social_links
            )
        assert "social" in str(exc_info.value).lower() or "url" in str(exc_info.value).lower()
    
    def test_valid_manager_email(self):
        """Test valid manager email validation."""
        company = CompanyCreate(
            name="Test Company",
            manager_email="manager@example.com"
        )
        assert company.manager_email == "manager@example.com"
    
    def test_invalid_manager_email(self):
        """Test invalid manager email raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyCreate(
                name="Test Company",
                manager_email="invalid@"
            )
        assert "email" in str(exc_info.value).lower()
    
    def test_valid_manager_phone(self):
        """Test valid manager phone validation."""
        company = CompanyCreate(
            name="Test Company",
            manager_phone="+1 (555) 987-6543"
        )
        assert company.manager_phone == "+1 (555) 987-6543"
    
    def test_valid_city_and_manager_name(self):
        """Test valid city and manager name validation."""
        company = CompanyCreate(
            name="Test Company",
            city="New York",
            manager_name="John Manager"
        )
        assert company.city == "New York"
        assert company.manager_name == "John Manager"
    
    def test_empty_string_fields_handled(self):
        """Test that empty string fields are handled correctly."""
        company = CompanyCreate(
            name="Test Company",
            email="",
            phone="",
            website=""
        )
        # Empty strings should be accepted without validation
        assert company.email == ""
        assert company.phone == ""
        assert company.website == ""
    
    def test_company_update_validators(self):
        """Test validators work for CompanyUpdate model."""
        update = CompanyUpdate(
            email="updated@example.com",
            phone="+1 (555) 000-0000",
            website="https://updated.com"
        )
        assert update.email == "updated@example.com"
        assert update.phone == "+1 (555) 000-0000"
        assert update.website == "https://updated.com"
    
    def test_company_update_invalid_email(self):
        """Test CompanyUpdate with invalid email raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyUpdate(
                email="invalid-email-format"
            )
        assert "email" in str(exc_info.value).lower()
    
    def test_social_links_validator_function(self):
        """Test validate_social_links function directly."""
        # Valid dict input
        social_dict = {"twitter": "https://twitter.com/test"}
        result = validate_social_links(social_dict)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == social_dict
        
        # Valid JSON string input
        social_json = '{"facebook": "https://facebook.com/test"}'
        result = validate_social_links(social_json)
        assert isinstance(result, str)
        
        # Invalid: not a dict or JSON
        with pytest.raises(ValueError) as exc_info:
            validate_social_links(["not", "a", "dict"])
        assert "dict" in str(exc_info.value).lower() or "json" in str(exc_info.value).lower()
        
        # Invalid: empty platform name
        with pytest.raises(ValueError) as exc_info:
            validate_social_links({"": "https://test.com"})
        assert "platform" in str(exc_info.value).lower()
        
        # Invalid: empty URL
        with pytest.raises(ValueError) as exc_info:
            validate_social_links({"twitter": ""})
        
        # Invalid: bad URL format
        with pytest.raises(ValueError) as exc_info:
            validate_social_links({"twitter": "not-a-url"})
        assert "url" in str(exc_info.value).lower()
    
    def test_all_contact_fields_together(self):
        """Test creating company with all contact fields."""
        social_links_json = json.dumps({
            "facebook": "https://facebook.com/company",
            "twitter": "https://twitter.com/company",
            "linkedin": "https://linkedin.com/company/company"
        })
        
        company = CompanyCreate(
            name="Full Contact Company",
            storage_type="local_disk",
            email="info@fullcontact.com",
            description="A company with all contact fields",
            city="San Francisco",
            phone="+1 (415) 555-1234",
            website="https://fullcontact.com",
            social_links=social_links_json,
            manager_name="Jane Doe",
            manager_phone="+1 (415) 555-5678",
            manager_email="jane@fullcontact.com"
        )
        
        assert company.name == "Full Contact Company"
        assert company.email == "info@fullcontact.com"
        assert company.description == "A company with all contact fields"
        assert company.city == "San Francisco"
        assert company.phone == "+1 (415) 555-1234"
        assert company.website == "https://fullcontact.com"
        assert company.social_links == social_links_json
        assert company.manager_name == "Jane Doe"
        assert company.manager_phone == "+1 (415) 555-5678"
        assert company.manager_email == "jane@fullcontact.com"
