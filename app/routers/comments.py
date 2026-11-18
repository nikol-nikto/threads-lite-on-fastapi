"""Изменение и удаление отдельных комментариев."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import CurrentUser, DbSession
from app.models import Comment, utcnow
from app.schemas import CommentRead, CommentUpdate
from app.services import ensure_can_modify

router = APIRouter(prefix="/comments", tags=["Комментарии"])


def _get_comment_or_404(db: Session, comment_id: int) -> Comment:
    comment = db.scalar(
        select(Comment).options(selectinload(Comment.author)).where(Comment.id == comment_id)
    )
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Комментарий не найден")
    return comment


@router.patch("/{comment_id}", response_model=CommentRead)
def update_comment(comment_id: int, data: CommentUpdate, db: DbSession, user: CurrentUser):
    """Изменить свой комментарий."""
    comment = _get_comment_or_404(db, comment_id)
    ensure_can_modify(user, comment.author_id, allow_admin=False)
    comment.text = data.text
    comment.updated_at = utcnow()
    db.commit()
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, db: DbSession, user: CurrentUser):
    """Удалить комментарий. Автор — свой, админ — любой."""
    comment = _get_comment_or_404(db, comment_id)
    ensure_can_modify(user, comment.author_id, allow_admin=True)
    db.delete(comment)
    db.commit()
