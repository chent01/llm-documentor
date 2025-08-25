"""
Unit tests for SOUP service.
"""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch

from medical_analyzer.models.core import SOUPComponent
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.database.schema import DatabaseManager


class TestSOUPService:
    """Test cases for SOUPService."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def db_manager(self, temp_db):
        """Create a database manager with temporary database."""
        return DatabaseManager(temp_db)
    
    @pytest.fixture
    def soup_service(self, db_manager):
        """Create a SOUP service instance."""
        return SOUPService(db_manager)
    
    @pytest.fixture
    def sample_component(self):
        """Create a sample SOUP component."""
        return SOUPComponent(
            id="test-id-123",
            name="SQLite",
            version="3.36.0",
            usage_reason="Database storage for analysis results",
            safety_justification="Well-tested, widely used database engine with good safety record",
            supplier="SQLite Development Team",
            license="Public Domain",
            website="https://sqlite.org",
            description="Lightweight SQL database engine",
            criticality_level="Medium",
            verification_method="Unit testing and integration testing",
            anomaly_list=["None known"]
        )
    
    def test_add_component_success(self, soup_service, sample_component):
        """Test successful component addition."""
        component_id = soup_service.add_component(sample_component)
        
        assert component_id == sample_component.id
        
        # Verify component was stored
        retrieved = soup_service.get_component(component_id)
        assert retrieved is not None
        assert retrieved.name == sample_component.name
        assert retrieved.version == sample_component.version
        assert retrieved.usage_reason == sample_component.usage_reason
        assert retrieved.safety_justification == sample_component.safety_justification
    
    def test_add_component_validation_error(self, soup_service):
        """Test component addition with validation errors."""
        invalid_component = SOUPComponent(
            id="test-id",
            name="",  # Empty name should cause validation error
            version="1.0",
            usage_reason="Test",
            safety_justification="Test"
        )
        
        with pytest.raises(ValueError, match="Component validation failed"):
            soup_service.add_component(invalid_component)
    
    def test_add_component_generates_id(self, soup_service):
        """Test that component ID is generated if not provided."""
        component = SOUPComponent(
            id="",  # Empty ID should be generated
            name="Test Component",
            version="1.0",
            usage_reason="Testing",
            safety_justification="Safe for testing"
        )
        
        component_id = soup_service.add_component(component)
        
        assert component_id
        assert len(component_id) > 0
        
        # Verify component was stored with generated ID
        retrieved = soup_service.get_component(component_id)
        assert retrieved is not None
        assert retrieved.id == component_id
    
    def test_update_component_success(self, soup_service, sample_component):
        """Test successful component update."""
        # Add component first
        soup_service.add_component(sample_component)
        
        # Update component
        sample_component.version = "3.37.0"
        sample_component.description = "Updated description"
        
        success = soup_service.update_component(sample_component)
        assert success
        
        # Verify update
        retrieved = soup_service.get_component(sample_component.id)
        assert retrieved.version == "3.37.0"
        assert retrieved.description == "Updated description"
    
    def test_update_nonexistent_component(self, soup_service, sample_component):
        """Test updating a component that doesn't exist."""
        success = soup_service.update_component(sample_component)
        assert not success
    
    def test_update_component_validation_error(self, soup_service, sample_component):
        """Test component update with validation errors."""
        soup_service.add_component(sample_component)
        
        # Make component invalid
        sample_component.name = ""
        
        with pytest.raises(ValueError, match="Component validation failed"):
            soup_service.update_component(sample_component)
    
    def test_get_component_exists(self, soup_service, sample_component):
        """Test getting an existing component."""
        soup_service.add_component(sample_component)
        
        retrieved = soup_service.get_component(sample_component.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_component.id
        assert retrieved.name == sample_component.name
    
    def test_get_component_not_exists(self, soup_service):
        """Test getting a non-existent component."""
        retrieved = soup_service.get_component("nonexistent-id")
        assert retrieved is None
    
    def test_get_all_components_empty(self, soup_service):
        """Test getting all components when none exist."""
        components = soup_service.get_all_components()
        assert components == []
    
    def test_get_all_components_multiple(self, soup_service):
        """Test getting all components with multiple components."""
        # Add multiple components
        component1 = SOUPComponent(
            id="comp1", name="Component A", version="1.0",
            usage_reason="Test", safety_justification="Safe"
        )
        component2 = SOUPComponent(
            id="comp2", name="Component B", version="2.0",
            usage_reason="Test", safety_justification="Safe"
        )
        
        soup_service.add_component(component1)
        soup_service.add_component(component2)
        
        components = soup_service.get_all_components()
        
        assert len(components) == 2
        component_names = [c.name for c in components]
        assert "Component A" in component_names
        assert "Component B" in component_names
    
    def test_delete_component_success(self, soup_service, sample_component):
        """Test successful component deletion."""
        soup_service.add_component(sample_component)
        
        success = soup_service.delete_component(sample_component.id)
        assert success
        
        # Verify component was deleted
        retrieved = soup_service.get_component(sample_component.id)
        assert retrieved is None
    
    def test_delete_component_not_exists(self, soup_service):
        """Test deleting a non-existent component."""
        success = soup_service.delete_component("nonexistent-id")
        assert not success
    
    def test_search_components_by_name(self, soup_service):
        """Test searching components by name."""
        component1 = SOUPComponent(
            id="comp1", name="SQLite Database", version="1.0",
            usage_reason="Test", safety_justification="Safe"
        )
        component2 = SOUPComponent(
            id="comp2", name="OpenSSL Library", version="1.0",
            usage_reason="Test", safety_justification="Safe"
        )
        
        soup_service.add_component(component1)
        soup_service.add_component(component2)
        
        results = soup_service.search_components("SQLite")
        
        assert len(results) == 1
        assert results[0].name == "SQLite Database"
    
    def test_search_components_by_supplier(self, soup_service):
        """Test searching components by supplier."""
        component = SOUPComponent(
            id="comp1", name="Test Component", version="1.0",
            usage_reason="Test", safety_justification="Safe",
            supplier="Test Supplier Inc."
        )
        
        soup_service.add_component(component)
        
        results = soup_service.search_components("Test Supplier")
        
        assert len(results) == 1
        assert results[0].supplier == "Test Supplier Inc."
    
    def test_search_components_no_results(self, soup_service, sample_component):
        """Test searching with no matching results."""
        soup_service.add_component(sample_component)
        
        results = soup_service.search_components("NonexistentComponent")
        assert results == []
    
    def test_get_components_by_criticality(self, soup_service):
        """Test getting components by criticality level."""
        high_comp = SOUPComponent(
            id="high", name="High Criticality", version="1.0",
            usage_reason="Test", safety_justification="Safe",
            criticality_level="High"
        )
        medium_comp = SOUPComponent(
            id="medium", name="Medium Criticality", version="1.0",
            usage_reason="Test", safety_justification="Safe",
            criticality_level="Medium"
        )
        
        soup_service.add_component(high_comp)
        soup_service.add_component(medium_comp)
        
        high_results = soup_service.get_components_by_criticality("High")
        medium_results = soup_service.get_components_by_criticality("Medium")
        
        assert len(high_results) == 1
        assert high_results[0].criticality_level == "High"
        
        assert len(medium_results) == 1
        assert medium_results[0].criticality_level == "Medium"
    
    def test_export_inventory_empty(self, soup_service):
        """Test exporting empty inventory."""
        export_data = soup_service.export_inventory()
        
        assert "soup_inventory" in export_data
        assert export_data["soup_inventory"]["component_count"] == 0
        assert export_data["soup_inventory"]["components"] == []
        assert "export_timestamp" in export_data["soup_inventory"]
    
    def test_export_inventory_with_components(self, soup_service, sample_component):
        """Test exporting inventory with components."""
        soup_service.add_component(sample_component)
        
        export_data = soup_service.export_inventory()
        
        assert export_data["soup_inventory"]["component_count"] == 1
        assert len(export_data["soup_inventory"]["components"]) == 1
        
        exported_comp = export_data["soup_inventory"]["components"][0]
        assert exported_comp["name"] == sample_component.name
        assert exported_comp["version"] == sample_component.version
    
    def test_component_with_dates(self, soup_service):
        """Test component with installation and update dates."""
        install_date = datetime(2023, 1, 15)
        update_date = datetime(2023, 6, 20)
        
        component = SOUPComponent(
            id="date-test", name="Date Test", version="1.0",
            usage_reason="Test", safety_justification="Safe",
            installation_date=install_date,
            last_updated=update_date
        )
        
        soup_service.add_component(component)
        retrieved = soup_service.get_component("date-test")
        
        assert retrieved.installation_date == install_date
        assert retrieved.last_updated == update_date
    
    def test_component_with_anomaly_list(self, soup_service):
        """Test component with anomaly list."""
        component = SOUPComponent(
            id="anomaly-test", name="Anomaly Test", version="1.0",
            usage_reason="Test", safety_justification="Safe",
            anomaly_list=["Bug #123: Memory leak in version 1.0", "Issue #456: Crash on invalid input"]
        )
        
        soup_service.add_component(component)
        retrieved = soup_service.get_component("anomaly-test")
        
        assert len(retrieved.anomaly_list) == 2
        assert "Bug #123" in retrieved.anomaly_list[0]
        assert "Issue #456" in retrieved.anomaly_list[1]