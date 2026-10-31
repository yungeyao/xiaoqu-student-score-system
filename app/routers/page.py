"""后台页面路由。"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.deps import get_db, require_admin
from ..models import Attendance, Banji, Course, Kaoshi, Student, Teacher, Xueqi
from ..models.base import ts_to_str
from ..services.menu import build_menu

router = APIRouter(tags=["page"])


@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..main import templates

    return templates.TemplateResponse(request, "index.html",
        {"request": request, "user": user, "menu": build_menu(db, user)},
    )


@router.get("/welcome")
def welcome(request: Request, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..main import templates

    stats = {
        "kaoshi": db.scalar(
            select(func.count()).select_from(Kaoshi).where(Kaoshi.delete_time.is_(None))
        )
        or 0,
        "student": db.scalar(
            select(func.count()).select_from(Student).where(Student.delete_time.is_(None))
        )
        or 0,
        "banji": db.scalar(
            select(func.count()).select_from(Banji).where(Banji.delete_time.is_(None))
        )
        or 0,
        "teacher": db.scalar(
            select(func.count()).select_from(Teacher).where(Teacher.delete_time.is_(None))
        )
        or 0,
        "course": db.scalar(
            select(func.count()).select_from(Course).where(Course.delete_time.is_(None))
        )
        or 0,
        "attendance": db.scalar(select(func.count()).select_from(Attendance)) or 0,
    }

    ks = db.scalars(
        select(Kaoshi)
        .where(Kaoshi.delete_time.is_(None))
        .order_by(Kaoshi.bfdate.desc())
        .limit(6)
    ).all()
    xq = {x.id: x.title for x in db.scalars(select(Xueqi)).all()}
    recent = [
        {
            "title": k.title,
            "xueqi": xq.get(k.xueqi_id, ""),
            "bfdate": ts_to_str(k.bfdate),
            "enddate": ts_to_str(k.enddate),
            "luru": k.luru,
        }
        for k in ks
    ]

    return templates.TemplateResponse(request, "welcome.html", {"request": request, "stats": stats, "recent": recent}
    )


@router.get("/password/edit")
def password_edit(request: Request, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..main import templates

    page = {
        "webtitle": "Change password",
        "url": "/api/changepassword",
        "formpost": "POST",
        "fields": [
            {"name": "old_password", "label": "Current password", "type": "password", "required": True},
            {"name": "new_password", "label": "New password", "type": "password", "required": True},
        ],
        "obj": {},
    }
    return templates.TemplateResponse(request, "generic_form.html", {"request": request, "page": page}
    )
