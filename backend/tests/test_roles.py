from fastapi.testclient import TestClient

from app.scripts.seed_rbac import PERMISSIONS
from tests.conftest import API


def test_list_includes_the_protected_admin_role(
    admin_client: TestClient,
) -> None:
    response = admin_client.get(f"{API}/roles/")

    assert response.status_code == 200

    admin = next(role for role in response.json() if role["name"] == "admin")

    assert admin["is_protected"] is True
    assert admin["user_count"] == 1
    assert "users.view" in admin["permissions"]


def test_create_role(admin_client: TestClient) -> None:
    response = admin_client.post(
        f"{API}/roles/",
        json={
            "name": "Planner",
            "description": "Plans resource allocation",
            "permissions": ["projects.view", "planning.view"],
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["name"] == "planner"
    assert body["description"] == "Plans resource allocation"
    assert body["permissions"] == ["planning.view", "projects.view"]
    assert body["user_count"] == 0
    assert body["is_protected"] is False


def test_create_role_rejects_duplicate_names(
    admin_client: TestClient,
) -> None:
    payload = {"name": "planner", "permissions": []}

    assert admin_client.post(f"{API}/roles/", json=payload).status_code == 201
    assert admin_client.post(f"{API}/roles/", json=payload).status_code == 409


def test_create_role_rejects_unknown_permissions(
    admin_client: TestClient,
) -> None:
    response = admin_client.post(
        f"{API}/roles/",
        json={"name": "broken", "permissions": ["nope.nope"]},
    )

    assert response.status_code == 400


def test_update_role_renames_and_replaces_permissions(
    admin_client: TestClient,
    make_role,
) -> None:
    role = make_role("planner", ["projects.view"])

    response = admin_client.patch(
        f"{API}/roles/{role.id}",
        json={
            "name": "senior-planner",
            "description": "  ",
            "permissions": ["projects.edit"],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["name"] == "senior-planner"
    assert body["description"] is None
    assert body["permissions"] == ["projects.edit"]


def test_update_role_can_clear_the_description(
    admin_client: TestClient,
    make_role,
) -> None:
    role = make_role("planner", [])

    response = admin_client.patch(
        f"{API}/roles/{role.id}",
        json={"description": None},
    )

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_update_role_returns_404_for_unknown_role(
    admin_client: TestClient,
) -> None:
    response = admin_client.patch(
        f"{API}/roles/999999",
        json={"name": "unknown-role"},
    )

    assert response.status_code == 404


def test_the_admin_role_cannot_be_modified_or_deleted(
    admin_client: TestClient,
) -> None:
    roles = admin_client.get(f"{API}/roles/").json()
    admin = next(role for role in roles if role["name"] == "admin")

    update = admin_client.patch(
        f"{API}/roles/{admin['id']}",
        json={"permissions": []},
    )

    assert update.status_code == 400
    assert "seed" in update.json()["detail"]

    assert admin_client.delete(f"{API}/roles/{admin['id']}").status_code == 400

    still_there = admin_client.get(f"{API}/roles/").json()
    admin = next(role for role in still_there if role["name"] == "admin")

    assert len(admin["permissions"]) == len(PERMISSIONS)


def test_cannot_delete_a_role_that_is_still_assigned(
    admin_client: TestClient,
    make_role,
    make_user,
) -> None:
    role = make_role("planner", ["projects.view"])
    make_user("planner@example.com", roles=[role])

    response = admin_client.delete(f"{API}/roles/{role.id}")

    assert response.status_code == 409
    assert "assigned" in response.json()["detail"]


def test_delete_an_unassigned_role(
    admin_client: TestClient,
    make_role,
) -> None:
    role = make_role("temporary", [])

    assert admin_client.delete(f"{API}/roles/{role.id}").status_code == 204
    assert role.name not in [
        item["name"] for item in admin_client.get(f"{API}/roles/").json()
    ]


def test_delete_unknown_role_returns_404(admin_client: TestClient) -> None:
    assert admin_client.delete(f"{API}/roles/999999").status_code == 404


def test_role_mutations_require_the_matching_permission(
    make_role,
    make_user,
    authenticated_client,
) -> None:
    """A role that may create roles still cannot edit or delete them."""
    creator = make_role("role-creator", ["roles.create"])
    make_user("creator@example.com", roles=[creator])

    existing = make_role("existing", ["projects.view"])

    member = authenticated_client("creator@example.com")

    assert (
        member.post(
            f"{API}/roles/",
            json={"name": "fresh", "permissions": []},
        ).status_code
        == 201
    )

    assert (
        member.patch(
            f"{API}/roles/{existing.id}",
            json={"description": "nope"},
        ).status_code
        == 403
    )
    assert member.delete(f"{API}/roles/{existing.id}").status_code == 403


def test_permission_catalogue_is_protected_and_complete(
    admin_client: TestClient,
) -> None:
    response = admin_client.get(f"{API}/permissions/")

    assert response.status_code == 200

    names = {permission["name"] for permission in response.json()}

    assert len(names) == len(PERMISSIONS)
    assert {"users.view", "roles.view", "projects.view", "reports.view"} <= names
    assert {"projects.archive", "master_data.manage", "rates.manage"} <= names
    assert {"forecasts.view", "forecasts.publish", "forecasts.cost.view"} <= names


def test_permission_catalogue_requires_roles_view(
    make_role,
    make_user,
    authenticated_client,
) -> None:
    role = make_role("user-admin", ["users.view"])
    make_user("userviewer@example.com", roles=[role])

    member = authenticated_client("userviewer@example.com")

    assert member.get(f"{API}/permissions/").status_code == 403
