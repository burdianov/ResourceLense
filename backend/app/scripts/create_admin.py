import getpass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.role import Role
from app.models.user import User


email_adapter = TypeAdapter(EmailStr)


def main() -> None:
    print("Create ResourceLense administrator")
    print("----------------------------------")

    raw_email = input("Email: ").strip().lower()

    try:
        email = str(email_adapter.validate_python(raw_email))
    except ValueError:
        print("Invalid email address.")
        return

    full_name = input("Full name: ").strip()

    if not full_name:
        print("Full name is required.")
        return

    password = getpass.getpass("Password: ")
    password_confirmation = getpass.getpass("Confirm password: ")

    if not password:
        print("Password is required.")
        return

    if password != password_confirmation:
        print("Passwords do not match.")
        return

    with SessionLocal() as db:
        existing_user = db.scalar(select(User).where(User.email == email))

        if existing_user is not None:
            print("A user with this email already exists.")
            return

        admin_role = db.scalar(select(Role).where(Role.name == "admin"))

        if admin_role is None:
            admin_role = Role(
                name="admin",
                description="Full system administrator",
            )
            db.add(admin_role)
            db.flush()

        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            is_active=True,
        )

        user.roles.append(admin_role)

        db.add(user)
        db.commit()

        print()
        print(f"Administrator created: {user.email}")


if __name__ == "__main__":
    main()
