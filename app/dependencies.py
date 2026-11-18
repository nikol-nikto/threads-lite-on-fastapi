"""Общие зависимости (Depends) для роутеров."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

# tokenUrl — адрес, куда Swagger UI (кнопка Authorize) отправляет логин/пароль.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# Тот же механизм, но без ошибки, если токена нет — для публичных эндпоинтов.
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительный или просроченный токен",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _user_from_token(token: str, db: Session) -> User:
    user_id = decode_access_token(token)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise _credentials_error()
    return user


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    """Требует авторизацию: без валидного токена — 401."""
    return _user_from_token(token, db)


def get_current_user_optional(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)], db: DbSession
) -> User | None:
    """Авторизация по желанию: аноним получает None."""
    if token is None:
        return None
    return _user_from_token(token, db)


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
