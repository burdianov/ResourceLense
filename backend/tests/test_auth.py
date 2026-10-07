from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    API,
    DEFAULT_PASSWORD,
    login,
)


def test_health(client: TestClient) -> None:
    response = client.get(f"{API}/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_with_correct_credentials_sets_httponly_cookie(
    client: TestClient,
) -> None:
    response = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

    assert response.status_code == 204

    set_cookie = response.headers["set-cookie"]

    assert "access_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie


def test_login_with_wrong_password_is_rejected(client: TestClient) -> None:
    response = login(client, ADMIN_EMAIL, "wrong-password")

    assert response.status_code == 401


def test_login_with_unknown_email_is_rejected(client: TestClient) -> None:
    response = login(client, "nobody@example.com", DEFAULT_PASSWORD)

    assert response.status_code == 401


def test_login_is_case_insensitive_for_email(client: TestClient) -> None:
    response = login(client, ADMIN_EMAIL.upper(), ADMIN_PASSWORD)

    assert response.status_code == 204


def test_login_rejects_inactive_user(
    client: TestClient,
    make_user,
) -> None:
    make_user("inactive@example.com", is_active=False)

    response = login(client, "inactive@example.com")

    assert response.status_code == 401


def test_me_requires_authentication(client: TestClient) -> None:
    assert client.get(f"{API}/auth/me").status_code == 401


def test_me_returns_roles_and_permissions(admin_client: TestClient) -> None:
    response = admin_client.get(f"{API}/auth/me")

    assert response.status_code == 200

    body = response.json()

    assert body["email"] == ADMIN_EMAIL
    assert body["roles"] == ["admin"]
    assert "users.view" in body["permissions"]
    assert "roles.delete" in body["permissions"]


def test_logout_clears_the_cookie(admin_client: TestClient) -> None:
    response = admin_client.post(f"{API}/auth/logout")

    assert response.status_code == 204
    assert admin_client.get(f"{API}/auth/me").status_code == 401


def test_logout_revokes_the_issued_token(admin_client: TestClient) -> None:
    """The JWT must stop working even when it is replayed after logout."""
    stolen_token = admin_client.cookies.get("access_token")

    assert stolen_token

    admin_client.post(f"{API}/auth/logout")

    replayed = TestClient(app)
    replayed.cookies.set("access_token", stolen_token)

    try:
        assert replayed.get(f"{API}/auth/me").status_code == 401
    finally:
        replayed.close()


def test_logout_without_a_session_is_still_successful(
    client: TestClient,
) -> None:
    assert client.post(f"{API}/auth/logout").status_code == 204


def test_cors_allows_the_vite_dev_origin(client: TestClient) -> None:
    response = client.options(
        f"{API}/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:5173"
    )
    assert response.headers["access-control-allow-credentials"] == "true"
