import os
import pytest
import importlib
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse
from testcontainers.postgres import PostgresContainer
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def test_db():
    with PostgresContainer("postgres:15") as postgres:
        url = postgres.get_connection_url()
        parsed = urlparse(url)

        # Set environment variables that your app uses
        os.environ["POSTGRES_HOST"] = parsed.hostname
        os.environ["POSTGRES_PORT"] = str(parsed.port)
        os.environ["POSTGRES_USER"] = parsed.username
        os.environ["POSTGRES_PASSWORD"] = parsed.password
        os.environ["POSTGRES_DB"] = parsed.path.lstrip("/")

        # Reimport app.db.database AFTER env vars are set
        import app.db.database
        importlib.reload(app.db.database)

        from app.db.database import Base, get_db, get_engine

        engine = get_engine()
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        # Override DB dependency
        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        yield client

        # Cleanup
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)  # Optional cleanup
