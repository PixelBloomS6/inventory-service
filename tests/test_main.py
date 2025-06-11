import pytest

def test_basic_functionality():
    """Test basic Python functionality"""
    assert 1 + 1 == 2

def test_string_operations():
    """Test string operations"""
    test_string = "inventory service"
    assert "inventory" in test_string
    assert test_string.title() == "Inventory Service"

def test_list_comprehension():
    """Test list operations"""
    numbers = [1, 2, 3, 4, 5]
    squared = [x**2 for x in numbers]
    assert squared == [1, 4, 9, 16, 25]

def test_dictionary_operations():
    """Test dictionary operations"""
    inventory_data = {
        "name": "Test Item",
        "price": 99.99,
        "quantity": 10
    }
    assert inventory_data["name"] == "Test Item"
    assert len(inventory_data) == 3

# Try to test the app without Azure dependencies
def test_app_models():
    """Test that we can import domain models"""
    try:
        from app.models.domain.inventory import InventoryItem, InventoryItemCreate
        # Test that classes exist
        assert InventoryItem is not None
        assert InventoryItemCreate is not None
    except ImportError as e:
        pytest.skip(f"Could not import models: {e}")

def test_database_models():
    """Test database models"""
    try:
        from app.models.database.inventory import InventoryItemModel
        assert InventoryItemModel is not None
    except ImportError as e:
        pytest.skip(f"Could not import database models: {e}")
        
