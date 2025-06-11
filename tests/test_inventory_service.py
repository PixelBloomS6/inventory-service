import pytest
import uuid
from unittest.mock import Mock
from sqlalchemy.orm import Session
from app.services.inventory_service import InventoryService
from app.models.domain.inventory import InventoryItemCreate


class TestInventoryService:
    """Simple tests for InventoryService"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_repository(self):
        """Mock inventory repository"""
        return Mock()
    
    @pytest.fixture
    def inventory_service(self, mock_db_session, mock_repository):
        """Create inventory service with mocked dependencies"""
        service = InventoryService(mock_db_session)
        service.repository = mock_repository
        return service
    
    def test_service_initialization(self, mock_db_session):
        """Test that service initializes correctly"""
        service = InventoryService(mock_db_session)
        assert service.repository is not None
    
    def test_create_item_calls_repository(self, inventory_service, mock_repository):
        """Test that create_item calls the repository"""
        # Arrange
        item_data = InventoryItemCreate(
            name="Test Item",
            description="Test Description", 
            price=99.99,
            quantity=10,
            shop_id=uuid.uuid4()
        )
        
        # Act
        inventory_service.create_item(item_data)
        
        # Assert
        mock_repository.create.assert_called_once_with(item_data)
    
    def test_get_item_calls_repository(self, inventory_service, mock_repository):
        """Test that get_item calls the repository"""
        # Arrange
        item_id = uuid.uuid4()
        
        # Act
        inventory_service.get_item(item_id)
        
        # Assert
        mock_repository.get_by_id.assert_called_once_with(item_id)
    
    def test_get_all_items_default_params(self, inventory_service, mock_repository):
        """Test get_all_items uses default parameters"""
        # Act
        inventory_service.get_all_items()
        
        # Assert
        mock_repository.get_all.assert_called_once_with(0, 100)


# Keep your existing basic tests
def test_health_check():
    """Test basic functionality"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ping():
    """Test ping endpoint"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"message": "pong"}