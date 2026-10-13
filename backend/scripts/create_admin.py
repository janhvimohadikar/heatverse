"""
Create (or promote) an administrator account.  The password is typed at a hidden prompt and is never stored in any file.

Run from the backend folder with the virtual environment active:
    python scripts/create_admin.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.security import EMAIL_RE, hash_password  # noqa: E402
from app.db.session import SessionLocal, init_app_tables  # noqa: E402
from app.models import AuditLog, User, UserProfile  # noqa: E402


def main() -> int:
    init_app_tables()
    email = input("Admin email: ").strip().lower()
    if not EMAIL_RE.match(email):
        print("That does not look like a valid email address.")
        return 1
    with SessionLocal() as session:
        existing = session.scalar(select(User).where(User.email == email))
        if existing:
            if existing.role == "admin":
                print("That account is already an administrator.")
                return 0
            if input("An account with this email exists. Promote it to admin? [y/N] ").strip().lower() != "y":
                return 0
            existing.role = "admin"
            session.add(AuditLog(actor_user_id=None, action="admin.promote_cli", target=email))
            session.commit()
            print("Account promoted to administrator.")
            return 0
        pw = getpass.getpass("Password (min 8 characters): ")
        if len(pw) < 8:
            print("Password must be at least 8 characters.")
            return 1
        if pw != getpass.getpass("Repeat password: "):
            print("Passwords do not match.")
            return 1
        user = User(email=email, password_hash=hash_password(pw), role="admin")
        user.profile = UserProfile(full_name="Administrator")
        session.add(user)
        session.add(AuditLog(actor_user_id=None, action="admin.create_cli", target=email))
        session.commit()
        print(f"Administrator account created for {email}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
