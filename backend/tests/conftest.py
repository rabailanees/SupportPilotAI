import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.organization import Organization
from app.models.user import User


test_url = make_url(settings.TEST_DATABASE_URL)

# Safety guard: tests must never create/drop tables in the development DB.
if test_url.database != "supportpilot_test":
    raise RuntimeError(
        "Unsafe test database configuration. "
        "Expected database: supportpilot_test"
    )

if test_url.host not in ("localhost", "127.0.0.1") or test_url.port != 5433:
    raise RuntimeError(
        "Unsafe test database host or port. "
        "Expected localhost:5433."
    )

test_engine = create_engine(
    settings.TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def tenant_context(db_session):
    """Create two isolated organizations and authenticated users."""

    organization_a = Organization(
        name="Organization A",
        slug="organization-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="organization-b",
    )

    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="admin-a@example.com",
        password_hash=hash_password("TestPassword123!"),
        role="admin",
        is_active=True,
    )
    user_b = User(
        organization_id=organization_b.id,
        email="admin-b@example.com",
        password_hash=hash_password("TestPassword123!"),
        role="admin",
        is_active=True,
    )

    db_session.add_all([user_a, user_b])
    db_session.commit()

    return {
        "organization_a": organization_a,
        "organization_b": organization_b,
        "user_a": user_a,
        "user_b": user_b,
        "headers_a": {
            "Authorization": f"Bearer {create_access_token(str(user_a.id))}"
        },
        "headers_b": {
            "Authorization": f"Bearer {create_access_token(str(user_b.id))}"
        },
    }
