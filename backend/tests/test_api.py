# Backend tests
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.core.database import Base, get_db
from app.core.config import Settings
from app.models import User, Instance, Mod
from passlib.context import CryptContext

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


@pytest.fixture(scope="function")
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Add CSRF handling
        original_request = ac.request
        async def request_with_csrf(method, url, **kwargs):
            # For non-GET requests, get CSRF token first
            if method.upper() not in ("GET", "HEAD", "OPTIONS", "TRACE"):
                # Get CSRF cookie
                resp = await ac.get("/api/health")
                csrf_token = resp.cookies.get("csrf_token")
                if csrf_token:
                    headers = kwargs.get("headers", {}) or {}
                    headers["X-CSRF-Token"] = csrf_token
                    kwargs["headers"] = headers
                    # Ensure cookies are sent
                    cookies = kwargs.get("cookies", {}) or {}
                    cookies["csrf_token"] = csrf_token
                    kwargs["cookies"] = cookies
            return await original_request(method, url, **kwargs)
        ac.request = request_with_csrf
        yield ac


@pytest.fixture
def pwd_context():
    return CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture
def test_settings():
    return Settings(
        secret_key="test-secret-key",
        environment="development",
        debug=True,
        database_url="sqlite+aiosqlite:///:memory:",
        demo_mode=False,
    )


@pytest.fixture
async def test_user(db, pwd_context):
    user = User(
        email="test@example.com",
        hashed_password=pwd_context.hash("password123"),
        full_name="Test User",
        role="operator",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def test_user_token(test_user, test_settings):
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email, "role": test_user.role})
    return token


