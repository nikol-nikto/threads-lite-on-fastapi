"""Профили пользователей и избранное."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession
from app.models import Favorite, Post, User
from app.schemas import Page, PostRead, UserRead
from app.services import posts_select, to_post_reads

router = APIRouter(prefix="/users", tags=["Пользователи"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/me", response_model=UserRead)
def read_me(user: CurrentUser):
    return user


@router.get("/me/favorites", response_model=Page[PostRead])
def my_favorites(user: CurrentUser, db: DbSession, limit: Limit = 20, offset: Offset = 0):
    """Посты, которые текущий пользователь добавил в избранное (сначала недавно добавленные)."""
    total = db.scalar(select(func.count()).select_from(Favorite).where(Favorite.user_id == user.id))
    posts = db.scalars(
        posts_select()
        .join(Favorite, Favorite.post_id == Post.id)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return Page(items=to_post_reads(db, list(posts), user), total=total, limit=limit, offset=offset)


@router.get("/{username}", response_model=UserRead)
def read_user(username: str, db: DbSession):
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    return user
