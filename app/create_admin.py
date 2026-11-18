"""Создание администратора из консоли.

Примеры:
    python -m app.create_admin admin                 # спросит пароль
    python -m app.create_admin admin --password 123456
    python -m app.create_admin existing_user         # повысит существующего пользователя до админа
"""

import argparse
import getpass
import sys

from pydantic import ValidationError
from sqlalchemy import select

from app.database import SessionLocal
from app.models import User, UserRole
from app.schemas import UserCreate
from app.security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Создать администратора или выдать права существующему пользователю")
    parser.add_argument("username")
    parser.add_argument("--password", help="пароль для нового пользователя (если не указан — будет запрошен)")
    args = parser.parse_args()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == args.username))
        if user is not None:
            user.role = UserRole.ADMIN
            db.commit()
            print(f"Пользователь {user.username!r} теперь администратор.")
            return

        password = args.password or getpass.getpass("Пароль: ")
        try:
            data = UserCreate(username=args.username, password=password)
        except ValidationError as e:
            print(f"Ошибка: {e}", file=sys.stderr)
            sys.exit(1)

        db.add(User(username=data.username, hashed_password=hash_password(data.password), role=UserRole.ADMIN))
        db.commit()
        print(f"Администратор {data.username!r} создан.")


if __name__ == "__main__":
    main()
