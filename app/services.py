"""Вспомогательная логика, которую используют несколько роутеров."""

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Comment, Favorite, Like, Post, Tag, User
from app.schemas import PostRead, UserShort


def posts_select() -> Select[tuple[Post]]:
    """SELECT постов, сразу подгружающий авторов и теги (без лишних запросов на каждый пост)."""
    return select(Post).options(selectinload(Post.author), selectinload(Post.tags))


def get_post_or_404(db: Session, post_id: int) -> Post:
    post = db.scalar(posts_select().where(Post.id == post_id))
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пост не найден")
    return post


def ensure_can_modify(user: User, author_id: int, *, allow_admin: bool) -> None:
    """Изменять может только автор; удалять — автор или админ."""
    if user.id == author_id or (allow_admin and user.is_admin):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")


def get_or_create_tags(db: Session, names: list[str]) -> list[Tag]:
    if not names:
        return []
    existing = {t.name: t for t in db.scalars(select(Tag).where(Tag.name.in_(names)))}
    tags = []
    for name in names:
        tag = existing.get(name)
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            existing[name] = tag
        tags.append(tag)
    return tags


def to_post_reads(db: Session, posts: list[Post], current_user: User | None) -> list[PostRead]:
    """Превращает ORM-посты в схемы ответа, досчитывая лайки/комментарии одним запросом на всё."""
    ids = [p.id for p in posts]
    if not ids:
        return []

    def count_by_post(model) -> dict[int, int]:
        rows = db.execute(
            select(model.post_id, func.count()).where(model.post_id.in_(ids)).group_by(model.post_id)
        )
        return dict(rows.tuples().all())

    likes = count_by_post(Like)
    comments = count_by_post(Comment)

    liked: set[int] = set()
    favorited: set[int] = set()
    if current_user is not None:
        liked = set(
            db.scalars(select(Like.post_id).where(Like.user_id == current_user.id, Like.post_id.in_(ids)))
        )
        favorited = set(
            db.scalars(
                select(Favorite.post_id).where(Favorite.user_id == current_user.id, Favorite.post_id.in_(ids))
            )
        )

    return [
        PostRead(
            id=p.id,
            text=p.text,
            author=UserShort.model_validate(p.author),
            tags=[t.name for t in p.tags],
            created_at=p.created_at,
            updated_at=p.updated_at,
            likes_count=likes.get(p.id, 0),
            comments_count=comments.get(p.id, 0),
            liked_by_me=p.id in liked,
            favorited_by_me=p.id in favorited,
        )
        for p in posts
    ]
