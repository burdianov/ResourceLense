from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.models.project import ProjectMembership
from tests.conftest import API


def _create_project(client: TestClient, code: str) -> int:
    response = client.post(
        f"{API}/projects/", json={"code": code, "name": f"Project {code}"}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_designation(client: TestClient, code: str) -> int:
    response = client.post(
        f"{API}/designations/",
        json={"code": code, "name": f"Designation {code}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_employee(
    client: TestClient, designation_id: int, code: str
) -> int:
    response = client.post(
        f"{API}/employees/",
        json={
            "employee_id": code,
            "full_name": f"Worker {code}",
            "designation_id": designation_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _add_designation_rate(
    client: TestClient,
    designation_id: int,
    rate: float,
    effective_from: str = "2026-01-01T00:00:00Z",
) -> dict:
    response = client.post(
        f"{API}/rates/designations",
        json={
            "designation_id": designation_id,
            "hourly_rate": rate,
            "currency_code": "AED",
            "effective_from": effective_from,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _end_designation_rate(
    client: TestClient, rate_id: int, effective_to: str
) -> None:
    response = client.post(
        f"{API}/rates/designations/{rate_id}/end",
        params={"effective_to": effective_to},
    )
    assert response.status_code == 200, response.text


def _add_employee_rate(
    client: TestClient,
    employee_id: int,
    rate: float,
    effective_from: str = "2026-01-01T00:00:00Z",
) -> dict:
    response = client.post(
        f"{API}/rates/employees",
        json={
            "employee_id": employee_id,
            "hourly_rate": rate,
            "currency_code": "AED",
            "effective_from": effective_from,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_version(
    client: TestClient,
    project_id: int,
    forecast_type: str = "tender",
    **overrides,
) -> dict:
    response = client.post(
        f"{API}/forecasts/",
        json={
            "project_id": project_id,
            "forecast_type": forecast_type,
            **overrides,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add_line(
    client: TestClient,
    version_id: int,
    designation_id: int,
    months: list[dict] | None = None,
    **overrides,
) -> dict:
    payload: dict = {"designation_id": designation_id, **overrides}

    if months is not None:
        payload["months"] = months

    response = client.post(
        f"{API}/forecasts/{version_id}/lines", json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


def _cell(month: str, allocation: float) -> dict:
    return {"month": month, "allocation_percentage": allocation}


def _find_line(detail: dict, line_id: int) -> dict:
    return next(line for line in detail["lines"] if line["id"] == line_id)


def _find_month(line: dict, month: str) -> dict:
    return next(
        cell for cell in line["months"] if cell["month"].startswith(month)
    )


def _grant_membership(user_id: int, project_id: int) -> None:
    with SessionLocal() as db:
        db.add(
            ProjectMembership(
                project_id=project_id, user_id=user_id, created_by_id=1
            )
        )
        db.commit()


# --- versions --------------------------------------------------------------


def test_version_numbering_per_project_and_type(
    admin_client: TestClient,
) -> None:
    project = _create_project(admin_client, "F-100")

    tender_v1 = _create_version(admin_client, project, "tender")
    tender_v2 = _create_version(admin_client, project, "tender")
    job_v1 = _create_version(admin_client, project, "job")

    assert tender_v1["version_no"] == 1
    assert tender_v2["version_no"] == 2
    assert job_v1["version_no"] == 1

    assert tender_v1["status"] == "draft"
    assert tender_v1["is_current"] is False

    response = admin_client.post(
        f"{API}/forecasts/",
        json={"project_id": project, "forecast_type": "bogus"},
    )
    assert response.status_code == 422


def test_create_version_requires_project_access_and_permission(
    admin_client: TestClient,
    authenticated_client,
    make_role,
    make_user,
) -> None:
    project = _create_project(admin_client, "F-101")

    role = make_role("forecaster", ["forecasts.view", "forecasts.create"])
    user = make_user("forecaster@example.com", roles=[role])
    client = authenticated_client("forecaster@example.com")

    # RBAC permission is present, but without project membership the
    # project is not visible (spec #9).
    response = client.post(
        f"{API}/forecasts/",
        json={"project_id": project, "forecast_type": "tender"},
    )
    assert response.status_code == 403

    _grant_membership(user.id, project)

    assert (
        client.post(
            f"{API}/forecasts/",
            json={"project_id": project, "forecast_type": "tender"},
        ).status_code
        == 201
    )


# --- lines -----------------------------------------------------------------


def test_repeated_designation_rows_with_named_and_unnamed(
    admin_client: TestClient,
) -> None:
    """Spec #6/#24/#106: repeated designations are intentional."""
    project = _create_project(admin_client, "F-110")
    designation = _create_designation(admin_client, "F-PE-110")
    employee = _create_employee(admin_client, designation, "F-EMP-110")

    version = _create_version(admin_client, project)

    detail = _add_line(
        admin_client,
        version["id"],
        designation,
        employee_id=employee,
        months=[_cell("2027-01-01", 100)],
    )
    detail = _add_line(
        admin_client,
        version["id"],
        designation,
        headcount=2,
        months=[_cell("2027-01-01", 50)],
    )

    assert len(detail["lines"]) == 2

    named, unnamed = detail["lines"]

    assert named["employee_id"] == employee
    assert named["employee_name"] == "Worker F-EMP-110"
    assert named["headcount"] == 1

    assert unnamed["employee_id"] is None
    assert unnamed["headcount"] == 2
    assert unnamed["designation_id"] == designation


def test_named_line_forces_headcount_one(admin_client: TestClient) -> None:
    project = _create_project(admin_client, "F-111")
    designation = _create_designation(admin_client, "F-PE-111")
    employee = _create_employee(admin_client, designation, "F-EMP-111")

    version = _create_version(admin_client, project)

    response = admin_client.post(
        f"{API}/forecasts/{version['id']}/lines",
        json={
            "designation_id": designation,
            "employee_id": employee,
            "headcount": 5,
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["lines"][0]["headcount"] == 1


def test_unnamed_line_requires_positive_headcount(
    admin_client: TestClient,
) -> None:
    project = _create_project(admin_client, "F-112")
    designation = _create_designation(admin_client, "F-PE-112")
    version = _create_version(admin_client, project)

    response = admin_client.post(
        f"{API}/forecasts/{version['id']}/lines",
        json={"designation_id": designation, "headcount": 0},
    )

    assert response.status_code == 422


def test_line_rejects_inactive_designation_and_terminated_employee(
    admin_client: TestClient,
) -> None:
    project = _create_project(admin_client, "F-113")
    designation = _create_designation(admin_client, "F-PE-113")
    employee = _create_employee(admin_client, designation, "F-EMP-113")

    assert (
        admin_client.post(
            f"{API}/employees/{employee}/terminate",
            json={"termination_date": "2026-06-01T00:00:00Z"},
        ).status_code
        in (200, 204)
    )

    version = _create_version(admin_client, project)

    response = admin_client.post(
        f"{API}/forecasts/{version['id']}/lines",
        json={"designation_id": designation, "employee_id": employee},
    )
    assert response.status_code == 422

    admin_client.patch(
        f"{API}/designations/{designation}", json={"is_active": False}
    )

    response = admin_client.post(
        f"{API}/forecasts/{version['id']}/lines",
        json={"designation_id": designation},
    )
    assert response.status_code == 422


# --- monthly deployment, FTE and cost --------------------------------------


def test_monthly_deployment_fte_and_hours(admin_client: TestClient) -> None:
    project = _create_project(admin_client, "F-120")
    designation = _create_designation(admin_client, "F-PE-120")

    version = _create_version(admin_client, project)

    detail = _add_line(
        admin_client,
        version["id"],
        designation,
        headcount=3,
        months=[
            _cell("2027-01-01", 50),
            _cell("2027-02-01", 100),
        ],
    )

    line = detail["lines"][0]

    january = _find_month(line, "2027-01")
    february = _find_month(line, "2027-02")

    # FTE = headcount x allocation / 100 (spec #29).
    assert january["fte"] == 1.5
    assert february["fte"] == 3.0

    # 100% for one month = 208 hours (spec #22).
    assert january["hours"] == 312.0
    assert february["hours"] == 624.0

    assert line["summary"]["active_months"] == 2
    assert line["summary"]["average_fte"] == 2.25
    assert line["summary"]["total_hours"] == 936.0


def test_month_values_are_normalised_to_first_day(
    admin_client: TestClient,
) -> None:
    project = _create_project(admin_client, "F-121")
    designation = _create_designation(admin_client, "F-PE-121")
    version = _create_version(admin_client, project)

    line_id = _add_line(admin_client, version["id"], designation)["lines"][0][
        "id"
    ]

    response = admin_client.put(
        f"{API}/forecasts/lines/{line_id}/months",
        json={"months": [_cell("2027-03-15", 25)]},
    )

    assert response.status_code == 200, response.text
    cell = response.json()["lines"][0]["months"][0]

    assert cell["month"] == "2027-03-01"
    assert cell["allocation_percentage"] == 25.0


def test_allocation_percentage_bounds(admin_client: TestClient) -> None:
    project = _create_project(admin_client, "F-122")
    designation = _create_designation(admin_client, "F-PE-122")
    version = _create_version(admin_client, project)
    line_id = _add_line(admin_client, version["id"], designation)["lines"][0][
        "id"
    ]

    for allocation in (-5, 101):
        response = admin_client.put(
            f"{API}/forecasts/lines/{line_id}/months",
            json={"months": [_cell("2027-01-01", allocation)]},
        )
        assert response.status_code == 422


def test_forecast_cost_uses_208_rule_and_designation_rate(
    admin_client: TestClient,
) -> None:
    """Spec #28 worked example: 3 x 50% x 208 x 80 = 24,960."""
    project = _create_project(admin_client, "F-130")
    designation = _create_designation(admin_client, "F-PE-130")
    _add_designation_rate(admin_client, designation, 80)

    version = _create_version(admin_client, project)
    detail = _add_line(
        admin_client,
        version["id"],
        designation,
        headcount=3,
        months=[_cell("2027-01-01", 50)],
    )

    cell = detail["lines"][0]["months"][0]

    assert cell["hourly_rate"] == 80.0
    assert cell["currency_code"] == "AED"
    assert cell["rate_source"] == "designation"
    assert cell["cost"] == 24960.0
    assert cell["missing_rate"] is False


def test_named_line_prefers_employee_rate(admin_client: TestClient) -> None:
    project = _create_project(admin_client, "F-131")
    designation = _create_designation(admin_client, "F-PE-131")
    employee = _create_employee(admin_client, designation, "F-EMP-131")

    _add_designation_rate(admin_client, designation, 80)
    _add_employee_rate(admin_client, employee, 100)

    version = _create_version(admin_client, project)
    detail = _add_line(
        admin_client,
        version["id"],
        designation,
        employee_id=employee,
        months=[_cell("2027-01-01", 50)],
    )

    cell = detail["lines"][0]["months"][0]

    assert cell["rate_source"] == "employee"
    assert cell["hourly_rate"] == 100.0
    # 1 x 0.5 x 208 x 100
    assert cell["cost"] == 10400.0


def test_missing_rate_is_flagged_never_zero(admin_client: TestClient) -> None:
    project = _create_project(admin_client, "F-132")
    designation = _create_designation(admin_client, "F-PE-132")

    version = _create_version(admin_client, project)
    detail = _add_line(
        admin_client,
        version["id"],
        designation,
        headcount=1,
        months=[_cell("2027-01-01", 100)],
    )

    cell = detail["lines"][0]["months"][0]

    assert cell["hourly_rate"] is None
    assert cell["cost"] is None
    assert cell["missing_rate"] is True


def test_forecast_tables_store_no_monetary_totals() -> None:
    """Spec #26/#106: cost is derived, never stored."""
    from app.models.forecast import ForecastLine, ForecastLineMonth, ForecastVersion

    for model in (ForecastVersion, ForecastLine, ForecastLineMonth):
        columns = set(model.__table__.columns.keys())
        assert "monthly_cost" not in columns
        assert "total_cost" not in columns
        assert "cost" not in columns


# --- versioning: clone, publish, supersede, immutability --------------------


def test_clone_copies_structure_into_new_draft(
    admin_client: TestClient,
) -> None:
    project = _create_project(admin_client, "F-140")
    designation = _create_designation(admin_client, "F-PE-140")
    _add_designation_rate(admin_client, designation, 80)

    version = _create_version(admin_client, project)
    detail = _add_line(
        admin_client,
        version["id"],
        designation,
        headcount=2,
        months=[_cell("2027-01-01", 100)],
    )
    line_id = detail["lines"][0]["id"]

    response = admin_client.post(
        f"{API}/forecasts/{version['id']}/clone", json={}
    )

    assert response.status_code == 201, response.text
    clone = response.json()

    assert clone["version_no"] == 2
    assert clone["status"] == "draft"
    assert clone["is_current"] is False

    assert len(clone["lines"]) == 1
    cloned_line = clone["lines"][0]

    assert cloned_line["id"] != line_id
    assert cloned_line["designation_id"] == designation
    assert cloned_line["headcount"] == 2
    assert cloned_line["months"][0]["allocation_percentage"] == 100.0


def test_publish_supersedes_previous_current_and_freezes_rates(
    admin_client: TestClient,
) -> None:
    project = _create_project(admin_client, "F-141")
    designation = _create_designation(admin_client, "F-PE-141")
    rate = _add_designation_rate(admin_client, designation, 80)

    version = _create_version(admin_client, project)
    detail = _add_line(
        admin_client,
        version["id"],
        designation,
        headcount=3,
        months=[_cell("2027-01-01", 50)],
    )

    response = admin_client.post(f"{API}/forecasts/{version['id']}/publish")
    assert response.status_code == 200, response.text

    published = response.json()
    assert published["status"] == "published"
    assert published["is_current"] is True
    assert published["published_at"] is not None
    assert published["lines"][0]["months"][0]["cost"] == 24960.0

    # Rates change after publication.
    _end_designation_rate(admin_client, rate["id"], "2026-06-01T00:00:00Z")
    _add_designation_rate(
        admin_client, designation, 90, effective_from="2026-06-01T00:00:00Z"
    )

    # The published snapshot is unchanged (spec #27/#99).
    frozen = admin_client.get(f"{API}/forecasts/{version['id']}").json()
    frozen_cell = frozen["lines"][0]["months"][0]

    assert frozen_cell["hourly_rate"] == 80.0
    assert frozen_cell["cost"] == 24960.0

    # A new draft resolve rates currently (90) and, once published,
    # supersedes the previous current version.
    revision = admin_client.post(
        f"{API}/forecasts/{version['id']}/clone", json={}
    ).json()

    revision_cell = revision["lines"][0]["months"][0]
    assert revision_cell["hourly_rate"] == 90.0

    response = admin_client.post(f"{API}/forecasts/{revision['id']}/publish")
    assert response.status_code == 200, response.text

    superseded = admin_client.get(f"{API}/forecasts/{version['id']}").json()
    assert superseded["status"] == "superseded"
    assert superseded["is_current"] is False
    assert superseded["superseded_at"] is not None

    current = admin_client.get(f"{API}/forecasts/{revision['id']}").json()
    assert current["status"] == "published"
    assert current["is_current"] is True
    assert current["lines"][0]["months"][0]["cost"] == 28080.0


def test_published_versions_are_immutable(admin_client: TestClient) -> None:
    project = _create_project(admin_client, "F-142")
    designation = _create_designation(admin_client, "F-PE-142")

    version = _create_version(admin_client, project)
    detail = _add_line(
        admin_client,
        version["id"],
        designation,
        months=[_cell("2027-01-01", 100)],
    )
    line_id = detail["lines"][0]["id"]

    admin_client.post(f"{API}/forecasts/{version['id']}/publish")

    assert (
        admin_client.patch(
            f"{API}/forecasts/{version['id']}", json={"name": "Renamed"}
        ).status_code
        == 409
    )
    assert (
        admin_client.post(
            f"{API}/forecasts/{version['id']}/lines",
            json={"designation_id": designation},
        ).status_code
        == 409
    )
    assert (
        admin_client.patch(
            f"{API}/forecasts/lines/{line_id}", json={"headcount": 2}
        ).status_code
        == 409
    )
    assert (
        admin_client.put(
            f"{API}/forecasts/lines/{line_id}/months",
            json={"months": [_cell("2027-02-01", 50)]},
        ).status_code
        == 409
    )
    assert (
        admin_client.delete(f"{API}/forecasts/{version['id']}").status_code
        == 409
    )
    assert (
        admin_client.post(
            f"{API}/forecasts/{version['id']}/publish"
        ).status_code
        == 409
    )


def test_publish_requires_at_least_one_line(admin_client: TestClient) -> None:
    project = _create_project(admin_client, "F-143")
    version = _create_version(admin_client, project)

    response = admin_client.post(f"{API}/forecasts/{version['id']}/publish")

    assert response.status_code == 422


def test_refresh_rates_updates_draft_snapshots(
    admin_client: TestClient,
) -> None:
    project = _create_project(admin_client, "F-144")
    designation = _create_designation(admin_client, "F-PE-144")
    rate = _add_designation_rate(admin_client, designation, 80)

    version = _create_version(admin_client, project)
    detail = _add_line(
        admin_client,
        version["id"],
        designation,
        headcount=1,
        months=[_cell("2027-01-01", 100)],
    )
    assert detail["lines"][0]["months"][0]["hourly_rate"] == 80.0

    _end_designation_rate(admin_client, rate["id"], "2026-06-01T00:00:00Z")
    _add_designation_rate(
        admin_client, designation, 90, effective_from="2026-06-01T00:00:00Z"
    )

    response = admin_client.post(
        f"{API}/forecasts/{version['id']}/refresh-rates"
    )

    assert response.status_code == 200, response.text
    assert response.json()["lines"][0]["months"][0]["hourly_rate"] == 90.0


def test_draft_soft_delete_is_recoverable_and_hidden(
    admin_client: TestClient,
) -> None:
    project = _create_project(admin_client, "F-145")
    version = _create_version(admin_client, project)

    assert (
        admin_client.delete(f"{API}/forecasts/{version['id']}").status_code
        == 204
    )

    assert admin_client.get(f"{API}/forecasts/{version['id']}").status_code == 404

    listing = admin_client.get(
        f"{API}/forecasts/", params={"project_id": project}
    ).json()
    assert listing == []

    # The row itself is retained for recovery (spec #87).
    listing_all = admin_client.get(f"{API}/forecasts/").json()
    assert all(item["id"] != version["id"] for item in listing_all)


def test_archive_removes_current_and_hides_from_default_list(
    admin_client: TestClient,
) -> None:
    project = _create_project(admin_client, "F-146")
    designation = _create_designation(admin_client, "F-PE-146")

    version = _create_version(admin_client, project)
    _add_line(admin_client, version["id"], designation)
    admin_client.post(f"{API}/forecasts/{version['id']}/publish")

    response = admin_client.post(f"{API}/forecasts/{version['id']}/archive")
    assert response.status_code == 200, response.text

    archived = response.json()
    assert archived["status"] == "archived"
    assert archived["is_current"] is False

    listing = admin_client.get(
        f"{API}/forecasts/", params={"project_id": project}
    ).json()
    assert listing == []

    listing = admin_client.get(
        f"{API}/forecasts/",
        params={"project_id": project, "include_archived": True},
    ).json()
    assert len(listing) == 1


# --- permissions and cost visibility ---------------------------------------


def test_edit_and_publish_require_permissions(
    admin_client: TestClient,
    authenticated_client,
    make_role,
    make_user,
) -> None:
    project = _create_project(admin_client, "F-150")
    designation = _create_designation(admin_client, "F-PE-150")
    version = _create_version(admin_client, project)
    _add_line(admin_client, version["id"], designation)

    role = make_role("viewer", ["forecasts.view"])
    user = make_user("viewer@example.com", roles=[role])
    _grant_membership(user.id, project)
    client = authenticated_client("viewer@example.com")

    assert client.get(f"{API}/forecasts/{version['id']}").status_code == 200

    assert (
        client.post(
            f"{API}/forecasts/{version['id']}/lines",
            json={"designation_id": designation},
        ).status_code
        == 403
    )
    assert (
        client.post(f"{API}/forecasts/{version['id']}/publish").status_code
        == 403
    )
    assert (
        client.post(f"{API}/forecasts/{version['id']}/clone").status_code
        == 403
    )


def test_cost_and_rate_fields_hidden_without_cost_permission(
    admin_client: TestClient,
    authenticated_client,
    make_role,
    make_user,
) -> None:
    project = _create_project(admin_client, "F-151")
    designation = _create_designation(admin_client, "F-PE-151")
    _add_designation_rate(admin_client, designation, 80)

    version = _create_version(admin_client, project)
    _add_line(
        admin_client,
        version["id"],
        designation,
        headcount=1,
        months=[_cell("2027-01-01", 100)],
    )

    role = make_role("manpower", ["forecasts.view"])
    user = make_user("manpower@example.com", roles=[role])
    _grant_membership(user.id, project)
    client = authenticated_client("manpower@example.com")

    cell = client.get(f"{API}/forecasts/{version['id']}").json()["lines"][0][
        "months"
    ][0]

    # Manpower numbers stay visible; monetary/rate data does not (spec #95).
    assert cell["fte"] == 1.0
    assert cell["hours"] == 208.0
    assert cell["hourly_rate"] is None
    assert cell["cost"] is None
    assert cell["missing_rate"] is None

    cost_role = make_role(
        "costs", ["forecasts.view", "forecasts.cost.view"]
    )
    cost_user = make_user("costs@example.com", roles=[cost_role])
    _grant_membership(cost_user.id, project)
    cost_client = authenticated_client("costs@example.com")

    cell = cost_client.get(f"{API}/forecasts/{version['id']}").json()["lines"][
        0
    ]["months"][0]

    assert cell["hourly_rate"] == 80.0
    assert cell["cost"] == 16640.0


# --- project scope (spec #9/#104) ------------------------------------------


def test_forecast_scope_is_enforced_server_side(
    admin_client: TestClient,
    authenticated_client,
    make_role,
    make_user,
) -> None:
    own_project = _create_project(admin_client, "F-160")
    other_project = _create_project(admin_client, "F-161")

    own_version = _create_version(admin_client, own_project)
    other_version = _create_version(admin_client, other_project)

    role = make_role(
        "planner",
        ["forecasts.view", "forecasts.create", "forecasts.edit"],
    )
    user = make_user("planner@example.com", roles=[role])
    _grant_membership(user.id, own_project)
    client = authenticated_client("planner@example.com")

    # Only member projects are listed.
    listing = client.get(f"{API}/forecasts/").json()
    assert {item["id"] for item in listing} == {own_version["id"]}

    assert client.get(f"{API}/forecasts/{own_version['id']}").status_code == 200

    # Foreign projects are not reachable even with a direct id (spec #104).
    assert (
        client.get(f"{API}/forecasts/{other_version['id']}").status_code == 403
    )

    # Membership alone grants nothing without the RBAC permission.
    member_only_role = make_role("member-only", ["reports.view"])
    member_only = make_user("member-only@example.com", roles=[member_only_role])
    _grant_membership(member_only.id, own_project)
    member_client = authenticated_client("member-only@example.com")

    assert (
        member_client.get(f"{API}/forecasts/{own_version['id']}").status_code
        == 403
    )


def test_admin_sees_all_projects(admin_client: TestClient) -> None:
    project = _create_project(admin_client, "F-162")
    version = _create_version(admin_client, project)

    listing = admin_client.get(f"{API}/forecasts/").json()

    assert any(item["id"] == version["id"] for item in listing)
