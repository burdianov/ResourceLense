from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import ADMIN_EMAIL, API, DEFAULT_PASSWORD, login


def test_list_returns_the_seeded_admin(admin_client: TestClient) -> None:
    response = admin_client.get(f"{API}/users/")

    assert response.status_code == 200

    emails = [user["email"] for user in response.json()]

    assert ADMIN_EMAIL in emails


def test_create_user(admin_client: TestClient) -> None:
    response = admin_client.post(
        f"{API}/users/",
        json={
            "email": "New.User@example.com",
            "full_name": "New User",
            "password": "password123",
            "roles": [],
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["email"] == "new.user@example.com"
    assert body["is_active"] is True
    assert body["roles"] == []


def test_create_user_with_a_known_role(
    admin_client: TestClient,
    make_role,
) -> None:
    make_role("planner", ["projects.view"])

    response = admin_client.post(
        f"{API}/users/",
        json={
            "email": "planner@example.com",
            "full_name": "Planner",
            "password": "password123",
            "roles": ["planner"],
        },
    )

    assert response.status_code == 201
    assert response.json()["roles"] == ["planner"]


def test_create_user_rejects_a_duplicate_email(
    admin_client: TestClient,
) -> None:
    response = admin_client.post(
        f"{API}/users/",
        json={
            "email": ADMIN_EMAIL,
            "full_name": "Duplicate",
            "password": "password123",
        },
    )

    assert response.status_code == 409


def test_create_user_rejects_an_unknown_role(
    admin_client: TestClient,
) -> None:
    response = admin_client.post(
        f"{API}/users/",
        json={
            "email": "someone@example.com",
            "full_name": "Someone",
            "password": "password123",
            "roles": ["does-not-exist"],
        },
    )

    assert response.status_code == 400


def test_create_user_rejects_a_short_password(
    admin_client: TestClient,
) -> None:
    response = admin_client.post(
        f"{API}/users/",
        json={
            "email": "someone@example.com",
            "full_name": "Someone",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_update_user_name_and_status(
    admin_client: TestClient,
    make_user,
) -> None:
    user = make_user("target@example.com")

    response = admin_client.patch(
        f"{API}/users/{user.id}",
        json={"full_name": "Renamed User", "is_active": False},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["full_name"] == "Renamed User"
    assert body["is_active"] is False


def test_update_user_roles(
    admin_client: TestClient,
    make_user,
    make_role,
) -> None:
    role = make_role("planner", ["projects.view"])
    user = make_user("target@example.com")

    response = admin_client.patch(
        f"{API}/users/{user.id}",
        json={"roles": [role.name]},
    )

    assert response.status_code == 200
    assert response.json()["roles"] == ["planner"]


def test_update_user_returns_404_for_unknown_user(
    admin_client: TestClient,
) -> None:
    response = admin_client.patch(f"{API}/users/999999", json={"full_name": "X"})

    assert response.status_code == 404


def test_cannot_deactivate_your_own_account(
    admin_client: TestClient,
) -> None:
    me = admin_client.get(f"{API}/auth/me").json()

    response = admin_client.patch(
        f"{API}/users/{me['id']}",
        json={"is_active": False},
    )

    assert response.status_code == 400


def test_cannot_change_your_own_roles(admin_client: TestClient) -> None:
    me = admin_client.get(f"{API}/auth/me").json()

    response = admin_client.patch(
        f"{API}/users/{me['id']}",
        json={"roles": []},
    )

    assert response.status_code == 400


def test_password_reset_replaces_the_old_password(
    admin_client: TestClient,
    make_user,
    client: TestClient,
) -> None:
    user = make_user("target@example.com")

    response = admin_client.put(
        f"{API}/users/{user.id}/password",
        json={"password": "brand-new-password"},
    )

    assert response.status_code == 204
    assert response.content == b""

    assert login(client, "target@example.com", "brand-new-password").status_code == 204
    assert login(client, "target@example.com", DEFAULT_PASSWORD).status_code == 401


def test_password_reset_revokes_existing_sessions(
    admin_client: TestClient,
    make_user,
    authenticated_client,
) -> None:
    user = make_user("target@example.com")

    member = authenticated_client("target@example.com")

    assert member.get(f"{API}/auth/me").status_code == 200

    admin_client.put(
        f"{API}/users/{user.id}/password",
        json={"password": "brand-new-password"},
    )

    assert member.get(f"{API}/auth/me").status_code == 401


def test_password_reset_validates_input(
    admin_client: TestClient,
    make_user,
) -> None:
    user = make_user("target@example.com")

    assert (
        admin_client.put(
            f"{API}/users/{user.id}/password",
            json={"password": "short"},
        ).status_code
        == 422
    )
    assert (
        admin_client.put(
            f"{API}/users/999999/password",
            json={"password": "long-enough-password"},
        ).status_code
        == 404
    )


def test_reset_password_then_login_again(
    admin_client: TestClient,
    make_user,
) -> None:
    """End-to-end: reset the password, then use it through a fresh client."""
    user = make_user("target@example.com")

    admin_client.put(
        f"{API}/users/{user.id}/password",
        json={"password": "brand-new-password"},
    )

    fresh = TestClient(app)

    try:
        assert login(fresh, "target@example.com", "brand-new-password").status_code == 204
        assert fresh.get(f"{API}/auth/me").json()["email"] == "target@example.com"
    finally:
        fresh.close()


def test_admin_password_change_does_not_break_other_users(
    admin_client: TestClient,
    make_user,
    authenticated_client,
) -> None:
    other = make_user("other@example.com")

    member = authenticated_client("other@example.com")

    admin_client.put(
        f"{API}/users/{other.id}/password",
        json={"password": "brand-new-password"},
    )

    assert member.get(f"{API}/auth/me").status_code == 401
    assert admin_client.get(f"{API}/auth/me").status_code == 200
