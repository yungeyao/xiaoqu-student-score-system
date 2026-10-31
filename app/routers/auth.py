"""登录 / 退出。"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.config import SESSION_COOKIE, SESSION_EXPIRE
from ..core.deps import get_db
from ..core.security import make_session, password_hash, password_verify
from ..models import Admin, Student
from ..models.base import now_ts

router = APIRouter(tags=["auth"])


@router.get("/login")
def login_page(request: Request):
    from ..main import templates

    return templates.TemplateResponse(request, "login.html", {"request": request})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    category: str = Form("admin"),
    db: Session = Depends(get_db),
):
    if category == "student":
        user = db.scalars(
            select(Student).where(
                Student.shenfenzhenghao == username.strip(), Student.status == 1
            )
        ).first()
        cat = "student"
    else:
        user = db.scalars(
            select(Admin).where(
                or_(Admin.username == username.strip(), Admin.phone == username.strip()),
                Admin.status == 1,
            )
        ).first()
        cat = "admin"

    if user is None or not password_verify(password, user.password):
        from ..main import templates

        return templates.TemplateResponse(request, "login.html", {"request": request, "error": "Incorrect account or password"}
        )

    user.login_count = (user.login_count or 0) + 1
    user.last_time = now_ts()
    user.last_ip = request.client.host if request.client else ""
    db.commit()

    resp = RedirectResponse("/student" if cat == "student" else "/", status_code=302)
    resp.set_cookie(
        SESSION_COOKIE,
        make_session(user.id, cat),
        max_age=SESSION_EXPIRE,
        httponly=True,
        samesite="lax",
    )
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@router.post("/api/changepassword")
def change_password(
    request: Request,
    old_password: str = Form(""),
    new_password: str = Form(""),
    db: Session = Depends(get_db),
):
    from ..core.security import read_session
    from ..models import Admin

    sess = read_session(request.cookies.get(SESSION_COOKIE))
    if not sess:
        return {"val": 0, "msg": "Please sign in first"}
    uid, cat = sess
    model = Admin if cat == "admin" else Student
    user = db.get(model, uid)
    if not user or not password_verify(old_password, user.password):
        return {"val": 0, "msg": "Current password is incorrect"}
    if len(new_password) < 6:
        return {"val": 0, "msg": "New password must be at least 6 characters"}
    user.password = password_hash(new_password)
    db.commit()
    return {"val": 1, "msg": "Password updated"}
