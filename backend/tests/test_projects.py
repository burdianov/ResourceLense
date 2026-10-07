from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.models.project import ProjectMembership
from tests.conftest import API, make_user


def _create_project(client: TestClient, code: str = "P-100", **overrides):
    payload = {"code": code, "name": f"Project {code}", **overrides}
    return client.post(f"{API}/projects/", json=payload)


def _grant_membership(user_id: int, project_id: int) -> None:
    with SessionLocal() as db:
        db.add(
            ProjectMembership(
                project_id=project_id, user_id=user_id, created_by_id=1
            )
        )
        db.commit()


def test_create_project(admin_client: TestClient) -> None:
    response = _create_project(
        admin_client, award_probability=65.5, client_name="Acme"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "P-100"
    assert body["status"] == "tender"
    assert body["award_probability"] == 65.5
    assert body["archived_at"] is None


def test_create_project_strips_and_requires_code_and_name(
    admin_client: TestClient,
) -> None:
    assert _create_project(admin_client, code="  P-101 ").status_code == 201
    assert _create_project(admin_client, code="   ").status_code == 422
    assert (
        admin_client.post(
            f"{API}/projects/", json={"code": "P-102", "name": "  "}
        ).status_code
        == 422
    )


def test_create_project_rejects_duplicate_code(admin_client: TestClient) -> None:
    assert _create_project(admin_client, code="P-DUP").status_code == 201
    assert _create_project(admin_client, code="P-DUP").status_code == 409


def test_create_project_validates_status_and_probability(
    admin_client: TestClient,
) -> None:
    assert (
        _create_project(admin_client, code="P-BAD", status="bogus").status_code
        == 422
    )
    assert (
        _create_project(
            admin_client, code="P-NEG", award_probability=150.0
        ).status_code
        == 422
    )


def test_status_transition_and_archive_roundtrip(
    admin_client: TestClient,
) -> None:
    project = _create_project(admin_client, code="P-LIFE").json()

    response = admin_client.patch(
        f"{API}/projects/{project['id']}", json={"status": "active"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "active"

    gone = _create_project(admin_client, code="P-GONE").json()
    assert admin_client.post(f"{API}/projects/{gone['id']}/archive").status_code == 200

    codes = [item["code"] for item in admin_client.get(f"{API}/projects/").json()]
    assert "P-GONE" not in codes

    archived = admin_client.get(f"{API}/projects/archived").json()
    assert [item["code"] for item in archived] == ["P-GONE"]

    response = admin_client.post(f"{API}/projects/{gone['id']}/unarchive")
    assert response.status_code == 200
    assert response.json()["archived_at"] is None


def test_normal_user_only_sees_member_projects(
    make_role, make_user, authenticated_client, admin_client: TestClient
) -> None:
    role = make_role("viewer", ["projects.view"])
    user = make_user("viewer@example.com", roles=[role])

    visible = _create_project(admin_client, code="P-MINE").json()
    _create_project(admin_client, code="P-OTHER")

    viewer = authenticated_client("viewer@example.com", "user-password")

    # Without membership: sees nothing, cannot open the project by ID.
    assert viewer.get(f"{API}/projects/").json() == []
    assert viewer.get(f"{API}/projects/{visible['id']}").status_code == 403

    _grant_membership(user.id, visible["id"])

    listed = viewer.get(f"{API}/projects/").json()
    assert [item["code"] for item in listed] == [visible["code"]]
    assert viewer.get(f"{API}/projects/{visible['id']}").status_code == 200


def test_membership_does_not_grant_missing_rbac_permission(
    make_user, authenticated_client, admin_client: TestClient
) -> None:
    user = make_user("nomperm@example.com")
    project = _create_project(admin_client, code="P-NOP").json()

    _grant_membership(user.id, project["id"])

    member = authenticated_client("nomperm@example.com")

    assert member.get(f"{API}/projects/").status_code == 403
    assert member.get(f"{API}/projects/{project['id']}").status_code == 403


def test_deactivated_membership_hides_project(
    make_role, make_user, authenticated_client, admin_client: TestClient
) -> None:
    role = make_role("viewer", ["projects.view"])
    user = make_user("gone@example.com", roles=[role])
    project = _create_project(admin_client, code="P-BYE").json()

    _grant_membership(user.id, project["id"])

    member = authenticated_client("gone@example.com")
    assert member.get(f"{API}/projects/{project['id']}").status_code == 200

    memberships = admin_client.get(
        f"{API}/projects/{project['id']}/memberships"
    ).json()
    admin_client.patch(
        f"{API}/projects/memberships/{memberships[0]['id']}",
        json={"is_active": False},
    )

    assert member.get(f"{API}/projects/{project['id']}").status_code == 403
    assert member.get(f"{API}/projects/").json() == []


def test_memberships_view_allowed_but_manage_needs_permission(
    make_role, make_user, authenticated_client, admin_client: TestClient
) -> None:
    """Viewing who has access follows the view permission; mutating needs manage."""
    role = make_role("viewer", ["projects.view", "project_memberships.view"])
    user = make_user("cv@example.com", roles=[role])
    project = _create_project(admin_client, code="P-CV").json()

    _grant_membership(user.id, project["id"])
    member = authenticated_client("cv@example.com")

    assert (
        member.get(f"{API}/projects/{project['id']}/memberships").status_code
        == 200
    )
    assert (
        member.post(
            f"{API}/projects/{project['id']}/memberships",
            json={"user_id": user.id},
        ).status_code
        == 403
    )
    assert (
        member.delete(
            f"{API}/projects/memberships/999999"
        ).status_code
        == 403
    )


def test_add_membership_validates_unknown_user_and_duplicates(
    admin_client: TestClient, make_user
) -> None:
    project = _create_project(admin_client, code="P-DUPM").json()

    assert (
        admin_client.post(
            f"{API}/projects/{project['id']}/memberships",
            json={"user_id": 999999},
        ).status_code
        == 400
    )

    user = make_user("dup@example.com")

    assert (
        admin_client.post(
            f"{API}/projects/{project['id']}/memberships",
            json={"user_id": user.id},
        ).status_code
        == 201
    )
    assert (
        admin_client.post(
            f"{API}/projects/{project['id']}/memberships",
            json={"user_id": user.id},
        ).status_code
        == 409
    )


def test_remove_membership(admin_client: TestClient, make_user) -> None:
    project = _create_project(admin_client, code="P-RM").json()
    user = make_user("rm@example.com")

    membership = admin_client.post(
        f"{API}/projects/{project['id']}/memberships",
        json={"user_id": user.id},
    ).json()

    assert (
        admin_client.delete(
            f"{API}/projects/memberships/{membership['id']}"
        ).status_code
        == 204
    )
    assert (
        admin_client.get(f"{API}/projects/{project['id']}/memberships").json()
        == []
    )


def test_project_approvers_crud(admin_client: TestClient, make_user) -> None:
    project = _create_project(admin_client, code="P-APR").json()
    user = make_user("approver@example.com")

    response = admin_client.post(
        f"{API}/projects/{project['id']}/approvers",
        json={
            "user_id": user.id,
            "approval_type": "assignment",
            "sequence_order": 1,
        },
    )
    assert response.status_code == 201

    approver = response.json()
    assert approver["approval_type"] == "assignment"
    assert approver["is_required"] is True

    assert (
        len(admin_client.get(f"{API}/projects/{project['id']}/approvers").json())
        == 1
    )

    response = admin_client.patch(
        f"{API}/projects/approvers/{approver['id']}",
        json={"approval_type": "transfer", "sequence_order": 2},
    )
    assert response.status_code == 200
    assert response.json()["approval_type"] == "transfer"

    assert (
        admin_client.delete(
            f"{API}/projects/approvers/{approver['id']}"
        ).status_code
        == 204
    )
    assert (
        admin_client.get(f"{API}/projects/{project['id']}/approvers").json()
        == []
    )


def test_project_approver_validates_type(
    admin_client: TestClient, make_user
) -> None:
    project = _create_project(admin_client, code="P-BADT").json()
    user = make_user("badtype@example.com")

    response = admin_client.post(
        f"{API}/projects/{project['id']}/approvers",
        json={"user_id": user.id, "approval_type": "payroll"},
    )
    assert response.status_code == 422


def test_projects_require_authentication(client: TestClient) -> None:
    assert client.get(f"{API}/projects/").status_code == 401


def test_projects_require_permissions(make_role, make_user, authenticated_client) -> None:
    role = make_role("noroles", [])
    make_user("plain@example.com", roles=[role])

    member = authenticated_client("plain@example.com")

    assert member.get(f"{API}/projects/").status_code == 403
    assert (
        member.post(
            f"{API}/projects/", json={"code": "P-X", "name": "X"}
        ).status_code
        == 403
    )
