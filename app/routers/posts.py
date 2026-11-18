"""Посты: лента, создание/изменение/удаление, лайки, избранное, комментарии к посту."""

from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession, OptionalUser
from app.models import Comment, Favorite, Like, Post, Tag, User, utcnow
from app.schemas import (
    CommentCreate,
    CommentRead,
    Page,
    PostCreate,
    PostRead,
    PostUpdate,
    normalize_tag,
)
from app.services import ensure_can_modify, get_or_create_tags, get_post_or_404, posts_select, to_post_reads

router = APIRouter(prefix="/posts", tags=["Посты"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("", response_model=Page[PostRead])
def list_posts(
    db: DbSession,
    user: OptionalUser,
    limit: Limit = 20,
    offset: Offset = 0,
    tag: Annotated[str | None, Query(description="Фильтр по тегу, например python")] = None,
    author: Annotated[str | None, Query(description="Фильтр по имени автора")] = None,
    search: Annotated[str | None, Query(description="Поиск по тексту поста")] = None,
):
    """Лента постов, новые сверху. Доступна без авторизации."""
    stmt = select(Post)
    if tag:
        stmt = stmt.where(Post.tags.any(Tag.name == normalize_tag(tag)))
    if author:
        stmt = stmt.where(Post.author.has(User.username == author))
    if search:
        stmt = stmt.where(Post.text.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    posts = db.scalars(
        stmt.options(selectinload(Post.author), selectinload(Post.tags))
        .order_by(Post.created_at.desc(), Post.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return Page(items=to_post_reads(db, list(posts), user), total=total, limit=limit, offset=offset)


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def create_post(data: PostCreate, db: DbSession, user: CurrentUser):
    post = Post(text=data.text, author=user, tags=get_or_create_tags(db, data.tags))
    db.add(post)
    db.commit()
    return to_post_reads(db, [post], user)[0]


@router.get("/{post_id}", response_model=PostRead)
def read_post(post_id: int, db: DbSession, user: OptionalUser):
    return to_post_reads(db, [get_post_or_404(db, post_id)], user)[0]


@router.patch("/{post_id}", response_model=PostRead)
def update_post(post_id: int, data: PostUpdate, db: DbSession, user: CurrentUser):
    """Изменить свой пост. Редактировать чужие посты не может даже админ."""
    post = get_post_or_404(db, post_id)
    ensure_can_modify(user, post.author_id, allow_admin=False)
    if data.text is not None:
        post.text = data.text
    if data.tags is not None:
        post.tags = get_or_create_tags(db, data.tags)
    post.updated_at = utcnow()
    db.commit()
    return to_post_reads(db, [post], user)[0]


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: DbSession, user: CurrentUser):
    """Удалить пост. Автор может удалить свой пост, админ — любой."""
    post = get_post_or_404(db, post_id)
    ensure_can_modify(user, post.author_id, allow_admin=True)
    db.delete(post)
    db.commit()


# ---------- Лайки и избранное ----------
# Операции идемпотентны: повторный лайк или снятие несуществующего лайка не ошибка.


def _set_mark(db: DbSession, model, user_id: int, post_id: int, enabled: bool) -> None:
    get_post_or_404(db, post_id)
    mark = db.get(model, (user_id, post_id))
    if enabled and mark is None:
        db.add(model(user_id=user_id, post_id=post_id))
    elif not enabled and mark is not None:
        db.delete(mark)
    db.commit()


@router.post("/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def like_post(post_id: int, db: DbSession, user: CurrentUser):
    _set_mark(db, Like, user.id, post_id, enabled=True)


@router.delete("/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def unlike_post(post_id: int, db: DbSession, user: CurrentUser):
    _set_mark(db, Like, user.id, post_id, enabled=False)


@router.post("/{post_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def add_to_favorites(post_id: int, db: DbSession, user: CurrentUser):
    _set_mark(db, Favorite, user.id, post_id, enabled=True)


@router.delete("/{post_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_favorites(post_id: int, db: DbSession, user: CurrentUser):
    _set_mark(db, Favorite, user.id, post_id, enabled=False)


# ---------- Комментарии к посту ----------


@router.get("/{post_id}/comments", response_model=Page[CommentRead], tags=["Комментарии"])
def list_comments(post_id: int, db: DbSession, limit: Limit = 50, offset: Offset = 0):
    """Комментарии к посту в хронологическом порядке."""
    get_post_or_404(db, post_id)
    total = db.scalar(select(func.count()).select_from(Comment).where(Comment.post_id == post_id))
    comments = db.scalars(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at, Comment.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return Page(items=comments, total=total, limit=limit, offset=offset)


@router.post(
    "/{post_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Комментарии"],
)
def create_comment(post_id: int, data: CommentCreate, db: DbSession, user: CurrentUser):
    get_post_or_404(db, post_id)
    comment = Comment(text=data.text, post_id=post_id, author=user)
    db.add(comment)
    db.commit()
    return comment
