from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import Base, get_db, get_engine, get_session_local
import importlib

@pytest.fixture(scope="module")
def test_db():
    with PostgresContainer("postgres:15") as postgres:
        # Set env vars
        url = postgres.get_connection_url()
        os.environ["DATABASE_URL"] = url  # Optional if you use a unified var
        parsed = urlparse(url)

        os.environ["POSTGRES_HOST"] = parsed.hostname
        os.environ["POSTGRES_PORT"] = str(parsed.port)
        os.environ["POSTGRES_USER"] = parsed.username
        os.environ["POSTGRES_PASSWORD"] = parsed.password
        os.environ["POSTGRES_DB"] = parsed.path.strip("/")

        # Reload modules that use env vars
        import app.db.database
        importlib.reload(app.db.database)

        engine = get_engine()
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()
