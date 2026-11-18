"""Pydantic-схемы — что API принимает на вход и что отдаёт на выход.

Модели БД (models.py) и схемы API специально разделены: например, в ответе
никогда не должен оказаться hashed_password.
"""

import re
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import UserRole

POST_MAX_LENGTH = 1000
COMMENT_MAX_LENGTH = 500
MAX_TAGS_PER_POST = 10
TAG_PATTERN = re.compile(r"^[\w-]{1,32}$")  # буквы (в т.ч. кириллица), цифры, _ и -


# ---------- Пользователи и авторизация ----------


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=6, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    created_at: datetime


class UserShort(BaseModel):
    """Короткая информация об авторе — для вложения в посты и комментарии."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Посты ----------


def _clean_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Текст не может быть пустым")
    return value


def normalize_tag(raw: str) -> str:
    """'#Python ' -> 'python'."""
    return raw.strip().lstrip("#").lower()


def _clean_tags(values: list[str]) -> list[str]:
    result: list[str] = []
    for raw in values:
        tag = normalize_tag(raw)
        if not TAG_PATTERN.match(tag):
            raise ValueError(f"Некорректный тег: {raw!r} (буквы, цифры, _ и -, до 32 символов)")
        if tag not in result:  # убираем дубликаты, сохраняя порядок
            result.append(tag)
    if len(result) > MAX_TAGS_PER_POST:
        raise ValueError(f"Не больше {MAX_TAGS_PER_POST} тегов на пост")
    return result


class PostCreate(BaseModel):
    text: str = Field(min_length=1, max_length=POST_MAX_LENGTH)
    tags: list[str] = Field(default_factory=list, examples=[["python", "fastapi"]])

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        return _clean_text(v)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        return _clean_tags(v)


class PostUpdate(BaseModel):
    """Частичное обновление: передаются только те поля, которые нужно изменить."""

    text: str | None = Field(default=None, min_length=1, max_length=POST_MAX_LENGTH)
    tags: list[str] | None = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str | None) -> str | None:
        return None if v is None else _clean_text(v)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else _clean_tags(v)


class PostRead(BaseModel):
    id: int
    text: str
    author: UserShort
    tags: list[str]
    created_at: datetime
    updated_at: datetime | None
    likes_count: int
    comments_count: int
    # Для анонимного пользователя всегда False
    liked_by_me: bool
    favorited_by_me: bool


# ---------- Комментарии ----------


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=COMMENT_MAX_LENGTH)

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        return _clean_text(v)


class CommentUpdate(CommentCreate):
    pass


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    text: str
    author: UserShort
    created_at: datetime
    updated_at: datetime | None


# ---------- Теги ----------


class TagRead(BaseModel):
    name: str
    posts_count: int


# ---------- Пагинация ----------

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
