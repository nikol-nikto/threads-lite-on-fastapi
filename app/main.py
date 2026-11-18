"""Точка входа приложения. Запуск: uvicorn app.main:app --reload"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers import auth, comments, posts, tags, users

app = FastAPI(
    title="Threads Lite",
    description="Учебная мини-соцсеть для коротких текстовых постов.",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(tags.router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")