class TestHealth:
    async def test_health_check(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_db_health_check(self, client):
        response = await client.get("/api/health/db")
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "connected"


class TestAuth:
    async def test_register(self, client):
        response = await client.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "password": "password123",
            "full_name": "New User"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"

    async def test_register_duplicate_email(self, client, test_user):
        response = await client.post("/api/auth/register", json={
            "email": test_user.email,
            "password": "password123"
        })
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    async def test_login(self, client, test_user):
        response = await client.post("/api/auth/login", data={
            "username": test_user.email,
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_password(self, client, test_user):
        response = await client.post("/api/auth/login", data={
            "username": test_user.email,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    async def test_login_nonexistent_user(self, client):
        response = await client.post("/api/auth/login", data={
            "username": "nonexistent@example.com",
            "password": "password123"
        })
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    async def test_get_me(self, client, test_user_token):
        response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    async def test_get_me_no_token(self, client):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_logout(self, client, test_user_token):
        response = await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"


class TestInstances:
    async def test_create_instance(self, client, test_user_token):
        response = await client.post("/api/instances", json={
            "name": "Test Instance",
            "minecraft_version": "1.20.1",
            "loader": "fabric",
            "loader_version": "0.14.21",
            "memory_min": "1G",
            "memory_max": "2G",
            "java_path": "/usr/bin/java",
            "game_dir": "/home/user/minecraft",
        }, headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Instance"
        assert data["minecraft_version"] == "1.20.1"
        assert data["owner_id"] == 1

    async def test_list_instances(self, client, test_user_token, db):
        # Create a few instances
        for i in range(3):
            instance = Instance(
                name=f"Instance {i}",
                minecraft_version="1.20.1",
                loader="fabric",
                loader_version="0.14.21",
                memory_min="1G",
                memory_max="2G",
                java_path="/usr/bin/java",
                game_dir="/home/user/minecraft",
                owner_id=1,
            )
            db.add(instance)
        await db.commit()

        response = await client.get("/api/instances", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_instances_pagination(self, client, test_user_token, db):
        for i in range(15):
            instance = Instance(
                name=f"Instance {i}",
                minecraft_version="1.20.1",
                loader="fabric",
                loader_version="0.14.21",
                memory_min="1G",
                memory_max="2G",
                java_path="/usr/bin/java",
                game_dir="/home/user/minecraft",
                owner_id=1,
            )
            db.add(instance)
        await db.commit()

        response = await client.get("/api/instances?page=1&page_size=10", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["items"]) == 10

        response = await client.get("/api/instances?page=2&page_size=10", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5

    async def test_list_instances_search(self, client, test_user_token, db):
        instance1 = Instance(
            name="My Special Instance",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        instance2 = Instance(
            name="Another Instance",
            minecraft_version="1.19.2",
            loader="forge",
            loader_version="43.2.0",
            memory_min="2G",
            memory_max="4G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        db.add(instance1)
        db.add(instance2)
        await db.commit()

        response = await client.get("/api/instances?search=Special", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "My Special Instance"

    async def test_get_instance(self, client, test_user_token, db):
        instance = Instance(
            name="Test Instance",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        response = await client.get(f"/api/instances/{instance.id}", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == instance.id
        assert data["name"] == "Test Instance"

    async def test_get_instance_not_found(self, client, test_user_token):
        response = await client.get("/api/instances/999", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 404

    async def test_update_instance(self, client, test_user_token, db):
        instance = Instance(
            name="Original Name",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        response = await client.patch(f"/api/instances/{instance.id}", json={
            "name": "Updated Name",
            "memory_max": "4G"
        }, headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["memory_max"] == "4G"

    async def test_delete_instance(self, client, test_user_token, db):
        instance = Instance(
            name="To Delete",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        response = await client.delete(f"/api/instances/{instance.id}", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(f"/api/instances/{instance.id}", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 404


class TestMods:
    async def test_create_mod(self, client, test_user_token, db):
        # First create an instance
        instance = Instance(
            name="Test Instance",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        response = await client.post("/api/mods", json={
            "name": "Test Mod",
            "version": "1.0.0",
            "filename": "test-mod.jar",
            "file_path": "/mods/test-mod.jar",
            "file_hash": "abc123",
            "source": "local",
            "source_url": "https://example.com/mod.jar",
            "description": "A test mod",
            "is_enabled": True,
            "instance_id": instance.id,
        }, headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Mod"
        assert data["version"] == "1.0.0"

    async def test_list_mods(self, client, test_user_token, db):
        instance = Instance(
            name="Test Instance",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        for i in range(3):
            mod = Mod(
                name=f"Mod {i}",
                version="1.0.0",
                filename=f"mod{i}.jar",
                file_path=f"/mods/mod{i}.jar",
                file_hash=f"hash{i}",
                source="local",
                description="A test mod",
                is_enabled=True,
                instance_id=instance.id,
            )
            db.add(mod)
        await db.commit()

        response = await client.get("/api/mods", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_mods_enabled_only(self, client, test_user_token, db):
        instance = Instance(
            name="Test Instance",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        mod1 = Mod(
            name="Enabled Mod",
            version="1.0.0",
            filename="enabled.jar",
            file_path="/mods/enabled.jar",
            file_hash="hash1",
            source="local",
            description="Enabled",
            is_enabled=True,
            instance_id=instance.id,
        )
        mod2 = Mod(
            name="Disabled Mod",
            version="1.0.0",
            filename="disabled.jar",
            file_path="/mods/disabled.jar",
            file_hash="hash2",
            source="local",
            description="Disabled",
            is_enabled=False,
            instance_id=instance.id,
        )
        db.add(mod1)
        db.add(mod2)
        await db.commit()

        response = await client.get("/api/mods?enabled_only=true", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Enabled Mod"

    async def test_update_mod(self, client, test_user_token, db):
        instance = Instance(
            name="Test Instance",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        mod = Mod(
            name="Original Mod",
            version="1.0.0",
            filename="original.jar",
            file_path="/mods/original.jar",
            file_hash="hash123",
            source="local",
            description="Original",
            is_enabled=False,
            instance_id=instance.id,
        )
        db.add(mod)
        await db.commit()
        await db.refresh(mod)

        response = await client.patch(f"/api/mods/{mod.id}", json={
            "name": "Updated Mod",
            "is_enabled": True
        }, headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Mod"
        assert data["is_enabled"] is True

    async def test_delete_mod(self, client, test_user_token, db):
        instance = Instance(
            name="Test Instance",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        mod = Mod(
            name="To Delete",
            version="1.0.0",
            filename="delete.jar",
            file_path="/mods/delete.jar",
            file_hash="hash123",
            source="local",
            description="To delete",
            is_enabled=True,
            instance_id=instance.id,
        )
        db.add(mod)
        await db.commit()
        await db.refresh(mod)

        response = await client.delete(f"/api/mods/{mod.id}", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 204

        response = await client.get(f"/api/mods/{mod.id}", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 404

    async def test_upload_mod(self, client, test_user_token, db):
        import io
        # First create an instance
        instance = Instance(
            name="Test Instance",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        file_content = b"fake mod file content"
        file = io.BytesIO(file_content)
        files = {"file": ("mod.jar", file, "application/java-archive")}
        params = {"instance_id": str(instance.id)}
        data = {
            "name": "Uploaded Mod",
            "version": "1.0.0",
        }
        response = await client.post("/api/mods/upload", files=files, params=params, data=data, headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 201
        result = response.json()
        assert result["name"] == "mod"  # Extracted from filename
        assert result["file_hash"] is not None

    async def test_upload_mod_duplicate_hash(self, client, test_user_token, db):
        import io
        # First create an instance
        instance = Instance(
            name="Test Instance",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=1,
        )
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        file_content = b"fake mod file content"
        
        # First upload
        file1 = io.BytesIO(file_content)
        files1 = {"file": ("mod1.jar", file1, "application/java-archive")}
        params1 = {"instance_id": str(instance.id)}
        data1 = {"name": "Mod 1", "version": "1.0.0"}
        response1 = await client.post("/api/mods/upload", files=files1, params=params1, data=data1, headers={"Authorization": f"Bearer {test_user_token}"})
        assert response1.status_code == 201
        
        # Second upload with same content
        file2 = io.BytesIO(file_content)
        files2 = {"file": ("mod2.jar", file2, "application/java-archive")}
        params2 = {"instance_id": str(instance.id)}
        data2 = {"name": "Mod 2", "version": "1.0.0"}
        response2 = await client.post("/api/mods/upload", files=files2, params=params2, data=data2, headers={"Authorization": f"Bearer {test_user_token}"})
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]


class TestAuthorization:
    async def test_unauthorized_access(self, client):
        # Test without following redirects
        response = await client.get("/api/instances", follow_redirects=False)
        assert response.status_code == 401

    async def test_user_cannot_access_other_user_instance(self, client, test_user_token, db, pwd_context):
        # Create another user
        other_user = User(
            email="other@example.com",
            hashed_password=pwd_context.hash("password123"),
            full_name="Other User",
            role="operator",
        )
        db.add(other_user)
        await db.commit()
        await db.refresh(other_user)

        # Create instance owned by other user
        instance = Instance(
            name="Other's Instance",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="0.14.21",
            memory_min="1G",
            memory_max="2G",
            java_path="/usr/bin/java",
            game_dir="/home/user/minecraft",
            owner_id=other_user.id,
        )
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        # Try to access with test_user_token (user id 1)
        response = await client.get(f"/api/instances/{instance.id}", headers={"Authorization": f"Bearer {test_user_token}"})
        assert response.status_code == 404  # Not found because it's not theirs

