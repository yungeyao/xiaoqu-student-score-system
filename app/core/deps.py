"""FastAPI 依赖项: 当前登录用户。"""
from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import SESSION_COOKIE
from ..core.database import SessionLocal
from ..core.security import read_session
from ..models import Admin, Student


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(request: Request, db: Session = Depends(get_db)):
    """返回 (user, category); Not signed in返回 (None, None)。"""
    token = request.cookies.get(SESSION_COOKIE)
    sess = read_session(token)
    if not sess:
        return None, None
    uid, cat = sess
    if cat == "admin":
        return db.get(Admin, uid), "admin"
    return db.get(Student, uid), "student"


def require_login(request: Request, db: Session = Depends(get_db)):
    """Not signed in时重定向到登录页。"""
    user, cat = current_user(request, db)
    if not user:
        return None, None, RedirectResponse("/login", status_code=302)
    return user, cat, None


def require_admin(request: Request, db: Session = Depends(get_db)):
    """管理端: 必须Yes admin Role。"""
    user, cat = current_user(request, db)
    if not user or cat != "admin":
        return None, None, RedirectResponse("/login", status_code=302)
    return user, cat, None


def require_student(request: Request, db: Session = Depends(get_db)):
    """Student端。"""
    user, cat = current_user(request, db)
    if not user or cat != "student":
        return None, None, RedirectResponse("/login", status_code=302)
    return user, cat, None
