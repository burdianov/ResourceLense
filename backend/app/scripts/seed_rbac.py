from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.permission import Permission
from app.models.role import ADMIN_ROLE_NAME, Role


PERMISSIONS = {
    "users.view": "View users",
    "users.create": "Create users",
    "users.edit": "Edit users",
    "roles.view": "View roles and the permission catalogue",
    "roles.create": "Create roles",
    "roles.edit": "Edit roles and their permissions",
    "roles.delete": "Delete roles",
    "projects.view": "View projects",
    "projects.create": "Create projects",
    "projects.edit": "Edit projects",
    "projects.archive": "Archive and unarchive projects",
    "project_memberships.view": "View project access assignments",
    "project_memberships.manage": "Grant and revoke project access",
    "project_approvers.view": "View project approver configuration",
    "project_approvers.manage": "Configure project approvers",
    "master_data.view": "View departments, designations, categories, trades and providers",
    "master_data.manage": "Manage departments, designations, categories, trades and providers",
    "employees.view": "View employee records",
    "employees.create": "Create employee records",
    "employees.edit": "Edit employee records",
    "employees.terminate": "Terminate and reactivate employees",
    "rates.view": "View hourly rate history",
    "rates.manage": "Create and end hourly rate records",
    "forecasts.view": "View forecasts",
    "forecasts.create": "Create and clone forecasts",
    "forecasts.edit": "Edit draft forecasts",
    "forecasts.publish": "Publish, supersede and archive forecasts",
    "forecasts.cost.view": "See forecast costs and hourly rates",
    "resources.view": "View resources",
    "resources.create": "Create resources",
    "resources.edit": "Edit resources",
    "resources.delete": "Delete resources",
    "planning.view": "View resource planning",
    "planning.edit": "Edit resource planning",
    "reports.view": "View reports",
    "reports.export": "Export reports as PDF, Excel or CSV",
}


def main() -> None:
    with SessionLocal() as db:
        permissions: list[Permission] = []

        for name, description in PERMISSIONS.items():
            permission = db.scalar(select(Permission).where(Permission.name == name))

            if permission is None:
                permission = Permission(
                    name=name,
                    description=description,
                )
                db.add(permission)
                db.flush()

                print(f"Created permission: {name}")
            else:
                print(f"Permission already exists: {name}")

            permissions.append(permission)

        admin_role = db.scalar(select(Role).where(Role.name == ADMIN_ROLE_NAME))

        if admin_role is None:
            admin_role = Role(
                name="admin",
                description="Full system administrator",
            )
            db.add(admin_role)
            db.flush()

            print("Created role: admin")

        admin_role.permissions = permissions

        db.commit()

        print()
        print("RBAC seed complete.")
        print(f"Admin role has {len(permissions)} permissions.")


if __name__ == "__main__":
    main()
