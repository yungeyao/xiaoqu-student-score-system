"""Student端: 查看个 studentsExam history。"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_db, require_student
from ..core.response import fail, ok, table
from ..models import Banji, Chengji, Kaohao, Kaoshi, Student, Subject
from ..models.base import ts_to_str
from ..services.crud import int_or

router = APIRouter(tags=["portal"])


async def _form(request: Request) -> dict:
    return dict(await request.form())


@router.get("/student")
def student_home(request: Request, db: Session = Depends(get_db)):
    user, cat, redirect = require_student(request, db)
    if redirect:
        return redirect
    from ..main import templates

    banji = db.get(Banji, user.banji_id)
    subjects = {
        s.id: s.title
        for s in db.scalars(select(Subject).where(Subject.delete_time.is_(None))).all()
    }
    return templates.TemplateResponse(request, "student.html",
        {
            "request": request,
            "student": user,
            "banji_name": banji.full_title if banji else "",
            "subjects": subjects,
            "page": {"webtitle": "My Results"},
        },
    )


@router.post("/api/student/scores")
async def student_scores(request: Request, db: Session = Depends(get_db)):
    """本 studentsExam history: 一行一场Exam, 一列一个Subject。"""
    user, cat, redirect = require_student(request, db)
    if redirect:
        return fail("Not signed in")

    khs = db.scalars(
        select(Kaohao).where(Kaohao.student_id == user.id, Kaohao.delete_time.is_(None))
    ).all()
    if not khs:
        return table(0, [])

    ks = {k.id: k.title for k in db.scalars(select(Kaoshi)).all()}
    subs = {
        s.id: s.title
        for s in db.scalars(select(Subject).where(Subject.delete_time.is_(None))).all()
    }
    kh_ids = [k.id for k in khs]
    cj: dict[tuple[int, int], float] = {}
    for kh_id, sid, defen in db.execute(
        select(Chengji.kaohao_id, Chengji.subject_id, Chengji.defen).where(
            Chengji.kaohao_id.in_(kh_ids)
        )
    ).all():
        if defen is not None:
            cj[(kh_id, sid)] = float(defen)

    by_exam: dict[int, dict] = defaultdict(lambda: {"scores": {}, "total": 0.0})
    for k in khs:
        rec = by_exam[k.kaoshi_id]
        rec["scores"].update(
            {sid: v for (kh, sid), v in cj.items() if kh == k.id}
        )
        rec["total"] += sum(v for (kh, sid), v in cj.items() if kh == k.id)

    data = []
    for kid, rec in by_exam.items():
        row = {
            "id": kid,
            "exam": ks.get(kid, ""),
            "total": round(rec["total"], 1) if rec["scores"] else None,
        }
        for sid, title in subs.items():
            row[f"s{sid}"] = rec["scores"].get(sid)
        data.append(row)
    data.sort(key=lambda x: x["id"], reverse=True)
    return table(len(data), data)


@router.post("/api/student/chart")
async def student_chart(request: Request, db: Session = Depends(get_db)):
    """本 students某一SubjectExam history的折线图数据。"""
    user, cat, redirect = require_student(request, db)
    if redirect:
        return fail("Not signed in")
    form = await _form(request)
    sid = int_or(form, "subject_id")

    rows = db.execute(
        select(Kaoshi.title, Chengji.defen, Chengji.kaohao_id)
        .join(Kaohao, Kaohao.id == Chengji.kaohao_id)
        .join(Kaoshi, Kaoshi.id == Kaohao.kaoshi_id)
        .where(Kaohao.student_id == user.id, Chengji.subject_id == sid)
        .order_by(Kaoshi.bfdate)
    ).all()

    cats: list[str] = []
    vals: list = []
    seen: dict[str, float] = {}
    for title, defen, _kh in rows:
        if defen is None:
            continue
        seen[title] = float(defen)
    cats = list(seen.keys())
    vals = list(seen.values())
    return ok("", {"categories": cats, "series": [{"name": "Score", "data": vals}]})
