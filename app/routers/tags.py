"""Список тегов."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.dependencies import DbSession
from app.models import Tag, post_tags
from app.schemas import TagRead

router = APIRouter(prefix="/tags", tags=["Теги"])


@router.get("", response_model=list[TagRead])
def list_tags(db: DbSession, limit: Annotated[int, Query(ge=1, le=100)] = 50):
    """Популярные теги: сколько постов с каждым тегом (теги без постов не показываются)."""
    posts_count = func.count(post_tags.c.post_id).label("posts_count")
    rows = db.execute(
        select(Tag.name, posts_count)
        .join(post_tags, post_tags.c.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(posts_count.desc(), Tag.name)
        .limit(limit)
    )
    return [TagRead(name=name, posts_count=count) for name, count in rows]
