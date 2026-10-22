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
        yield ac

@pytest.fixture
def pwd_context():
    return CryptContext(schemes=["bcrypt"], deprecated="auto")

@pytest.fixture
def test_settings():
    return Settings(
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
        environment="test",
    )

@pytest.fixture
async def test_user(db, pwd_context):
    user = User(
        email="test@example.com",
        hashed_password=pwd_context.hash("testpass123"[:72]),
        full_name="Test User",
        role="viewer",
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
        assert "app" in data
        assert "version" in data

    async def test_db_health_check(self, client):
        response = await client.get("/api/health/db")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"


class TestAuth:
    async def test_register(self, client):
        response = await client.post(
            "/api/auth/register",
            json={"email": "newuser@example.com", "password": "password123", "full_name": "New User"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "viewer"

    async def test_register_duplicate_email(self, client, test_user):
        response = await client.post(
            "/api/auth/register",
            json={"email": test_user.email, "password": "password123"},
        )
        assert response.status_code == 400

    async def test_login(self, client, test_user):
        response = await client.post(
            "/api/auth/login",
            data={"username": test_user.email, "password": "testpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # Check cookie is set
        assert "access_token" in response.cookies

    async def test_login_invalid_password(self, client, test_user):
        response = await client.post(
            "/api/auth/login",
            data={"username": test_user.email, "password": "wrongpass"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client):
        response = await client.post(
            "/api/auth/login",
            data={"username": "nonexistent@example.com", "password": "password123"},
        )
        assert response.status_code == 401

    async def test_get_me(self, client, test_user_token):
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    async def test_get_me_no_token(self, client):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_logout(self, client, test_user_token):
        response = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 200


class TestInstances:
    async def test_create_instance(self, client, test_user_token):
        response = await client.post(
            "/api/instances",
            json={
                "name": "Test Instance",
                "minecraft_version": "1.20.1",
                "loader": "fabric",
                "loader_version": "0.15.11",
                "memory_max": "4G",
            },
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Instance"
        assert data["minecraft_version"] == "1.20.1"
        assert data["loader"] == "fabric"

    async def test_list_instances(self, client, test_user_token, db):
        # Create test instances
        for i in range(3):
            instance = Instance(
                name=f"Instance {i}",
                minecraft_version="1.20.1",
                loader="fabric",
                owner_id=1,
            )
            db.add(instance)
        await db.commit()

        response = await client.get(
            "/api/instances",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_instances_pagination(self, client, test_user_token, db):
        for i in range(25):
            instance = Instance(name=f"Instance {i}", minecraft_version="1.20.1", owner_id=1)
            db.add(instance)
        await db.commit()

        response = await client.get(
            "/api/instances?page=1&page_size=10",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total_pages"] == 3

    async def test_list_instances_search(self, client, test_user_token, db):
        instance1 = Instance(name="My Server", minecraft_version="1.20.1", owner_id=1)
        instance2 = Instance(name="Other World", minecraft_version="1.19.2", owner_id=1)
        db.add_all([instance1, instance2])
        await db.commit()

        response = await client.get(
            "/api/instances?search=server",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "My Server"

    async def test_get_instance(self, client, test_user_token, db):
        instance = Instance(name="Test Instance", minecraft_version="1.20.1", owner_id=1)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        response = await client.get(
            f"/api/instances/{instance.id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == instance.id
        assert data["name"] == "Test Instance"

    async def test_get_instance_not_found(self, client, test_user_token):
        response = await client.get(
            "/api/instances/999",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 404

    async def test_update_instance(self, client, test_user_token, db):
        instance = Instance(name="Original", minecraft_version="1.20.1", owner_id=1)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        response = await client.patch(
            f"/api/instances/{instance.id}",
            json={"name": "Updated", "memory_max": "8G"},
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["memory_max"] == "8G"

    async def test_delete_instance(self, client, test_user_token, db):
        # Create operator user and token
        from app.core.security import create_access_token
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        operator_user = User(email="operator@example.com", hashed_password=pwd_context.hash("pass"), role="operator")
        db.add(operator_user)
        await db.commit()
        await db.refresh(operator_user)
        operator_token = create_access_token(data={"sub": str(operator_user.id), "email": operator_user.email, "role": operator_user.role})

        # Create instance owned by operator
        instance = Instance(name="To Delete", minecraft_version="1.20.1", owner_id=operator_user.id)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        response = await client.delete(
            f"/api/instances/{instance.id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(
            f"/api/instances/{instance.id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 404


class TestMods:
    async def test_create_mod(self, client, test_user_token, db):
        instance = Instance(name="Test Instance", minecraft_version="1.20.1", owner_id=1)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        response = await client.post(
            "/api/mods",
            json={
                "instance_id": instance.id,
                "name": "Test Mod",
                "version": "1.0.0",
                "filename": "test-mod.jar",
                "file_path": "/path/to/test-mod.jar",
                "source": "local",
            },
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Mod"
        assert data["instance_id"] == instance.id

    async def test_list_mods(self, client, test_user_token, db):
        instance = Instance(name="Test Instance", minecraft_version="1.20.1", owner_id=1)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        for i in range(3):
            mod = Mod(
                instance_id=instance.id,
                name=f"Mod {i}",
                version="1.0.0",
                filename=f"mod{i}.jar",
                file_path=f"/path/to/mod{i}.jar",
                is_enabled=True,
            )
            db.add(mod)
        await db.commit()

        response = await client.get(
            f"/api/mods?instance_id={instance.id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    async def test_list_mods_enabled_only(self, client, test_user_token, db):
        instance = Instance(name="Test Instance", minecraft_version="1.20.1", owner_id=1)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        mod1 = Mod(instance_id=instance.id, name="Enabled Mod", version="1.0", filename="enabled.jar", file_path="/p", is_enabled=True)
        mod2 = Mod(instance_id=instance.id, name="Disabled Mod", version="1.0", filename="disabled.jar", file_path="/p", is_enabled=False)
        db.add_all([mod1, mod2])
        await db.commit()

        response = await client.get(
            f"/api/mods?instance_id={instance.id}&enabled_only=true",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Enabled Mod"

    async def test_update_mod(self, client, test_user_token, db):
        instance = Instance(name="Test Instance", minecraft_version="1.20.1", owner_id=1)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        mod = Mod(instance_id=instance.id, name="Old Name", version="1.0", filename="old.jar", file_path="/p")
        db.add(mod)
        await db.commit()
        await db.refresh(mod)

        response = await client.patch(
            f"/api/mods/{mod.id}",
            json={"name": "New Name", "is_enabled": False},
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["is_enabled"] is False

    async def test_delete_mod(self, client, test_user_token, db):
        # Create operator user and token
        from app.core.security import create_access_token
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        operator_user = User(email="operator2@example.com", hashed_password=pwd_context.hash("pass"), role="operator")
        db.add(operator_user)
        await db.commit()
        await db.refresh(operator_user)
        operator_token = create_access_token(data={"sub": str(operator_user.id), "email": operator_user.email, "role": operator_user.role})

        # Create instance owned by operator
        instance = Instance(name="Test Instance", minecraft_version="1.20.1", owner_id=operator_user.id)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        mod = Mod(instance_id=instance.id, name="To Delete", version="1.0", filename="del.jar", file_path="/p")
        db.add(mod)
        await db.commit()
        await db.refresh(mod)

        response = await client.delete(
            f"/api/mods/{mod.id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 204


class TestAuthorization:
    async def test_unauthorized_access(self, client):
        response = await client.get("/api/instances")
        assert response.status_code == 401

    async def test_user_cannot_access_other_user_instance(self, client, db, pwd_context):
        # Create first user (owner)
        user1 = User(email="user1@example.com", hashed_password=pwd_context.hash("pass"), role="viewer")
        db.add(user1)
        await db.commit()
        await db.refresh(user1)

        # Create instance owned by user1
        instance = Instance(name="User1 Instance", minecraft_version="1.20.1", owner_id=user1.id)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

        # Create second user
        user2 = User(email="user2@example.com", hashed_password=pwd_context.hash("pass"), role="viewer")
        db.add(user2)
        await db.commit()
        await db.refresh(user2)

        # User2 tries to access user1's instance
        from app.core.security import create_access_token
        token2 = create_access_token(data={"sub": str(user2.id), "email": user2.email, "role": user2.role})

        response = await client.get(
            f"/api/instances/{instance.id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code == 404  # Not found because it's not theirs