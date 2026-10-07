import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://resourcelense:resourcelense@localhost:5432/resourcelense_test",
)

# These must be set before the application modules are imported: settings are
# read once at import time and would otherwise point the tests at the
# development database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-secret-key-that-is-long-enough-for-hs256-signing",
)
os.environ.setdefault("ENVIRONMENT", "test")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.permission import Permission  # noqa: E402
from app.models.role import Role  # noqa: E402
from app.models.user import User  # noqa: E402
from app.scripts.seed_rbac import PERMISSIONS  # noqa: E402

API = "/api/v1"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-password"
DEFAULT_PASSWORD = "user-password"


def _require_test_database() -> None:
    database = engine.url.database or ""

    if not database.endswith("_test"):
        raise RuntimeError(
            f"Refusing to run tests against database {database!r}; "
            "the test database name must end with '_test'."
        )


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    """Rebuild the test schema from the real Alembic migrations."""
    _require_test_database()

    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    backend_root = Path(__file__).resolve().parents[1]

    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "head")

    yield


@pytest.fixture(autouse=True)
def database(migrated_database: None) -> Iterator[None]:
    """Reset the database and seed the baseline RBAC data before every test."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE user_roles, role_permissions, users, roles, "
                "permissions RESTART IDENTITY CASCADE"
            )
        )

    with SessionLocal() as db:
        permissions = [
            Permission(name=name, description=description)
            for name, description in PERMISSIONS.items()
        ]

        admin_role = Role(
            name="admin",
            description="Full system administrator",
            permissions=permissions,
        )

        admin_user = User(
            email=ADMIN_EMAIL,
            full_name="Test Admin",
            hashed_password=hash_password(ADMIN_PASSWORD),
            is_active=True,
        )
        admin_user.roles.append(admin_role)

        db.add(admin_user)
        db.commit()

    yield


@pytest.fixture
def session() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db


@pytest.fixture
def client() -> Iterator[TestClient]:
    test_client = TestClient(app)

    yield test_client

    test_client.close()


def login(
    test_client: TestClient,
    email: str,
    password: str = DEFAULT_PASSWORD,
):
    return test_client.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
    )


@pytest.fixture
def authenticated_client() -> Iterator[
    Callable[..., TestClient]
]:
    """Factory returning a *new* logged-in client with its own cookie jar."""
    created: list[TestClient] = []

    def factory(
        email: str = ADMIN_EMAIL,
        password: str = DEFAULT_PASSWORD,
    ) -> TestClient:
        test_client = TestClient(app)
        created.append(test_client)

        response = login(test_client, email, password)

        assert response.status_code == 204, response.text

        return test_client

    yield factory

    for test_client in created:
        test_client.close()


@pytest.fixture
def admin_client(authenticated_client) -> TestClient:
    return authenticated_client(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture
def make_role(session: Session):
    def factory(name: str, permissions: list[str]) -> Role:
        granted = list(
            session.scalars(
                select(Permission).where(Permission.name.in_(permissions))
            ).all()
        )

        role = Role(
            name=name,
            description=f"{name} role",
            permissions=granted,
        )

        session.add(role)
        session.commit()
        session.refresh(role)

        return role

    return factory


@pytest.fixture
def make_user(session: Session):
    def factory(
        email: str,
        password: str = DEFAULT_PASSWORD,
        roles: list[Role] | None = None,
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email,
            full_name=email.split("@")[0].replace(".", " ").title(),
            hashed_password=hash_password(password),
            is_active=is_active,
        )
        user.roles = list(roles or [])

        session.add(user)
        session.commit()
        session.refresh(user)

        return user

    return factory
