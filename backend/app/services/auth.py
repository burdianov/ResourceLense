from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    # Emails are stored lower-cased (see the user admin endpoints), so the
    # lookup has to normalise the same way.
    normalized_email = email.strip().lower()

    statement = select(User).where(
        User.email == normalized_email,
    )

    user = db.scalar(statement)

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(
        password,
        user.hashed_password,
    ):
        return None

    return user
