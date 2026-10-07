# Business permission catalogue — proposed finalization

This is the permission set I would use to guard the ResourceLense business APIs.
It is written up now so the catalogue can be reviewed before Phase 2 migrations
and endpoints are created.

## Guiding rules

- Separate courses of action with separate permissions, not one giant
  `projects.edit` / `resources.edit` bucket.
- Keep “view” separate from “cost/rate visibility” where the spec calls for
  it.
- Reuse `require_any_permission` only for genuinely shared reference data.
- Do not create permissions for things that do not yet have endpoints.

## Proposed catalogue

## Projects

- `projects.view` — see project lists and project detail within scope
- `projects.create` — create projects
- `projects.edit` — edit project master data
- `projects.archive` — archive / unarchive projects

## Project scope

- `project_memberships.view` — see who has access to which projects
- `project_memberships.manage` — grant / revoke project access

## Project approval routing

- `project_approvers.view` — see project approver configuration
- `project_approvers.manage` — configure project approvers

## Departments / designations / categories / trades / providers

- `master_data.view` — view reference data
- `master_data.manage` — create / edit / deactivate reference data

## Employees

- `employees.view` — see employee records within scope
- `employees.create` — create employees
- `employees.edit` — edit employee master data
- `employees.terminate` — terminate / reactivate employees
- `employees.cost.view` — see employee rates and cost-bearing data

## Rates

- `rates.view` — see effective rate history
- `rates.manage` — create / end / edit rate records

## Forecast

- `forecasts.view` — view forecasts
- `forecasts.create` — create forecasts
- `forecasts.edit` — edit draft forecasts
- `forecasts.publish` — publish and supersede forecasts
- `forecasts.cost.view` — see forecast cost/rate details

## Assignments

- `assignments.view` — view assignments
- `assignments.create` — submit assignment requests
- `assignments.approve` — approve / reject assignment requests

## Transfers

- `transfers.view` — view transfers
- `transfers.create` — submit transfers
- `transfers.approve` — approve / reject transfers

## Leave

- `leave.view` — view leave
- `leave.create` — submit leave
- `leave.approve` — approve / reject leave

## Resource planning / dashboards / reports

- `planning.view` — view resource planning views
- `planning.edit` — edit planning where applicable
- `reports.view` — view reports
- `reports.export` — export reports

## Why not the current placeholder names

The existing `seed_rbac.py` currently carries generic names such as:
`projects.view`, `projects.create`, `projects.edit`, `projects.delete`,
`resources.view`, `resources.create`, `resources.edit`, `resources.delete`,
`planning.view`, `planning.edit`, `reports.view`.

That set is too coarse for a professional resource-planning application and
does not match the spec’s separation of concerns. I would retire it as part
of Phase 0 and replace it with the catalogue above, then re-run the RBAC seed
after the business tables exist.

## Scope of this document

This is design-only for review. No permission rows are created by this doc,
and no endpoints are guarded by these names until the catalogue is approved
and the seed script is updated.
