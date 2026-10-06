from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.permission import Permission
from app.models.role import Role


PERMISSIONS = {
    "users.view": "View users",
    "users.create": "Create users",
    "users.edit": "Edit users",
    "projects.view": "View projects",
    "projects.create": "Create projects",
    "projects.edit": "Edit projects",
    "projects.delete": "Delete projects",
    "resources.view": "View resources",
    "resources.create": "Create resources",
    "resources.edit": "Edit resources",
    "resources.delete": "Delete resources",
    "planning.view": "View resource planning",
    "planning.edit": "Edit resource planning",
    "reports.view": "View reports",
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

        admin_role = db.scalar(select(Role).where(Role.name == "admin"))

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
