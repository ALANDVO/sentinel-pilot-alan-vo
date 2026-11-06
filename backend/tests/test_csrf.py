"""CSRF protection tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.core.database import Base, get_db
from app.core.config import Settings, get_settings as original_get_settings
from app.core.security import generate_csrf_token, CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from app.models import User, Instance, Mod

# Test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def db():
    await create_test_db()
    async with TestingSessionLocal() as session:
        yield session
    await drop_test_db()


@pytest.fixture(scope="function")
async def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestCSRF:
    """Test CSRF protection on state-changing requests."""

    async def test_csrf_cookie_set_on_get(self, client):
        """CSRF cookie should be set on GET requests."""
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert CSRF_COOKIE_NAME in response.cookies

    async def test_csrf_token_generation(self):
        """CSRF token should be cryptographically random."""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        assert token1 != token2
        assert len(token1) >= 32

    async def test_csrf_required_for_post(self, client):
        """POST requests without CSRF token should fail."""
        response = await client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })
        # Should fail with CSRF missing (403)
        assert response.status_code == 403
        assert "CSRF" in response.json()["detail"]

    async def test_csrf_valid_token_works(self, client):
        """POST with valid CSRF token should work."""
        # First get CSRF cookie
        response = await client.get("/api/health")
        csrf_token = response.cookies.get(CSRF_COOKIE_NAME)
        assert csrf_token

        # Use token in header for POST
        response = await client.post(
            "/api/auth/register",
            json={"email": "test2@example.com", "password": "password123"},
            headers={CSRF_HEADER_NAME: csrf_token},
            cookies={CSRF_COOKIE_NAME: csrf_token}
        )
        # Should succeed (or fail for other reasons, not CSRF)
        assert response.status_code != 403 or "CSRF" not in response.json().get("detail", "")

    async def test_csrf_invalid_token_fails(self, client):
        """POST with mismatched CSRF token should fail."""
        # Get valid CSRF cookie
        response = await client.get("/api/health")
        csrf_token = response.cookies.get(CSRF_COOKIE_NAME)

        # Use different token in header
        response = await client.post(
            "/api/auth/register",
            json={"email": "test3@example.com", "password": "password123"},
            headers={CSRF_HEADER_NAME: "invalid-token"},
            cookies={CSRF_COOKIE_NAME: csrf_token}
        )
        assert response.status_code == 403
        assert "CSRF" in response.json()["detail"]

    async def test_csrf_missing_header_fails(self, client):
        """POST with missing header token should fail."""
        response = await client.get("/api/health")
        csrf_token = response.cookies.get(CSRF_COOKIE_NAME)

        response = await client.post(
            "/api/auth/register",
            json={"email": "test4@example.com", "password": "password123"},
            cookies={CSRF_COOKIE_NAME: csrf_token}
        )
        assert response.status_code == 403
        assert "CSRF" in response.json()["detail"]

    async def test_csrf_missing_cookie_fails(self, client):
        """POST with missing cookie token should fail."""
        response = await client.post(
            "/api/auth/register",
            json={"email": "test5@example.com", "password": "password123"},
            headers={CSRF_HEADER_NAME: "some-token"}
        )
        assert response.status_code == 403
        assert "CSRF" in response.json()["detail"]

    async def test_csrf_safe_methods_exempt(self, client):
        """GET, HEAD, OPTIONS should not require CSRF."""
        for method in ["get", "head", "options"]:
            response = await getattr(client, method)("/api/health")
            assert response.status_code in (200, 405)
            assert "CSRF" not in response.json().get("detail", "") if response.status_code == 403 else True

    async def test_csrf_demo_mode_exempt(self):
        """CSRF should be skipped in demo mode."""
        import app.core.config as config_module
        from app.core.config import Settings

        # Create demo settings
        demo_settings = Settings(
            secret_key="test-secret-key-for-csrf-tests",
            environment="development",
            demo_mode=True,
        )
        # Override get_settings to return demo settings
        original_get_settings_func = config_module.get_settings
        def demo_get_settings():
            return demo_settings
        config_module.get_settings = demo_get_settings
        original_get_settings_func.cache_clear()

        # Create test database
        await create_test_db()

        try:
            app = create_app()
            app.dependency_overrides[get_db] = override_get_db
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/auth/register", json={
                    "email": "demo@example.com",
                    "password": "password123"
                })
                # Should not fail due to CSRF (may fail for other reasons)
                assert response.status_code != 403 or "CSRF" not in response.json().get("detail", "")
        finally:
            await drop_test_db()
            config_module.get_settings = original_get_settings_func
