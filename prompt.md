# ResourceLense — Master Business Logic, UX and PostgreSQL Implementation Specification

---

# ✅ Implementation Progress & Handoff (authoritative status block)

> **Read this first.** This block is the single source of truth for what is
> done and what is pending. The specification below (sections 1–108) remains
> the requirements. Update this block whenever a phase or deliverable
> completes. Last verified: **2026-10-08** (full repo inspection, test run,
> migration check).

## Verification evidence (as of 2026-10-08)

- `cd backend && uv run pytest -q` → **101 passed** (auth, RBAC, users, roles, projects, master data, employees, rates, forecasts).
- `uv run alembic current` → `9763603b7163 (head)` — business settings + forecast engine applied to the dev database.
- Commits on `main` (2026-10-08), **pushed to `origin/main`**: `9fb87e9` master data + rate engine (phases 2–3), `c784b47` forecast engine backend (phase 4), `697709f` handoff update.
- An independent code review of phases 2–4 followed (10 review angles, every finding reproduced against the live test database; models/migrations confirmed in sync). Its findings are the backlog below — **pushed unfixed by explicit decision** (private repo, no deployment).

## Phase status

| Phase | Scope | Status |
|---|---|---|
| 1 | Inspect + final schema / ERD design | ⚠️ **PARTIAL** — see below |
| 2 | Master data (backend) | ✅ **DONE** |
| 2f | Master data frontend UI | ❌ NOT STARTED |
| 3 | Rate engine (backend) | ✅ **DONE** (2 small follow-ups; #3 resolved in Phase 4) |
| 4 | Forecast engine (backend) | ✅ **DONE** — but fix the review backlog (P0/P1) before building on it |
| 4f | Forecast editor UI (spreadsheet grid) | ❌ NOT STARTED — after the review backlog |
| 5 | Assignment engine | ❌ NOT STARTED |
| 6 | Transfers | ❌ NOT STARTED |
| 7 | Leave | ❌ NOT STARTED |
| 8 | Consolidated planning | ❌ NOT STARTED |
| 9 | Dashboard | ❌ NOT STARTED |
| 10 | Reports + PDF/Excel | ❌ NOT STARTED |

### Phase 1 — Inspect and final schema: PARTIAL

- Repository / SQLAlchemy / Alembic / RBAC / frontend inspection: **done** (evident from the implementation that followed).
- Only design artifact written down: `backend/app/scripts/business_permissions_design.md` (permission catalogue — since implemented in `seed_rbac.py`).
- The §108 deliverable list (ERD document, full table/FK/constraint/index list, scope & approval-flow write-ups) was **never produced as a document** — the schema was implemented directly as migration `523de1f79d30`. There is no ERD file in the repo.
- The "STOP after Phase 1" review gate was passed and work continued into Phase 2/3. Do not re-run that gate; if desired, write the ERD retroactively as low-priority documentation.

### Phase 2 — Master data: DONE (backend)

All with backend-enforced project scope, RBAC guards, and tests:

- `projects` — full lifecycle status list (§8), tender/planned/actual dates, `award_probability` 0–100, archive/restore + `/projects/archived` listing. Files: `backend/app/models/project.py`, `backend/app/api/v1/endpoints/projects.py`, `backend/app/schemas/project.py`.
- `project_memberships` — unique `(project_id, user_id)`, validity window, `is_active`, endpoints under `/projects/{id}/memberships`.
- **Project scope enforcement (done, reusable):** `visible_project_ids()`, `user_can_access_project()`, `_require_visible_project()` in `backend/app/api/v1/endpoints/projects.py` — admin role bypasses, everyone else needs active membership, direct-ID access returns 403; list endpoints filter to visible projects.
- `project_approvers` — `approval_type` validated to `assignment | transfer | leave`, `sequence_order`, `is_required`, validity window, endpoints under `/projects/{id}/approvers`.
- `departments`, `designations` (FK to department), `employee_categories`, `trades`, `resource_providers` — `is_active` lifecycle, unique codes, shared CRUD helpers in `backend/app/api/v1/endpoints/_reference.py` (hard delete only when unreferenced, per §84).
- `employees` — unique `employee_id`, structured names, required designation, `in_house | hired` + provider rule (`_validate_source_rule`: in-house ⇒ provider NULL, hired ⇒ provider required), employment status `active | inactive | terminated`, join/termination dates, terminate/reactivate endpoint.
- Migration: `backend/alembic/versions/523de1f79d30_business_master_data_projects_.py` (applied).
- RBAC: `backend/app/scripts/seed_rbac.py` seeds `projects.*`, `project_memberships.*`, `project_approvers.*`, `master_data.*`, `employees.*`, `rates.*`, `reports.export` (plus legacy `resources.*`, `planning.*`, `reports.view`).
- Tests: `backend/tests/test_projects.py` (16 tests incl. scope/403/membership/RBAC-negative), `test_master_data.py` (6), `test_employees_rates.py` (8).
- Frontend: **not started** — `frontend/src/pages/projects-page.tsx` and `resources-page.tsx` are placeholders; `frontend/src/features/projects/` and `features/resources/` are empty dirs; frontend types exist only for auth/role/user.

### Phase 3 — Rate engine: DONE (backend)

- `backend/app/services/rates.py`: `ResolvedRate` (rate, currency, source, source record id, effective period), `resolve_rate` (employee → designation → `None`), `require_rate` (422 on missing — never a silent zero, §21), `assert_no_overlap` (409, half-open interval test), `MONTHLY_STANDARD_HOURS = 208`, `monthly_cost()` (§28 formula incl. partial-month fraction).
- Endpoints `backend/app/api/v1/endpoints/rates.py` guarded by `rates.view` / `rates.manage`.
- Tests cover: employee-over-designation precedence, historical effective dates, overlap rejection, missing-rate error, permission guards.
- Follow-ups (not blocking Phase 4):
  1. Overlap prevention is **service-level only** — no DB exclusion/range constraint (§19 "if practical"); `hourly_rate >= 0` and other §91 check constraints are API-level, not DB-level (migration has only PK/FK/unique).
  2. No index on `(designation_id, effective_from)` / `(employee_id, effective_from)` (§98).
  3. ~~`208` as a Python constant~~ — **resolved in Phase 4**: `business_settings.monthly_standard_hours` (seeded by migration) + `app/services/settings.py`; `rates.monthly_cost` now takes the configured value.

### Phase 4 — Forecast engine: DONE (backend)

- `business_settings` (key/value) with `monthly_standard_hours = 208` seeded by migration; `backend/app/services/settings.py` reads it centrally (§22). The only 208 in the backend is the fallback default in that module.
- `forecast_versions`, `forecast_lines`, `forecast_line_months` (`backend/app/models/forecast.py`, migration `9763603b7163_business_settings_and_forecast_engine.py`): DB check constraints (named ⇒ headcount = 1, headcount ≥ 1, allocation 0–100, month = first day), unique `(line, month)`, partial unique index for one current version per project+type, indexes on the line FKs.
- `backend/app/services/forecasts.py`: create (per project+type numbering), clone into a new draft, publish (re-resolve + freeze snapshots, supersede previous current in one transaction), refresh-rates, archive, draft soft delete.
- `backend/app/services/forecast_costs.py`: FTE/hours for all viewers; `hourly_rate`/`cost`/`rate_source`/`missing_rate` only with `forecasts.cost.view` (§95); published versions use frozen snapshots only — drafts fall back to live resolution; a missing rate is flagged, never zero (§21).
- Endpoints `backend/app/api/v1/endpoints/forecasts.py`: list/create/detail/patch, clone, publish, refresh-rates, archive, `DELETE` (draft only), line CRUD, bulk month upsert (`PUT /forecasts/lines/{id}/months`) — enough for the editor's fill/copy operations. Any write to a published version returns 409; project scope enforced server-side.
- Scope helpers extracted to `backend/app/api/scope.py` and reused by forecast endpoints (§9).
- RBAC: `forecasts.view/create/edit/publish/cost.view` seeded; `tests/test_roles.py` now derives expected counts from the seed catalogue.
- Tests `backend/tests/test_forecasts.py` (24): numbering, repeated designations, named/unnamed rules, month normalisation, FTE/hours, the §28 worked example (3 × 50% × 208 × 80 = 24,960), employee-over-designation precedence, missing-rate flag, publish/supersede, **frozen snapshot unchanged after rate change (§99)**, immutability, draft soft delete, archive, permission + cost-visibility gating, project scope (§104).
- Deliberate decisions:
  - Rate snapshots resolve against the **first day of each month** (UTC).
  - Drafts keep live-resolution snapshots on write and via Refresh Rates; publish always re-resolves and freezes.
  - Publishing an empty version is rejected (422); missing rates do **not** block publish — they surface as `missing_rate` for the §61 dashboard alert.
  - Month cells set to 0 are kept (blank/0 both accepted per §30).
  - Cost view is a response-shaping concern: same endpoints, fields omitted without the permission.

### Code review backlog (2026-10-08) — ALL PENDING, none fixed yet

Verified findings from an independent review of phases 2–4. Fix P0/P1 before building further on these modules; every fix deserves a regression test. Fixes should be re-verified with `uv run pytest -q` and `uv run alembic check`.

**P0 — security / data integrity**

1. **Project-scope bypass in membership/approver endpoints** (`backend/app/api/v1/endpoints/projects.py` ~381, 438, 472, 541, 589, 632). Writes resolve the project with `project_by_id()` instead of `require_visible_project()`, so a user holding only `project_memberships.manage` can grant themselves access to any project (verified 403 → 201). Every membership/approver path must enforce project scope.
2. **Publish crashes when an older draft is published while a newer version is current** (`backend/app/services/forecasts.py` ~295). Superseding the old current and flipping the new `is_current` land in one flush; SQLAlchemy orders UPDATEs by PK, tripping `uq_forecast_versions_one_current` → HTTP 500. Flush the supersede before setting `is_current = True`.
3. **`PATCH /employees` silently discards `employment_status`, `employment_source`, `resource_provider_id`** (`backend/app/api/v1/endpoints/employees.py` ~294, setattr loop omits them). A terminated employee can never be reactivated; a wrong source/provider can never be corrected.
4. **`POST /employees` drops `join_date` / `termination_date`** (`backend/app/api/v1/endpoints/employees.py` ~217 — accepted on `EmployeeIn`, never passed to the model, not exposed on `EmployeeOut`).
5. **Rate overlap check misses bounded-new vs open-ended-existing** (`backend/app/services/rates.py` ~82): `ends_inside` requires an existing end date, so e.g. `[2026-05, 2026-06]` overlapping an open-ended rate is accepted (verified) — breaks §19/#20 and makes resolution order-dependent.
6. **Lowercase `currency_code` skips the overlap check** (`backend/app/api/v1/endpoints/rates.py` ~106/168): the guard compares the raw code while the row is stored upper-cased. Canonicalise once via a validator.
7. **`DELETE /departments/{id}` silently nulls employees' department** (`backend/app/api/v1/endpoints/departments.py` ~122): the guard checks designations only while the employees FK is `SET NULL`.

**P1 — 500s / wrong status codes**

8. `DELETE /designations/{id}` referenced by a forecast line → 500 (FK restrict); add `ForecastLine` to the reference guard (`backend/app/api/v1/endpoints/designations.py` ~131).
9. `PATCH /employees` existence-checks only `designation_id`; a bad `department_id` / `employee_category_id` / `trade_id` → IntegrityError 500 (`backend/app/api/v1/endpoints/employees.py` ~260).
10. Naive datetimes → TypeError 500: rate `end` endpoints (`backend/app/api/v1/endpoints/rates.py` ~207/248) and create-path comparisons (`backend/app/services/rates.py` ~80); a browser's `2026-06-30` / `...T00:00:00` without tz must be normalised or 422 — the test suite only ever sends `...Z`.
11. `POST /employees/{id}/terminate` with a malformed date → 500 (`backend/app/api/v1/endpoints/employees.py` ~335, raw `fromisoformat`); should be 422.
12. Archived projects are not frozen for forecast writes: only `create_version` checks `archived_at`; lines can be added to and drafts published in an archived project (`backend/app/api/v1/endpoints/forecasts.py`).

**P2 — correctness / hygiene**

13. Membership `valid_from`/`valid_to` are stored and returned but never evaluated — time-boxed access never expires (`backend/app/api/scope.py` ~34; `visible_project_ids` uses the same filter).
14. `next_version_no` is an unlocked `max()+1` → concurrent create/clone 500s on the unique constraint (`backend/app/services/forecasts.py` ~87; e.g. a double-clicked "New forecast").
15. `backend/tests/conftest.py` (~78) TRUNCATE cascade also wipes `business_settings` (the seeded §22 config is never exercised — 208 assertions pass via the Python fallback) and master-data tables without a users FK accumulate across tests.
16. N+1: per-cell `resolve_rate` + lazy relationship loads → ~21 statements per line × 12 months (`backend/app/services/forecast_costs.py` ~68–130); every write endpoint rebuilds the full detail. Use `selectinload` + one batched rate lookup.
17. Missing indexes on `employee_rates.employee_id` / `designation_rates.designation_id` (the WHERE key of every rate lookup; EXPLAIN shows Seq Scan + Sort).
18. Schema duplication: `backend/app/schemas/project.py` ~222–445 duplicates the reference/employee schemas (dead), `_to_list_item`/`_to_detail` exist three times, and the `endpoints/employees.py` twin has drifted (`join_date: str` vs `datetime`).
19. `hourly_rate` has no upper bound vs `NUMERIC(14,4)` → field overflow 500 (`backend/app/api/v1/endpoints/rates.py` ~22/44); add `le=9999999999.9999`.
20. Overlap uniqueness is per-currency but resolution has no currency notion (`backend/app/services/rates.py` ~71) — two effective rates in different currencies make one silently unreachable.
21. A designation's `department_id` cannot be cleared with an explicit `null` (`backend/app/api/v1/endpoints/designations.py` ~93 uses `is not None` instead of `model_fields_set`).
22. `Decimal('NaN')` in `business_settings` → 500 on every forecast detail (`backend/app/services/settings.py` ~37); guard with `is_finite()`.
23. Whitespace-only role name stored as `""` (`backend/app/api/v1/endpoints/roles.py` ~101, `min_length` checked before `strip()`).
24. `projects.archived_by_id` is never written (audit column always NULL).
25. `RoleResponse` lost `from_attributes` (moved onto `PermissionResponse`) — latent (`backend/app/schemas/role.py` ~25–30).
26. Dead code + precision: `monthly_cost()` duplicates the §28 formula and has no callers (`backend/app/services/rates.py` ~191); costs round from binary floats (0.07% × 46.8750 → 6.83 vs 6.82 exact) (`forecast_costs.py` ~107/145).

### Decisions taken (do not re-litigate unless requirements change)

- Integer surrogate PKs everywhere (matching existing `users`/`roles`), not the UUIDs "recommended" in §8/§17.
- Lifecycle/status values are validated strings (validated in API layer) + server defaults, not PostgreSQL enums.
- Cost/rate visibility is gated by `rates.view`; the design doc's proposed `employees.cost.view` was not adopted (rate endpoints are the only place rates are returned).
- Legacy `resources.*` permissions remain in the seed; retiring them (proposed in `business_permissions_design.md`) is still pending.
- Frontend nav (`frontend/src/components/layout/navigation.ts`) still keys the Resources item on `resources.view`; revisit when the employees/master-data UI is built.
- Business settings live in a key/value `business_settings` table (not a single-row settings table) so new keys can be added without schema churn.
- Forecast months are whole months; partial-month fractioning (§39) applies only to actual assignments (Phase 5).

### Next session — start here

1. **Fix the code review backlog above, P0 first.** Suggested order: 1 → 2 → 3+4 → 5+6 → 7, then P1 (8–12), then P2 (13–15). Each fix needs a regression test; the findings describe exact reproduction steps. Finish with `uv run pytest -q` + `uv run alembic check`, then commit and push.
2. **Then Phase 4f — Forecast editor UI** (spec #30–#32): spreadsheet-style grid with sticky designation/employee columns, sticky header, horizontally scrollable month columns, keyboard navigation, fill right/range, row duplicate, percentage presets, in-grid validation, save-state indicator, and a Cost View toggle gated by `forecasts.cost.view`. The backend is ready — especially `PUT /forecasts/lines/{id}/months` for arbitrary cell batches. Frontend stack: React 19, TanStack Query 5, react-hook-form + zod, **no grid library installed** (build a custom table); follow the `features/roles/*` + `types/*` + `lib/query-keys.ts` conventions; `features/forecasts/` and `features/projects/` are empty today.
3. Then **Phase 5 — Assignment engine** (spec #33–#39): `employee_project_assignments`, assignment requests + approvals, availability engine, allocation validation under lock.
4. Remaining backlog: master-data frontend UI (Phase 2f), DB-level rate/check constraints + effective-date indexes (Phase 3 follow-ups), ERD doc (Phase 1 gap), retire legacy `resources.*` permissions.

### How to verify / update this block

- Verify: `cd backend && uv run pytest -q`; `uv run alembic current`.
- When a phase completes: flip its row to ✅ in the table, add evidence files + test names, list follow-ups, and rewrite "Next session — start here".

---

## 1. Objective

Build the business-data layer and professional resource-planning functionality for **ResourceLense**, an internal construction-company application used to:

- manage projects and tenders;
- forecast staffing requirements;
- plan manpower for jobs in hand;
- assign actual employees to projects;
- share employees between projects;
- transfer employees between projects;
- manage employee leave without changing project assignments;
- determine current and future employee availability;
- calculate staffing costs;
- identify future shortages and hiring requirements;
- provide management dashboards, reports, charts and printable PDF reports.

This specification concerns the **business domain only**.

Authentication, login, users, JWT handling, roles, permissions and general authorization/RBAC are already implemented.

Do not redesign or replace the existing authentication/authorization system.

Important distinction:

- `User` = someone who can log into ResourceLense.
- `Employee` = a staff/resource record used for manpower planning.
- An Employee does not need a User account.
- A User does not automatically represent an Employee.

Where business functionality needs to refer to application users—for example project access, approval routing, `created_by`, or `approved_by`—reference the existing User table.

---

# 2. Technology and Existing Application

Use the existing project architecture and conventions.

Frontend:

- React
- Vite
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Router
- TanStack Query
- Axios
- pnpm

Backend:

- FastAPI
- SQLAlchemy 2
- Alembic
- Pydantic v2
- PostgreSQL 16
- psycopg
- uv

Before modifying anything:

1. inspect the repository;
2. inspect existing SQLAlchemy models;
3. inspect Alembic migrations;
4. inspect APIs;
5. inspect existing RBAC/authorization;
6. inspect frontend patterns;
7. reuse existing infrastructure and conventions.

Do not duplicate existing functionality.

---

# 3. Product Quality Standard

This must be designed as a **state-of-the-art professional resource-planning application**, not as a CRUD database frontend.

At every design decision prioritize, in this order:

1. Correct business logic
2. Data integrity
3. Industry best practice
4. Auditability
5. Excellent UX
6. Clear UI
7. Performance
8. Maintainability
9. Extensibility

The application will be used regularly by management and project teams.

Resource planning screens must therefore be:

- fast;
- information-dense;
- intuitive;
- spreadsheet-like where appropriate;
- keyboard friendly;
- easy to filter;
- easy to scan;
- easy to print/export;
- resistant to data-entry mistakes.

Avoid excessive modal dialogs and unnecessary click sequences.

Use progressive disclosure: show the most important planning information immediately, with secondary detail accessible when required.

---

# 4. Core Business Questions

ResourceLense must be able to answer at any point:

1. What active projects do we have?
2. What tenders do we currently expect?
3. What manpower does each tender require?
4. What manpower does each awarded project require?
5. Which employees are currently assigned to every project?
6. At what percentage is every employee allocated?
7. Which employees are shared?
8. Which employees are available?
9. When will each employee become available?
10. Who is on leave?
11. Which employees are expected to finish their current assignments soon?
12. How many people of each designation do we currently employ?
13. How many are allocated?
14. How many are available?
15. How many more will be required?
16. When will additional hiring be necessary?
17. What would manpower demand look like if tenders are awarded?
18. What is the monthly staffing cost of each project?
19. What is the consolidated staffing cost?
20. What was forecast versus what was actually assigned?
21. Where are we understaffed?
22. Where do we have surplus capacity?
23. Which rates were applicable historically?
24. Which projects are consuming the largest resource capacity?
25. How much capacity is committed versus potential?

---

# 5. Fundamental Domain Separation

Never mix these concepts:

## A. Forecast Demand

Represents:

> What manpower a project expects to require.

Example:

Planning Engineer  
Headcount: 3

Jan: 50%  
Feb: 100%  
Mar: 100%  
Apr: 50%

These people may not yet be known.

---

## B. Actual Employee Assignment

Represents:

> Where a real employee is actually allocated.

Example:

Ahmed Hassan  
Planning Engineer  
Project A  
60%

Project B  
40%

---

## C. Transfer

Represents:

> A formal business event that changes employee assignments.

---

## D. Leave

Represents:

> Temporary employee unavailability without changing the employee's project assignment.

These four concepts must remain separate in both the database and business logic.

---

# 6. Forecast Row Philosophy

Forecasting should work using **rows representing staffing requirements**.

A forecast row contains:

- designation;
- optional actual employee;
- required headcount;
- allocation percentage for each month.

The same designation MUST be allowed to appear multiple times.

Example:

| Designation | Employee | HC | Jan | Feb | Mar | Apr |
|---|---|---:|---:|---:|---:|---:|
| Planning Engineer | Ahmed Hassan | 1 | 100 | 100 | 50 | 0 |
| Planning Engineer | VACANT / Unnamed | 2 | 50 | 100 | 100 | 100 |
| Planning Engineer | VACANT / Unnamed | 1 | 0 | 0 | 50 | 100 |

This is intentional.

Do NOT automatically consolidate rows merely because designation is the same.

Repeated rows allow:

- named and unnamed resources to coexist;
- different deployment profiles;
- different start periods;
- different percentages;
- better planning clarity.

---

# 7. Named vs Unnamed Forecast Rows

A forecast line may be either:

### Named

Employee is known.

Example:

Planning Engineer — Ahmed Hassan

Rules:

- `employee_id` is populated;
- headcount must be exactly `1`;
- employee-specific rate may apply.

### Unnamed

Only the designation is known.

Example:

Planning Engineer — 3 required

Rules:

- `employee_id` is NULL;
- headcount may be greater than 1;
- designation rate applies.

The user must be able to mix both approaches in the same forecast.

---

# 8. Project Lifecycle

Use or extend:

## `projects`

Recommended fields:

- `id` UUID PK
- `code` VARCHAR unique not null
- `name` VARCHAR not null
- `client_name` nullable
- `location` nullable
- `description` nullable

Status:

- `tender`
- `awarded`
- `active`
- `on_hold`
- `completed`
- `lost`
- `cancelled`

Dates:

- `tender_start_date`
- `tender_submission_date`
- `expected_award_date`
- `planned_start_date`
- `planned_end_date`
- `actual_start_date`
- `actual_end_date`

Tender planning:

- `award_probability` NUMERIC(5,2) nullable

System:

- `created_at`
- `updated_at`
- `created_by`
- `updated_by`

Optional archival:

- `archived_at`
- `archived_by`

Do not treat `archived` as a business project status.

Archiving is a UI/data-retention concept.

---

# 9. Project Access Scope

Users must NOT automatically see every project.

Normal users only see projects to which they have been granted access.

Admin/Super User can see all projects.

Create, unless equivalent functionality already exists:

## `project_memberships`

Fields:

- `id`
- `project_id`
- `user_id`
- `valid_from` nullable
- `valid_to` nullable
- `is_active`
- `created_at`
- `created_by`

Unique:

`project_id + user_id`

This table defines **scope**, not permissions.

The existing RBAC system continues to determine what actions the user is authorized to perform.

Example:

A user may have RBAC permission:

`forecast:view`

but only see forecasts for projects included in `project_memberships`.

Admin/Super User bypasses project scope.

Never rely solely on frontend filtering.

Project access must be enforced by backend APIs.

---

# 10. Project Approvers

Project-level business approval is different from application authorization.

Create:

## `project_approvers`

Fields:

- `id`
- `project_id`
- `user_id`
- `approval_type`
- `sequence_order`
- `is_required`
- `valid_from`
- `valid_to`
- `is_active`
- timestamps

Possible `approval_type`:

- `assignment`
- `transfer`
- `leave`

This enables each project to nominate authorized business approvers.

Existing RBAC still determines whether the user is technically allowed to approve.

Both conditions should be satisfied when applicable.

---

# 11. Departments

## `departments`

Fields:

- `id`
- `code`
- `name`
- `description`
- `sort_order`
- `is_active`
- timestamps

Examples:

- Engineering
- Commercial
- QA/QC
- HSE
- Construction
- Planning
- Administration

---

# 12. Designations

## `designations`

Fields:

- `id`
- `code`
- `name`
- `department_id`
- `description`
- `sort_order`
- `is_active`
- timestamps

Examples:

- Project Director
- Project Manager
- Construction Manager
- MEP Manager
- Planning Engineer
- Electrical Engineer
- Mechanical Engineer
- QA/QC Engineer
- HSE Engineer
- Document Controller

Designations are fundamental because manpower can be forecast before actual names are known.

---

# 13. Employee Categories

If employee category remains useful for reporting/classification, keep:

## `employee_categories`

Fields:

- `id`
- `code`
- `name`
- `description`
- `is_active`

Employee category has absolutely **no relationship to hourly-rate resolution**.

There are no category rates.

Do not implement category rate tables.

Do not implement category rate fallback.

Do not create category-rate business logic.

---

# 14. Trades

If useful for labour/resource analysis:

## `trades`

Fields:

- `id`
- `code`
- `name`
- `description`
- `is_active`

Examples:

- Electrical
- Mechanical
- Plumbing
- Civil
- General

Trade is not the same as designation.

---

# 15. In-House vs Hired Employees

Resource source must clearly indicate whether an employee is:

- `in_house`
- `hired`

This should be directly available on the employee record.

Recommended:

`employment_source`

enum or constrained string:

- `in_house`
- `hired`

Do not create a generic Employee Sources table unless a future requirement genuinely requires more source types.

For the current requirement, a two-value source field is clearer and simpler.

---

# 16. External Resource Providers

Do NOT create separate `vendors` and `third_parties` tables.

Use one generalized table:

## `resource_providers`

This represents companies supplying hired manpower.

Fields:

- `id`
- `code`
- `name`
- `legal_name` nullable
- `contact_person` nullable
- `email` nullable
- `phone` nullable
- `notes` nullable
- `is_active`
- timestamps

Examples:

- manpower supplier;
- recruitment company;
- subcontract manpower provider;
- third-party staffing organization.

This eliminates ambiguous vendor/third-party duplication.

---

# 17. Employees

## `employees`

Fields:

- `id` UUID PK
- `employee_id` VARCHAR unique not null
- `full_name` VARCHAR not null

Optional structured names:

- `first_name`
- `middle_name`
- `last_name`

Organization:

- `designation_id` FK not null
- `department_id` FK nullable if derived from designation
- `employee_category_id` FK nullable
- `trade_id` FK nullable

Employment source:

- `employment_source` = `in_house` or `hired`
- `resource_provider_id` nullable

Rules:

If:

`employment_source = in_house`

then:

`resource_provider_id IS NULL`

If:

`employment_source = hired`

then:

`resource_provider_id IS NOT NULL`

Employment:

- `employment_status`
- `join_date`
- `termination_date`

Recommended status:

- `active`
- `inactive`
- `terminated`

Optional:

- email
- phone
- notes

System:

- `created_at`
- `updated_at`
- `created_by`
- `updated_by`

Do NOT store:

`current_project_id`

inside Employee.

Current assignment must always be derived from effective-dated assignment records.

---

# 18. Hourly Rate Architecture

There are ONLY two possible rate sources:

1. employee-specific hourly rate;
2. designation hourly rate.

Precedence:

**Employee Rate > Designation Rate**

There are no category rates.

---

# 19. Designation Rate History

## `designation_rates`

Fields:

- `id`
- `designation_id`
- `hourly_rate` NUMERIC(14,4)
- `currency_code` VARCHAR(3)
- `effective_from`
- `effective_to` nullable
- `notes`
- `created_at`
- `created_by`

Rules:

- rate >= 0;
- effective periods must not overlap for the same designation/currency;
- only one rate can be applicable on a given date.

Use a PostgreSQL exclusion/range constraint if practical.

---

# 20. Employee Rate History

## `employee_rates`

Fields:

- `id`
- `employee_id`
- `hourly_rate` NUMERIC(14,4)
- `currency_code`
- `effective_from`
- `effective_to`
- `notes`
- `created_at`
- `created_by`

Prevent overlapping effective periods.

---

# 21. Rate Resolution

For a named employee and target date:

1. Find effective employee rate.
2. If found, use it.
3. Otherwise find effective designation rate.
4. If found, use designation rate.
5. Otherwise return a missing-rate validation warning/error.

Never silently substitute zero.

For unnamed forecast lines:

Use designation rate.

Rate resolution should return:

- rate;
- currency;
- source;
- source record ID;
- effective period.

Centralize this in:

`RateResolutionService`

Do not reproduce rate-selection logic across endpoints.

---

# 22. Standard Monthly Hours

For resource-planning calculations:

**100% allocation for one complete month = 208 hours**

Store this centrally as configurable business configuration.

Example:

## `business_settings`

or existing settings infrastructure:

`monthly_standard_hours = 208`

Do not hard-code `208` independently in multiple frontend/backend locations.

---

# 23. Forecast Versioning

Forecasts must be versioned.

## `forecast_versions`

Fields:

- `id`
- `project_id`
- `forecast_type`
- `version_no`
- `name`
- `status`
- `forecast_date`
- `description`
- `is_current`
- `created_by`
- `created_at`
- `updated_at`
- `published_at`
- `published_by`
- `superseded_at`
- `superseded_by`

Forecast type:

- `tender`
- `job`

Status:

- `draft`
- `published`
- `superseded`
- `archived`

Only one current forecast of each relevant type per project.

Published forecasts are immutable.

To revise:

Clone the current published version into a new draft.

Example:

Tender Forecast V1  
Tender Forecast V2

After award:

Job Forecast V1  
Job Forecast V2

Never overwrite historical versions.

---

# 24. Forecast Lines

Create:

## `forecast_lines`

Fields:

- `id`
- `forecast_version_id`
- `designation_id`
- `employee_id` nullable
- `headcount`
- `notes`
- `sort_order`
- timestamps

Rules:

For named line:

`employee_id IS NOT NULL`

therefore:

`headcount = 1`

For unnamed line:

`employee_id IS NULL`

therefore:

`headcount >= 1`

Duplicate designation rows MUST be allowed.

Do not add a unique constraint on:

`forecast_version_id + designation_id`

because repeated designations are intentional.

---

# 25. Monthly Forecast Deployment

Database normalization and UI presentation are different concerns.

UI:

months MUST appear as columns.

Database:

months MUST be rows.

Create:

## `forecast_line_months`

Fields:

- `id`
- `forecast_line_id`
- `month`
- `allocation_percentage`
- `resolved_hourly_rate_snapshot` nullable
- `rate_source_snapshot` nullable
- `rate_source_id_snapshot` nullable
- `currency_code_snapshot` nullable
- timestamps

Unique:

`forecast_line_id + month`

Month stored as first day:

`YYYY-MM-01`

Allocation:

0–100%.

Example:

| Designation | Employee | HC | Jan | Feb | Mar | Apr |
|---|---|---:|---:|---:|---:|---:|
| Project Manager | John | 1 | 100 | 100 | 100 | 100 |
| Planning Engineer | Ahmed | 1 | 50 | 100 | 100 | 50 |
| Planning Engineer | — | 2 | 0 | 50 | 100 | 100 |

---

# 26. Forecast Does NOT Store Monetary Cost

Do NOT store:

- `monthly_cost`
- `forecast_total_cost`

inside forecast tables.

They are derived values.

The forecast records only:

- resource;
- designation;
- optional employee;
- headcount;
- monthly allocation percentage;
- frozen rate information where required for historical reproducibility.

Calculate costs on demand.

This prevents duplicated derived data from becoming inconsistent.

---

# 27. Why Rate Snapshots Are Still Required

Although monetary cost is calculated dynamically, published historical forecasts must remain financially reproducible.

Example:

Tender prepared October 2026.

Planning Engineer rate:

AED 80/hour.

Rate changes later to:

AED 90/hour.

The October tender must still calculate using:

AED 80/hour.

Therefore:

### Draft Forecast

Rate may resolve from current effective rate.

Provide action:

**Refresh Rates**

### Published Forecast

Freeze:

- resolved rate;
- rate source;
- currency;
- source rate record.

Do NOT freeze calculated cost.

Cost remains calculated using the frozen rate.

This gives both:

- normalized data;
- reliable historical pricing.

---

# 28. Forecast Cost Calculation

### Unnamed line

Formula:

`headcount × allocation_percentage / 100 × 208 × designation_rate`

Example:

3 Planning Engineers  
50% allocation  
AED 80/hour

`3 × 0.50 × 208 × 80`

= AED 24,960

---

### Named line

Resolve employee rate first.

If none:

designation rate.

Formula:

`1 × allocation_percentage / 100 × 208 × resolved_rate`

---

# 29. FTE Definition

FTE means:

**Full-Time Equivalent**

It expresses manpower demand as the equivalent number of employees working full time.

Examples:

1 employee at 100%:

`1.0 FTE`

1 employee at 50%:

`0.5 FTE`

2 employees each at 50%:

`1.0 FTE`

3 employees at 100%:

`3.0 FTE`

For a forecast line:

`FTE = headcount × allocation_percentage / 100`

Example:

4 Planning Engineers at 75%:

`4 × 0.75 = 3.0 FTE`

Use FTE heavily in consolidated resource reports because it allows meaningful comparison across shared resources.

---

# 30. Forecast Editor UX

This is one of the most important screens in ResourceLense.

It should behave like a modern resource-planning spreadsheet.

The planner must see the **entire forecast across months**.

Example:

| Designation | Employee | HC | Jan 27 | Feb 27 | Mar 27 | Apr 27 | May 27 |
|---|---|---:|---:|---:|---:|---:|---:|

Monthly cells contain allocation percentage.

Required UX features:

- sticky designation/name columns;
- horizontally scrollable month columns;
- sticky table header;
- compact professional row height;
- keyboard navigation;
- Enter/Tab navigation;
- copy/paste;
- multi-cell selection where practical;
- drag/fill across months;
- fill right;
- fill selected months;
- clear selected cells;
- set percentage for date range;
- duplicate row;
- add row below;
- reorder rows;
- designation autocomplete;
- employee autocomplete;
- fast employee search;
- contextual employee availability;
- undo unsaved edits where practical;
- autosave draft or clear save-state indicator;
- unsaved-change warning;
- validation visible directly inside the table.

Monthly input should accept:

- blank / 0
- 25
- 50
- 75
- 100

but also any valid percentage 0–100.

Provide quick presets.

---

# 31. Forecast UI Calculations

Do not clutter the grid with excessive financial details.

Primary grid should focus on manpower.

For each row optionally display calculated summary:

- average FTE;
- active months;
- total equivalent hours.

Provide a separate toggle or side panel for:

**Cost View**

where calculations such as:

- monthly cost;
- total cost;
- hourly rate;
- rate source

can be displayed.

The manpower-planning table should remain visually clean.

---

# 32. Existing Resource Visibility While Forecasting

When selecting a named employee or designation, provide resource availability information.

Example employee selection:

**Ahmed Hassan — Planning Engineer**

Jan:
Project A 100%

Feb:
Project A 100%

Mar:
Project A 50%

Apr:
Available 100%

This information should be visible without navigating away from the forecast.

Recommended UX:

- inline popover;
- side drawer;
- employee availability mini-timeline.

For designation search show:

- active employee count;
- currently available;
- becoming available;
- fully allocated;
- hired/in-house breakdown.

This allows planners to judge hiring requirements immediately.

---

# 33. Actual Employee Assignments

Create:

## `employee_project_assignments`

Fields:

- `id`
- `employee_id`
- `project_id`
- `start_date`
- `end_date` nullable
- `allocation_percentage`
- `assignment_source`
- `source_document_type` nullable
- `source_document_id` nullable
- `status`
- `notes`
- timestamps
- created/updated users

Recommended status:

- `planned`
- `active`
- `ended`
- `cancelled`

Assignment source:

- `initial_assignment`
- `transfer`
- `manual_adjustment`

Employees may have simultaneous project assignments.

Example:

Project A — 60%  
Project B — 40%

Total:

100%.

---

# 34. Formal Assignment Request / Assignment Form

Initial assignment should be a polished business workflow, not direct editing of assignment rows.

Create:

## `assignment_requests`

Fields:

- `id`
- `assignment_no`
- `employee_id`
- `target_project_id`
- `start_date`
- `planned_end_date`
- `allocation_percentage`
- `status`
- `reason`
- `remarks`
- `created_by`
- `created_at`
- `submitted_at`
- `approved_at`
- `cancelled_at`

Status:

- `draft`
- `submitted`
- `approved`
- `rejected`
- `cancelled`

The data-entry form should clearly display the employee's **current assignment(s)** even though current project is not stored directly on Employee.

Example:

CURRENT ALLOCATION

Project A — 70%  
Project B — 30%

PROPOSED ASSIGNMENT

Project C — 40%

Result:

Project A — 70%  
Project B — 30%  
Project C — 40%

TOTAL 140%

BLOCKED.

The purpose of showing current project(s) is clarity for the approver and data-entry user.

The system still derives them from assignments.

---

# 35. Approval Workflow

Assignments should only become effective after required approvals.

Approvals must be recorded.

Use a reusable approval mechanism.

Recommended:

## `document_approvals`

Fields:

- `id`
- `document_type`
- `document_id`
- `project_id`
- `approver_user_id`
- `sequence_order`
- `status`
- `decision_at`
- `comments`
- `created_at`

Status:

- `pending`
- `approved`
- `rejected`
- `cancelled`

Possible document types:

- `assignment`
- `transfer`
- `leave`

Business-document status remains in its own table.

Approval history must never disappear when project approvers are later changed.

Capture the approver at submission time.

---

# 36. Assignment Approval Scope

For initial assignment:

Target project approval is normally required.

If the proposed assignment reduces/removes allocation from another project, that becomes a transfer and should use the transfer workflow instead.

Do not silently reduce another project's assignment through an assignment form.

---

# 37. Allocation Validation

Total simultaneous project allocation must normally not exceed:

**100%**

Validation must consider overlapping date ranges.

Example:

Project A:
70%

Project B:
40%

Same dates:

110%

Reject.

This validation must run:

- during data entry for immediate UX feedback;
- again on the backend;
- again inside the final approval transaction.

Never trust frontend-only validation.

---

# 38. Monthly Cost of Actual Assigned Employee

For a full month:

Employee on one project at 100%:

`208 × hourly_rate`

Employee shared:

Project A 60%:

`208 × rate × 0.60`

Project B 40%:

`208 × rate × 0.40`

Total employee monthly hours:

`124.8 + 83.2 = 208`

Therefore the employee's full monthly cost is distributed pro rata across projects.

The total across all concurrent projects must not exceed the cost equivalent of 208 hours unless an explicit future overtime mechanism is implemented.

Do not treat a shared employee as costing 208 hours separately on every project.

---

# 39. Partial-Month Assignments

Assignments and transfers may start/end mid-month.

For monthly planning projections:

`effective_monthly_hours = 208 × allocation_percentage × active_month_fraction`

Where allocation percentage is expressed as decimal.

Default partial-month fraction:

`active_calendar_days / total_calendar_days_in_month`

Centralize this rule.

Do not duplicate it across frontend and backend.

If the company later introduces an official project-working-calendar system, this calculation can be replaced by working-day/hour calendars without changing the core assignment architecture.

---

# 40. Transfers

Transfers must be formal business events.

Do NOT simply edit old assignments.

Create:

## `employee_transfers`

Fields:

- `id`
- `transfer_no`
- `employee_id`
- `effective_date`
- `planned_end_date` nullable
- `target_project_id`
- `target_allocation_percentage`
- `status`
- `reason`
- `remarks`
- `created_by`
- `created_at`
- `submitted_at`
- `approved_at`
- `rejected_at`
- `cancelled_at`

Status:

- `draft`
- `submitted`
- `approved`
- `rejected`
- `cancelled`

---

# 41. Transfer Sources

Because employees may be shared across multiple projects:

## `employee_transfer_sources`

Fields:

- `id`
- `transfer_id`
- `source_assignment_id`
- `source_project_id`
- `previous_allocation_percentage`
- `new_allocation_percentage`
- timestamps

The system determines current assignments.

The user should not manually type an arbitrary "source project".

---

# 42. Transfer Form UX

The transfer form must visually show:

### EMPLOYEE

Ahmed Hassan  
Planning Engineer

### CURRENT ALLOCATION

Project A — 60%  
Project B — 40%

### PROPOSED CHANGE

Move 40% to Project C

### RESULT AFTER TRANSFER

Project A — 60%  
Project B — 0%  
Project C — 40%

Total allocated:

100%

Or if full transfer:

BEFORE:

Project A — 100%

AFTER:

Project A — 0%  
Project B — 100%

This before/after view is mandatory.

The user should understand the consequence before submitting.

---

# 43. Transfer Approvals

Transfer approval should involve the relevant project authorities.

Depending on the transfer:

- source project approver(s);
- destination project approver(s).

For employees shared across several projects, only projects whose allocation is being changed need source approval.

Approval workflow should make clear:

- pending with whom;
- approval order;
- approved/rejected status;
- comments.

Admin/Super User may have elevated workflow rights according to existing authorization policy.

---

# 44. Transfer Transaction Integrity

Approving a transfer must execute in one database transaction.

The transaction must:

1. lock relevant employee assignment state;
2. recalculate overlapping allocations;
3. validate <=100%;
4. end/change relevant source assignment(s);
5. create/update destination assignment;
6. store transfer history;
7. update transfer status;
8. finalize approval.

All succeed or all fail.

Never allow partially applied transfer state.

---

# 45. Leave Management

Leave does not transfer the employee.

Create:

## `leave_types`

Fields:

- `id`
- `code`
- `name`
- `is_paid` nullable if useful
- `is_active`

Examples:

- Annual Leave
- Sick Leave
- Emergency Leave
- Unpaid Leave
- Other

---

## `employee_leaves`

Fields:

- `id`
- `leave_no`
- `employee_id`
- `leave_type_id`
- `start_date`
- `end_date`
- `status`
- `remarks`
- `created_by`
- `created_at`
- `submitted_at`
- `approved_at`
- `rejected_at`
- `cancelled_at`

Status:

- `draft`
- `submitted`
- `approved`
- `rejected`
- `cancelled`

---

# 46. Leave Behaviour

Example:

Ahmed:

Project A — 100%  
Assignment through 30 June.

Leave:

10 March to 20 March.

Do NOT modify Project A assignment.

During leave:

Project Assignment:
Project A — 100%

Operational Status:
On Leave

Leave Until:
20 March

On 21 March:

Employee automatically returns to normal operational status.

No transfer is required.

---

# 47. Employee Status Is Derived

Do not store:

`current_project`

or:

`current_status = Project A`

on the employee record.

For a given date derive:

- employment status;
- active project assignments;
- assignment percentages;
- leave;
- total allocation;
- available percentage;
- next assignment end;
- expected release date.

---

# 48. Availability Engine

Implement:

`ResourceAvailabilityService`

Input:

- employee;
- date or range.

Return:

- project assignments;
- allocation by project;
- total allocated percentage;
- remaining project capacity;
- leave status;
- leave dates;
- expected release dates;
- operational availability.

Do not scatter this logic through controllers.

---

# 49. Availability Semantics

Distinguish:

### Project Capacity

`100% - active project assignment percentages`

### Operational Availability

Whether the person is actually available to work.

An employee may have:

Project Capacity:
0%

Operational Status:
On Leave

Or:

Project Capacity:
50%

Operational Status:
Available for additional 50%

Do not treat leave as a project.

---

# 50. Future Availability

For planning, calculate:

- next assignment ending;
- next reduction in allocation;
- next date 25% available;
- next date 50% available;
- next date 100% available.

This is extremely useful for planners selecting staff for upcoming projects.

---

# 51. Hiring Requirement

For each designation/month calculate demand versus internal capacity.

Use FTE.

Example:

Planning Engineer

Project A demand:
3.0 FTE

Project B demand:
2.0 FTE

Tender C:
1.5 FTE

Total demand:

6.5 FTE

Available internal capacity:

5.0 FTE

Resource gap:

1.5 FTE

Meaning:

The company needs the equivalent capacity of 1.5 full-time Planning Engineers during that month.

This may mean:

- hire 2 people;
- hire 1 person and share another;
- use a resource becoming available from another project;
- change project staffing plan.

---

# 52. Tender Probability

Tender demand must remain distinct from committed projects.

Dashboard scenarios:

### Committed

Awarded/active projects only.

### Potential

Tender demand.

### Combined

Committed + tender.

### Probability Weighted

Optional planning scenario:

`Tender FTE × award probability`

Example:

10 FTE required  
40% award probability

Raw potential demand:

10 FTE

Weighted planning demand:

4 FTE

Always retain and display raw tender demand.

Probability-weighted demand is a scenario, not a replacement.

---

# 53. Forecast vs Actual

Per:

- project;
- designation;
- month;

show:

- forecast headcount;
- forecast FTE;
- actual named headcount;
- actual FTE;
- FTE variance;
- estimated forecast cost;
- projected actual cost;
- cost variance.

Forecast monetary values are calculated dynamically from frozen published rate snapshots.

Actual projected costs use effective current/historical rate logic.

---

# 54. Recommended Dashboard

Create an executive-quality dashboard.

Avoid putting every possible metric on one page.

Use meaningful sections.

## KPI Cards

Recommended:

- Active Projects
- Active Tenders
- Active Employees
- In-House Employees
- Hired Employees
- Fully Allocated Employees
- Partially Allocated Employees
- Available Employees
- Employees on Leave
- Employees Releasing in 30 Days
- Employees Releasing in 60 Days
- Employees Releasing in 90 Days
- Resource Gap Next Month
- Current Monthly Staff Cost
- Next-Month Forecast Cost

Cards should be clickable and open the underlying filtered report where useful.

---

# 55. Dashboard Chart — Demand vs Capacity

Line/area chart:

X-axis:

Month

Series:

- internal capacity;
- committed project demand;
- tender demand;
- combined demand.

Optional scenario toggle:

- raw;
- probability weighted.

This should be one of the primary management charts.

---

# 56. Dashboard Chart — Hiring Gap by Designation

Recommended horizontal bar chart.

Show:

Designation  
Required FTE  
Available Internal FTE  
Gap

Highlight significant shortages.

Allow month selector.

---

# 57. Dashboard Chart — Monthly Manpower Trend

Stacked or grouped chart showing:

- committed FTE;
- tender FTE;
- in-house assigned FTE;
- hired assigned FTE.

This reveals whether the company is becoming more dependent on external manpower.

---

# 58. Dashboard Chart — Staff Cost Trend

Monthly chart:

- committed project staff cost;
- tender potential staff cost;
- actual/projected staff cost.

Use currency formatting.

Allow:

- total portfolio;
- project;
- department;
- designation.

---

# 59. Dashboard Chart — Resource Mix

Show:

- in-house;
- hired.

Can be summarized by:

- headcount;
- FTE;
- cost.

Avoid decorative pie charts when a bar/donut does not communicate useful information.

---

# 60. Dashboard — Upcoming Releases

Provide table:

- employee;
- designation;
- current project;
- current allocation;
- release/reduction date;
- percentage becoming available.

Filters:

- next 30 days;
- 60 days;
- 90 days;
- custom period.

This is a critical planning widget.

---

# 61. Dashboard — Over/Under Allocation Alerts

Show actionable exceptions:

- employee >100% allocated;
- forecast row without rate;
- employee whose assignment ended but remains shown as active;
- missing project approver;
- upcoming project demand without capacity;
- transfer awaiting approval;
- leave awaiting approval;
- expired hired resource assignment;
- missing designation rate.

Management dashboards should emphasize exceptions requiring attention.

---

# 62. Dashboard — Tender Pipeline Resource Impact

Table/chart:

| Tender | Probability | Start | Peak FTE | Primary Shortage | Forecast Staff Cost |

Allow sorting by:

- probability;
- expected award;
- manpower requirement;
- financial impact.

---

# 63. Resource Planning Matrix

One of the application's primary views.

Modes:

### Employee Mode

Rows:

employees

Columns:

months

Cells:

project allocation.

Example:

Ahmed

Jan:
Project A 100%

Feb:
Project A 100%

Mar:
A 60% / B 40%

Apr:
Available 50%

---

### Designation Mode

Rows:

designations

Columns:

months

Cells:

- required FTE;
- available FTE;
- gap.

---

Filters:

- date range;
- project;
- project status;
- department;
- designation;
- employee;
- source: in-house/hired;
- provider;
- employee category;
- trade;
- tender/job;
- availability.

---

# 64. Visual Resource Matrix Rules

Use visual indicators for:

- available;
- partial allocation;
- full allocation;
- overallocated;
- leave;
- vacancy;
- tender demand.

Do not rely on color alone.

Use:

- percentage text;
- icons;
- labels;
- tooltips.

Color palette should be accessible and consistent.

---

# 65. Reports

Implement dedicated backend report queries/services.

Do not build reports by downloading raw CRUD endpoints and joining everything in React.

Recommended reports follow.

---

# 66. Report — Project Manpower Plan

For a selected project:

- designation;
- named employee where applicable;
- required headcount;
- monthly allocation;
- monthly FTE;
- monthly projected hours.

Optional Cost View:

- hourly rate;
- monthly staff cost.

Suitable for tender and job forecast.

---

# 67. Report — Actual Project Manpower

For selected project:

- employee ID;
- employee name;
- designation;
- department;
- source;
- provider if hired;
- assignment percentage;
- assignment start;
- assignment end;
- leave status;
- applicable rate;
- projected monthly cost.

---

# 68. Report — Consolidated Resource Plan

Portfolio report.

Rows:

designation

Columns:

months

Values:

- committed demand;
- tender demand;
- internal capacity;
- hired capacity;
- gap.

Provide drill-down from designation/month into individual employees/projects.

---

# 69. Report — Employee Allocation

Rows:

employees

Columns:

months

Show:

- project;
- percentage;
- leave;
- available percentage.

This should also be exportable in landscape PDF.

---

# 70. Report — Employee Availability

Show:

- employee;
- designation;
- in-house/hired;
- current project(s);
- current allocation;
- remaining capacity;
- leave;
- next release;
- next full availability.

---

# 71. Report — Hiring Requirement

By:

- month;
- designation.

Show:

- demand FTE;
- internal FTE;
- hired FTE;
- deficit;
- recommended additional headcount equivalent.

Optional filters:

- committed only;
- include tenders;
- probability weighted.

---

# 72. Report — Tender Manpower Forecast

Show:

- tender;
- designation;
- employee if named;
- headcount;
- monthly allocation;
- monthly FTE;
- peak demand.

Optional cost section.

---

# 73. Report — Jobs-in-Hand Forecast

Same structure but exclusively:

- awarded;
- active;
- on-hold as appropriate.

Keep separately identifiable from tender report.

---

# 74. Report — Forecast vs Actual

By project/designation/month:

- forecast FTE;
- actual FTE;
- variance;
- forecast estimated cost;
- projected actual cost;
- financial variance.

---

# 75. Report — Staff Cost by Project

Monthly:

- project;
- employee/designation;
- FTE;
- projected hours;
- hourly rate;
- source of rate;
- calculated cost.

Totals:

- monthly;
- project;
- portfolio.

---

# 76. Report — Cost by Designation

Useful for management.

Show:

- designation;
- headcount;
- FTE;
- average effective hourly rate;
- monthly cost;
- annualized/projected cost.

---

# 77. Report — In-House vs Hired

Show:

- headcount;
- FTE;
- cost;
- percentage of workforce;
- designation;
- project;
- month.

This helps management understand dependency on external manpower.

---

# 78. Report — Transfer History

Show:

- transfer number;
- employee;
- designation;
- source project(s);
- destination project;
- previous percentages;
- new percentages;
- effective date;
- approvers;
- status.

---

# 79. Report — Leave

Show:

- leave number;
- employee;
- designation;
- assigned project(s);
- leave type;
- start;
- end;
- duration;
- status.

---

# 80. Report — Rate History

Restricted to users allowed to view cost information.

Show:

- employee/designation;
- rate;
- effective from;
- effective to;
- currency;
- created by.

---

# 81. PDF Reporting

Reports must be printable in professional PDF format.

Do not simply print browser screens.

Use proper report templates generated server-side or through a controlled HTML-to-PDF rendering pipeline.

Recommended implementation:

HTML/CSS report templates rendered through Playwright/Chromium or an equivalent reliable PDF engine already compatible with the application infrastructure.

PDF requirements:

- company logo;
- report title;
- project name/code where applicable;
- selected filters;
- generated date/time;
- generated by;
- page X of Y;
- consistent header/footer;
- repeating table headers;
- sensible page breaks;
- no clipped rows;
- print-safe fonts;
- professional spacing;
- proper currency formatting.

Use:

- A4 portrait for detail reports;
- A4 landscape for allocation matrices;
- optional A3 landscape for extremely wide monthly manpower matrices if required.

---

# 82. PDF Report Styling

Reports should look like formal corporate documents.

Do not reproduce dashboard styling in PDF.

Use:

- clean white background;
- strong report title;
- small metadata section;
- compact tables;
- subtotals;
- grand totals;
- zebra striping only if it improves readability;
- clear section headings;
- footnotes where calculations require explanation.

For management reports, include a concise summary section before detail.

---

# 83. PDF Export Options

Where useful provide:

- PDF
- Excel/XLSX
- CSV

PDF is for presentation/records.

Excel is for further analysis.

Do not force users to use PDF when a spreadsheet is more appropriate.

---

# 84. Soft Delete Strategy

Do NOT automatically add soft-delete to every table.

"Soft delete everything" creates hidden-data complexity and is not good design.

Use the following rules.

---

## Master Reference Data

For:

- departments;
- designations;
- employee categories;
- trades;
- resource providers;
- leave types;

use:

`is_active`

rather than delete.

Inactive records:

- no longer selectable for new transactions;
- remain visible in historical transactions.

Hard delete may be allowed only if the record has never been referenced.

---

# 85. Employees

Do not "soft delete" normal employees.

Use:

`employment_status`

and termination date.

An employee leaving the company becomes:

`terminated`

Historical assignments remain intact.

If an Employee record was created completely by mistake and has never been referenced, hard delete may be allowed to authorized administrators.

---

# 86. Projects

Use project status and archive functionality.

Do not soft-delete projects with transactions.

Completed/lost/cancelled projects remain part of history.

For UI cleanliness:

- archive them;
- hide archived projects by default;
- allow "Show Archived".

---

# 87. Forecasts

Published forecasts:

never delete.

Use:

- superseded;
- archived.

Draft forecast versions may use soft delete:

- `deleted_at`
- `deleted_by`

This permits recovery from accidental deletion while being edited.

Forecast lines/month cells inside an unpublished draft may be physically removed as normal editing operations.

---

# 88. Rates

Do not delete historical rate records once effective/used.

Incorrect rates should be:

- ended;
- corrected;
- or explicitly voided if entered entirely in error.

If implementing void:

- `is_void`
- `voided_at`
- `voided_by`
- `void_reason`

Never silently remove rates that may explain historical cost calculations.

---

# 89. Assignments, Transfers and Leave

Approved records must never be deleted.

Use statuses:

- cancelled;
- rejected;
- ended;
- superseded where applicable.

Draft business forms may use soft delete:

- `deleted_at`
- `deleted_by`

Approved records require cancellation/void workflows with audit trail.

---

# 90. Auditability

Important records must capture:

- created by;
- created at;
- updated by;
- updated at;
- submitted by;
- submitted at;
- approved/rejected by;
- decision time;
- cancellation;
- reason/comments.

Use existing audit infrastructure where available.

Do not create a competing audit framework unnecessarily.

---

# 91. Database Constraints

Use PostgreSQL constraints wherever practical.

Examples:

Allocation:

`0 < allocation_percentage <= 100`

Forecast deployment:

`0 <= allocation_percentage <= 100`

Rates:

`hourly_rate >= 0`

Award probability:

`0 <= award_probability <= 100`

Headcount:

`headcount >= 1`

Dates:

`end_date >= start_date`

Use FK constraints.

Use unique indexes for:

- project code;
- designation code;
- department code;
- employee ID;
- provider code;
- leave-type code.

Use NUMERIC for money.

Never FLOAT for monetary values.

---

# 92. Concurrency Protection

Assignment planning is concurrency sensitive.

Example:

Admin A assigns Ahmed 60% to Project A.

At the same time:

Admin B assigns Ahmed 60% to Project B.

Both may initially appear valid.

Together:

120%.

Prevent this.

Use PostgreSQL transaction locking/advisory locking as appropriate.

Before final approval/commit:

recalculate employee allocation under lock.

---

# 93. Business Services

Implement clear domain services.

Recommended:

- `RateResolutionService`
- `ForecastService`
- `ForecastCostService`
- `ResourceAvailabilityService`
- `AssignmentService`
- `TransferService`
- `LeaveService`
- `ResourcePlanningService`
- `ReportingService`
- `ApprovalWorkflowService`

Business-critical calculations must not be spread through route handlers or React components.

---

# 94. API Areas

Recommended logical areas:

`/projects`

`/departments`

`/designations`

`/employees`

`/resource-providers`

`/rates`

`/forecasts`

`/assignments`

`/transfers`

`/leave`

`/resource-planning`

`/reports`

`/dashboard`

Do not expose the database as raw CRUD only.

Use explicit business actions.

Examples:

- publish forecast;
- clone forecast;
- refresh draft forecast rates;
- submit assignment;
- approve assignment;
- reject assignment;
- submit transfer;
- approve transfer;
- reject transfer;
- cancel transfer;
- calculate availability;
- get resource matrix;
- export report.

---

# 95. UI Security and Cost Visibility

Some project users may be allowed to view manpower but not financial cost/rates.

Use existing RBAC permissions to separate:

- manpower visibility;
- cost visibility;
- rate editing;
- forecast editing;
- transfer approval;
- leave approval;
- report export.

Do not expose hourly rates through API responses to users without cost permission.

Backend must enforce this.

---

# 96. Search and Filtering UX

Large tables must support:

- fast search;
- multi-filter;
- saved filters where practical;
- sortable columns;
- configurable visible columns;
- sticky headers;
- pagination or virtual scrolling when needed;
- URL-persisted filters where useful.

Do not make users repeatedly recreate common report filters.

---

# 97. Employee Search UX

Employee selectors should display enough context to avoid choosing the wrong person.

Example:

Ahmed Hassan  
EMP-0183  
Planning Engineer  
In-House  
Currently: Project A 60%, Available 40%

For hired employee:

Mohammed Ali  
EMP-0421  
QA/QC Engineer  
Hired — ABC Manpower  
Project B 100%

---

# 98. Performance

Resource matrices may involve:

employees × projects × months.

Avoid hundreds of frontend API requests.

Create dedicated aggregate endpoints.

Indexes should cover commonly filtered/joined fields:

- project_id;
- employee_id;
- designation_id;
- department_id;
- resource_provider_id;
- assignment dates;
- forecast_version_id;
- forecast_line_id;
- forecast month;
- effective-rate dates;
- project status.

Use `EXPLAIN ANALYZE` when optimizing actual bottlenecks.

Do not prematurely denormalize.

---

# 99. Testing — Rates

Test:

- employee rate overrides designation;
- designation fallback;
- historical effective date;
- future effective rate;
- overlapping rates rejected;
- missing rate behavior;
- published forecast snapshot remains unchanged after rate updates.

---

# 100. Testing — Forecasts

Test:

- repeated designation rows allowed;
- named + unnamed same designation;
- named headcount forced to 1;
- unnamed headcount >1;
- monthly deployment percentages;
- FTE calculations;
- cost calculations;
- 208-hour rule;
- version cloning;
- publishing;
- immutability;
- rate snapshot;
- no stored monetary total.

---

# 101. Testing — Assignments

Test:

- one project 100%;
- 60/40 shared assignment;
- 50/25/25 shared assignment;
- allocation >100 rejected;
- overlapping dates;
- future assignments;
- assignment end;
- approval workflow;
- concurrency.

---

# 102. Testing — Transfers

Test:

- full transfer;
- partial transfer;
- employee shared across multiple projects;
- destination approval;
- source approval;
- future transfer;
- cancellation;
- rejection;
- atomic transaction behavior.

---

# 103. Testing — Leave

Test:

- leave does not change assignment;
- employee remains associated with project;
- employee displayed as on leave;
- automatic return after leave;
- overlap validation;
- approval workflow.

---

# 104. Testing — Access Scope

Test:

- Admin sees all projects.
- Normal user sees only project memberships.
- User cannot access another project by manually changing URL/API ID.
- Project membership does not grant permission the RBAC system does not already provide.
- RBAC permission without project membership does not expose unrelated project data.

---

# 105. Implementation Sequence

> **Status:** authoritative progress and handoff notes are tracked in the
> **Implementation Progress & Handoff** block at the top of this file.
> Update that block as phases complete — not this section.

Do not build everything simultaneously.

## Phase 1 — Inspect and Final Schema

Inspect repository and existing authentication/RBAC.

Produce:

- final ERD;
- proposed tables;
- relationships;
- constraints;
- indexes;
- enum strategy;
- project-scope strategy;
- approval-flow strategy.

STOP.

Do not create migrations until reviewed.

---

## Phase 2 — Master Data

Implement:

- projects;
- project membership;
- project approvers;
- departments;
- designations;
- employee categories;
- trades;
- resource providers;
- employees.

---

## Phase 3 — Rate Engine

Implement:

- designation rate history;
- employee rate history;
- rate overlap prevention;
- effective-date resolution;
- service/tests.

---

## Phase 4 — Forecast Engine

Implement:

- forecast versions;
- forecast lines;
- monthly deployment;
- repeated designations;
- named/unnamed lines;
- rate snapshots;
- versioning;
- publishing.

Then build the professional spreadsheet-style forecast editor.

---

## Phase 5 — Actual Assignment Engine

Implement:

- assignment requests;
- approvals;
- assignments;
- availability;
- allocation validation;
- shared resources.

---

## Phase 6 — Transfers

Implement:

- transfer forms;
- source allocations;
- before/after preview;
- approvals;
- atomic assignment modifications.

---

## Phase 7 — Leave

Implement leave workflow without changing project assignments.

---

## Phase 8 — Consolidated Planning

Implement:

- employee allocation matrix;
- designation matrix;
- demand vs capacity;
- FTE;
- hiring gaps;
- upcoming releases;
- tender scenarios.

---

## Phase 9 — Dashboard

Implement management KPIs, charts and exception widgets.

---

## Phase 10 — Reports and PDF

Implement:

- reporting endpoints;
- printable HTML templates;
- PDF generation;
- Excel exports;
- drill-down navigation.

---

# 106. Critical Rules — Never Violate

1. Forecast demand and actual assignment are different concepts.

2. Forecast designation rows may repeat.

3. Named and unnamed forecast rows can coexist.

4. Named forecast rows have headcount = 1.

5. Forecast UI shows months as columns.

6. Forecast database stores months as normalized rows.

7. Forecast monthly records store percentage, not monetary cost.

8. Forecast costs are calculated dynamically.

9. Published forecasts freeze the rate used so historical pricing remains reproducible.

10. Employee rate overrides designation rate.

11. There are no category rates.

12. Employee source is either in-house or hired.

13. Hired employees reference a resource provider.

14. Do not create separate Vendor and Third Party manpower tables.

15. An employee may be shared across multiple projects.

16. Total simultaneous allocation normally cannot exceed 100%.

17. One full month at 100% represents 208 hours.

18. Shared-resource cost is distributed pro rata across projects.

19. Never charge 208 hours independently to each project for the same shared employee.

20. Transfer changes employee assignments.

21. Leave does not change project assignment.

22. Do not store current project directly on Employee.

23. Assignment forms may DISPLAY current project(s), but derive them from assignment records.

24. Assignment/transfer actions require appropriate project approvals.

25. Normal users only see authorized projects.

26. Admin/Super User can see all projects.

27. Project access must be enforced server-side.

28. Published forecasts are immutable.

29. Approved transfers/leave/assignments are historical business records and must not be deleted.

30. Use lifecycle state instead of blindly soft-deleting everything.

31. Monetary values use PostgreSQL NUMERIC.

32. Business calculations belong in backend domain services.

33. Dashboard data should come from aggregated endpoints.

34. Reports should be professional printable documents, not browser screenshots.

35. Industry best practices and polished UX/UI take priority over merely making features technically functional.

---

# 107. Desired End State

A senior manager should be able to open ResourceLense and immediately understand:

### Current Workforce

Where every employee is.

### Utilization

How much each employee is allocated.

### Availability

Who is free now.

### Future Availability

Who will become available and when.

### Shared Resources

Who is split between projects.

### Leave

Who is temporarily unavailable without losing their project assignment.

### Project Requirements

How many people of every designation each project requires.

### Tender Exposure

What staffing demand may arise from upcoming awards.

### Capacity

Whether current staff can satisfy demand.

### Recruitment

Exactly when additional manpower is likely to be required.

### In-House vs Hired

How dependent the company is on external manpower.

### Cost

What manpower costs:

- by employee;
- designation;
- project;
- month;
- tender;
- jobs in hand;
- portfolio.

### History

What was forecast.

What was later revised.

What was actually assigned.

Who transferred.

Who approved it.

Which rates were applicable.

### Management Action

Where the company must:

- hire;
- reallocate;
- transfer;
- release;
- investigate;
- approve;
- reduce excess capacity.

---

# 108. First Task for the Coding Agent

> **Note (2026-10-08):** this first task was executed; items 1–6 and 8–20 were
> effectively addressed for Phases 2–3, but the ERD write-up (item 7) and the
> formal design presentation were not produced as a document — migrations were
> created directly. See the **Implementation Progress & Handoff** block at the
> top of this file. The current first task is Phase 4 (forecast engine).

Do NOT start generating all migrations immediately.

First:

1. Inspect the existing ResourceLense repository.
2. Inspect SQLAlchemy models.
3. Inspect Alembic history.
4. Inspect the existing User/RBAC implementation.
5. Identify reusable existing tables.
6. Compare the current implementation against this specification.
7. Produce the final proposed PostgreSQL ERD.
8. List every proposed business table.
9. List every FK relationship.
10. List important unique/check/exclusion constraints.
11. Explain project-access enforcement.
12. Explain assignment/transfer approval workflow.
13. Explain rate history and resolution.
14. Explain forecast versioning.
15. Explain soft-delete/lifecycle decisions.
16. Explain expected indexes.
17. Identify anything in the current repository that conflicts with this architecture.
18. Recommend any changes required to follow best industry practices.
19. Present an implementation sequence.
20. STOP.

Do not create migrations until this design has been reviewed.

The objective is not merely to implement tables.

The objective is to build ResourceLense as a robust, polished, auditable, high-performance manpower forecasting and resource-management platform suitable for long-term use by a construction company.