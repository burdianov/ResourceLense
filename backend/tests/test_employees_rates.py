from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.services.rates import resolve_rate, require_rate
from tests.conftest import API


def _make_designation(admin_client: TestClient, code: str = "PE-1") -> int:
    return admin_client.post(
        f"{API}/designations/", json={"code": code, "name": f"Desig {code}"}
    ).json()["id"]


def _make_employee(
    admin_client: TestClient,
    designation_id: int,
    code: str = "EMP-001",
    **overrides,
) -> dict:
    payload = {
        "employee_id": code,
        "full_name": f"Worker {code}",
        "designation_id": designation_id,
        **overrides,
    }
    response = admin_client.post(f"{API}/employees/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _add_designation_rate(
    admin_client: TestClient,
    designation_id: int,
    rate: float,
    effective_from: str = "2026-01-01T00:00:00Z",
    **overrides,
):
    return admin_client.post(
        f"{API}/rates/designations",
        json={
            "designation_id": designation_id,
            "hourly_rate": rate,
            "currency_code": "AED",
            "effective_from": effective_from,
            **overrides,
        },
    )


def _add_employee_rate(
    admin_client: TestClient,
    employee_id: int,
    rate: float,
    effective_from: str = "2026-01-01T00:00:00Z",
    **overrides,
):
    return admin_client.post(
        f"{API}/rates/employees",
        json={
            "employee_id": employee_id,
            "hourly_rate": rate,
            "currency_code": "AED",
            "effective_from": effective_from,
            **overrides,
        },
    )


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------


