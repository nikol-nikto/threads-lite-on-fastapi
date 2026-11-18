"""Регистрация и вход."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.dependencies import DbSession
from app.models import User
from app.schemas import Token, UserCreate, UserRead
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: DbSession):
    """Регистрация нового пользователя (всегда с ролью user)."""
    if db.scalar(select(User).where(User.username == data.username)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Имя пользователя уже занято")
    user = User(username=data.username, hashed_password=hash_password(data.password))
    db.add(user)
    db.commit()
    return user


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    """Вход по логину и паролю. Принимает form-data (так требует стандарт OAuth2 и Swagger UI).

    В ответ возвращает JWT-токен, который нужно передавать в заголовке
    `Authorization: Bearer <token>`.
    """
    user = db.scalar(select(User).where(User.username == form.username))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id))
