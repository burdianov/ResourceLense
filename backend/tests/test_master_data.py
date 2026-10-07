from fastapi.testclient import TestClient

from tests.conftest import API


def test_department_crud_and_reference_protection(admin_client: TestClient) -> None:
    response = admin_client.post(
        f"{API}/departments/",
        json={"code": "ENG", "name": "Engineering", "sort_order": 1},
    )
    assert response.status_code == 201
    department = response.json()

    duplicate = admin_client.post(
        f"{API}/departments/", json={"code": "ENG", "name": "Dup"}
    )
    assert duplicate.status_code == 409

    response = admin_client.patch(
        f"{API}/departments/{department['id']}",
        json={"name": "Engineering Dept", "is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Referenced -> 409; then deactivate path is the lifecycle.
    designation = admin_client.post(
        f"{API}/designations/",
        json={"code": "PE", "name": "Planning Engineer", "department_id": department["id"]},
    ).json()

    delete = admin_client.delete(f"{API}/departments/{department['id']}")
    assert delete.status_code == 409

    unreferenced = admin_client.post(
        f"{API}/departments/", json={"code": "TMP", "name": "Temp"}
    ).json()
    assert admin_client.delete(f"{API}/departments/{unreferenced['id']}").status_code == 204


def test_designation_crud(admin_client: TestClient) -> None:
    department = admin_client.post(
        f"{API}/departments/", json={"code": "QA", "name": "QA/QC"}
    ).json()

    response = admin_client.post(
        f"{API}/designations/",
        json={
            "code": "QAE",
            "name": "QA/QC Engineer",
            "department_id": department["id"],
        },
    )
    assert response.status_code == 201

    designation = response.json()
    assert designation["department_id"] == department["id"]

    # Unknown department rejected.
    assert (
        admin_client.post(
            f"{API}/designations/",
            json={"code": "X1", "name": "X", "department_id": 999999},
        ).status_code
        == 400
    )

    response = admin_client.patch(
        f"{API}/designations/{designation['id']}", json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_category_and_trade_crud(admin_client: TestClient) -> None:
    category = admin_client.post(
        f"{API}/employee-categories/",
        json={"code": "STAFF", "name": "Staff"},
    )
    assert category.status_code == 201

    trade = admin_client.post(
        f"{API}/trades/", json={"code": "ELEC", "name": "Electrical"}
    )
    assert trade.status_code == 201

    assert (
        admin_client.post(
            f"{API}/trades/", json={"code": "ELEC", "name": "Dup"}
        ).status_code
        == 409
    )

    updated = admin_client.patch(
        f"{API}/trades/{trade.json()['id']}", json={"description": "Electrical trade"}
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Electrical trade"


def test_provider_crud_and_audit_fields(admin_client: TestClient) -> None:
    provider = admin_client.post(
        f"{API}/resource-providers/",
        json={"code": "ABC", "name": "ABC Manpower", "contact_person": "Ali"},
    )
    assert provider.status_code == 201
    provider = provider.json()

    assert provider["created_by_id"] > 0

    updated = admin_client.patch(
        f"{API}/resource-providers/{provider['id']}",
        json={"email": "sales@abc.example.com", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False
    assert updated.json()["email"] == "sales@abc.example.com"
    assert updated.json()["updated_by_id"] == provider["created_by_id"]


def test_master_data_requires_manage_permission(
    make_role, make_user, authenticated_client
) -> None:
    role = make_role("ref-viewer", ["master_data.view"])
    make_user("refviewer@example.com", roles=[role])

    viewer = authenticated_client("refviewer@example.com", "user-password")

    assert viewer.get(f"{API}/departments/").status_code == 200
    assert (
        viewer.post(
            f"{API}/departments/", json={"code": "NOPE", "name": "Nope"}
        ).status_code
        == 403
    )


def test_master_data_visible_with_employees_view_only(
    make_role, make_user, authenticated_client
) -> None:
    role = make_role("emp-viewer", ["employees.view"])
    make_user("empviewer@example.com", roles=[role])

    viewer = authenticated_client("empviewer@example.com", "user-password")

    assert viewer.get(f"{API}/designations/").status_code == 200
    assert viewer.get(f"{API}/employee-categories/").status_code == 200