def test_employee_crud_and_duplicate_id(admin_client: TestClient) -> None:
    designation = _make_designation(admin_client)

    employee = _make_employee(admin_client, designation, first_name="Ahmed")
    assert employee["employment_source"] == "in_house"
    assert employee["employment_status"] == "active"

    # Duplicate employee_id rejected.
    assert (
        admin_client.post(
            f"{API}/employees/",
            json={
                "employee_id": "EMP-001",
                "full_name": "Dup",
                "designation_id": designation,
            },
        ).status_code
        == 409
    )

    response = admin_client.patch(
        f"{API}/employees/{employee['id']}",
        json={"full_name": "Ahmed Hassan", "phone": "+971500000000"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Ahmed Hassan"

    assert admin_client.get(f"{API}/employees/{employee['id']}").status_code == 200
    assert admin_client.get(f"{API}/employees/999999").status_code == 404


def test_employee_source_rules(admin_client: TestClient) -> None:
    designation = _make_designation(admin_client, "PE-SRC")
    provider = admin_client.post(
        f"{API}/resource-providers/",
        json={"code": "SRC-1", "name": "Source Co"},
    ).json()

    # hired without provider -> 422
    assert (
        admin_client.post(
            f"{API}/employees/",
            json={
                "employee_id": "EMP-H1",
                "full_name": "Hired No Provider",
                "designation_id": designation,
                "employment_source": "hired",
            },
        ).status_code
        == 422
    )

    # in_house with provider -> 422
    assert (
        admin_client.post(
            f"{API}/employees/",
            json={
                "employee_id": "EMP-H2",
                "full_name": "House With Provider",
                "designation_id": designation,
                "employment_source": "in_house",
                "resource_provider_id": provider["id"],
            },
        ).status_code
        == 422
    )

    # hired with provider -> 201
    hired = _make_employee(
        admin_client,
        designation,
        code="EMP-H3",
        employment_source="hired",
        resource_provider_id=provider["id"],
    )
    assert hired["employment_source"] == "hired"


def test_termination_lifecycle(admin_client: TestClient) -> None:
    designation = _make_designation(admin_client, "PE-TRM")
    employee = _make_employee(admin_client, designation, code="EMP-T1")

    response = admin_client.post(
        f"{API}/employees/{employee['id']}/terminate",
        json={"termination_date": "2026-12-31"},
    )
    assert response.status_code == 200
    assert response.json()["employment_status"] == "terminated"

    # Filter by status.
    active = admin_client.get(f"{API}/employees/?employment_status=active").json()
    terminated = admin_client.get(
        f"{API}/employees/?employment_status=terminated"
    ).json()

    assert all(item["id"] != employee["id"] for item in active)
    assert any(item["id"] == employee["id"] for item in terminated)


def test_employee_permissions(
    make_role, make_user, authenticated_client, admin_client: TestClient
) -> None:
    role = make_role("emp-view", ["employees.view"])
    make_user("empview@example.com", roles=[role])

    viewer = authenticated_client("empview@example.com", "user-password")
    designation = _make_designation(admin_client, "PE-PERM")

    assert viewer.get(f"{API}/employees/").status_code == 200
    assert (
        viewer.post(
            f"{API}/employees/",
            json={
                "employee_id": "EMP-NO",
                "full_name": "No",
                "designation_id": designation,
            },
        ).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# Rates (spec #99)
# ---------------------------------------------------------------------------


def test_designation_rate_crud_and_overlap_rejection(
    admin_client: TestClient,
) -> None:
    designation = _make_designation(admin_client, "PE-RATE")

    first = _add_designation_rate(admin_client, designation, 80.0)
    assert first.status_code == 201

    # Overlapping open-ended period -> 409
    assert (
        _add_designation_rate(admin_client, designation, 90.0).status_code == 409
    )

    # Close the first rate, then a new one fits after it.
    ended = admin_client.post(
        f"{API}/rates/designations/{first.json()['id']}/end",
        params={"effective_to": "2026-06-30T00:00:00Z"},
    )
    assert ended.status_code == 200

    second = _add_designation_rate(
        admin_client, designation, 90.0, effective_from="2026-07-01T00:00:00Z"
    )
    assert second.status_code == 201

    # Rate that starts before an existing period and runs into it -> 409
    assert (
        _add_designation_rate(
            admin_client,
            designation,
            70.0,
            effective_from="2026-05-01T00:00:00Z",
        ).status_code
        == 409
    )

    # effective_to before effective_from -> 422
    assert (
        _add_designation_rate(
            admin_client,
            designation,
            50.0,
            effective_from="2026-01-01T00:00:00Z",
            effective_to="2025-01-01T00:00:00Z",
        ).status_code
        == 422
    )

    # Negative rate -> 422
    assert (
        _add_designation_rate(admin_client, designation, -1).status_code == 422
    )


def test_rate_resolution_precedence_and_history(admin_client: TestClient) -> None:
    designation = _make_designation(admin_client, "PE-RES")
    employee = _make_employee(admin_client, designation, code="EMP-R1")

    # Designation rate from 2026-01-01 (open).
    _add_designation_rate(admin_client, designation, 80.0)

    # Employee override from 2026-03-01 (open).
    _add_employee_rate(admin_client, employee["id"], 95.0, effective_from="2026-03-01T00:00:00Z")

    with SessionLocal() as db:
        # Before override: designation rate applies.
        jan = resolve_rate(
            db,
            employee_id=employee["id"],
            designation_id=designation,
            target_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        )
        assert jan is not None
        assert jan.source == "designation"
        assert jan.hourly_rate == 80.0

        # After override: employee rate wins.
        apr = resolve_rate(
            db,
            employee_id=employee["id"],
            designation_id=designation,
            target_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
        )
        assert apr is not None
        assert apr.source == "employee"
        assert apr.hourly_rate == 95.0
        assert apr.currency_code == "AED"
        assert apr.source_record_id > 0

        # Historical date before any rate: None (missing-rate signal).
        missing = resolve_rate(
            db,
            employee_id=employee["id"],
            designation_id=designation,
            target_date=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        assert missing is None


def test_require_rate_raises_on_missing(admin_client: TestClient) -> None:
    import pytest
    from fastapi import HTTPException

    designation = _make_designation(admin_client, "PE-MISS")
    employee = _make_employee(admin_client, designation, code="EMP-M1")

    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            require_rate(
                db,
                employee_id=employee["id"],
                designation_id=designation,
                target_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
            )

        assert exc_info.value.status_code == 422


def test_rates_require_view_permission(
    make_role, make_user, authenticated_client, admin_client: TestClient
) -> None:
    role = make_role("no-rate", ["employees.view"])
    make_user("norate@example.com", roles=[role])

    member = authenticated_client("norate@example.com", "user-password")

    assert member.get(f"{API}/rates/designations").status_code == 403
    assert member.get(f"{API}/rates/employees").status_code == 403
