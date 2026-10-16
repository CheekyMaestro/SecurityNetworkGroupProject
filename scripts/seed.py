"""Buat akun demo: dua admin toko dan satu pembeli. Aman dijalankan berulang.

    python scripts/seed.py                  # password acak per akun, dicetak ke terminal
    python scripts/seed.py --password XYZ   # semua akun baru memakai password ini

Akun yang sudah ada tidak diubah (password-nya tetap).
"""

import argparse
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select  # noqa: E402

from app.crypto.keys import new_key_salt  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app import models  # noqa: E402,F401
from app.models import User  # noqa: E402
from app.security.passwords import hash_password  # noqa: E402

ACCOUNTS = [
    ("elektra", "store", "Toko Elektra"),
    ("gadgetin", "store", "Toko Gadgetin"),
    ("dzaky", "buyer", None),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--password", help="Password untuk akun baru (minimal 8 karakter)")
    args = parser.parse_args()
    if args.password is not None and len(args.password) < 8:
        parser.error("password minimal 8 karakter")

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for username, role, store_name in ACCOUNTS:
            existing = db.scalar(select(User).where(func.lower(User.username) == username))
            if existing:
                print(f"  {username:<10} sudah ada, dilewati")
                continue
            password = args.password or secrets.token_urlsafe(9)
            db.add(User(
                username=username, password_hash=hash_password(password), key_salt=new_key_salt(),
                role=role, store_name=store_name,
            ))
            db.commit()
            label = store_name or "pembeli"
            shown = "(dari --password)" if args.password else password
            print(f"+ {username:<10} {label:<14} password: {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
