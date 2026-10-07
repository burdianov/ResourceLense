from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.models.user import User
from tests.conftest import API


def test_anonymous_request_is_rejected(client: TestClient) -> None:
    assert client.get(f"{API}/users/").status_code == 401
    assert client.get(f"{API}/roles/").status_code == 401
    assert client.get(f"{API}/permissions/").status_code == 401


def test_user_without_the_permission_gets_403(
    make_role,
    make_user,
    authenticated_client,
) -> None:
    role = make_role("planner", ["projects.view"])
    make_user("planner@example.com", roles=[role])

    member = authenticated_client("planner@example.com")

    assert member.get(f"{API}/users/").status_code == 403
    assert member.get(f"{API}/roles/").status_code == 403
    assert member.post(
        f"{API}/users/",
        json={
            "email": "x@example.com",
            "full_name": "X",
            "password": "password123",
        },
    ).status_code == 403


def test_user_with_the_permission_gets_200(
    make_role,
    make_user,
    authenticated_client,
) -> None:
    role = make_role("user-admin", ["users.view"])
    make_user("viewer@example.com", roles=[role])

    viewer = authenticated_client("viewer@example.com")

    assert viewer.get(f"{API}/users/").status_code == 200


def test_role_list_accepts_either_permission(
    make_role,
    make_user,
    authenticated_client,
) -> None:
    """GET /roles/ is shared reference data for two administration screens."""
    roles_only = make_role("role-manager", ["roles.view"])
    users_only = make_role("user-viewer", ["users.view"])

    make_user("rolemgr@example.com", roles=[roles_only])
    make_user("userviewer@example.com", roles=[users_only])

    assert (
        authenticated_client("rolemgr@example.com").get(f"{API}/roles/").status_code
        == 200
    )
    assert (
        authenticated_client("userviewer@example.com")
        .get(f"{API}/roles/")
        .status_code
        == 200
    )


def test_permission_revocation_applies_without_a_new_login(
    make_role,
    make_user,
    authenticated_client,
) -> None:
    """Permissions are re-read per request, so a removed role takes effect at once."""
    role = make_role("user-admin", ["users.view"])
    user = make_user("viewer@example.com", roles=[role])

    viewer = authenticated_client("viewer@example.com")

    assert viewer.get(f"{API}/users/").status_code == 200

    with SessionLocal() as db:
        stored = db.get(User, user.id)
        assert stored is not None
        stored.roles = []
        db.commit()

    assert viewer.get(f"{API}/users/").status_code == 403


def test_deactivation_locks_out_an_existing_session(
    make_role,
    make_user,
    authenticated_client,
) -> None:
    role = make_role("user-admin", ["users.view"])
    user = make_user("viewer@example.com", roles=[role])

    viewer = authenticated_client("viewer@example.com")

    assert viewer.get(f"{API}/users/").status_code == 200

    with SessionLocal() as db:
        stored = db.get(User, user.id)
        assert stored is not None
        stored.is_active = False
        db.commit()

    assert viewer.get(f"{API}/users/").status_code == 401
