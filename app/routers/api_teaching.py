"""教学管理：课程考勤录入与选课名单的接口与页面。

考勤按「课程 + 日期」整班录入：一次载入该课程的学生名单并带出已有记录，
教师在页面上逐人点出勤状态后整批保存，重复保存按 (课程, 学生, 日期) 覆盖。
"""
from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_db, require_admin
from ..core.response import fail, ok, table
from ..models import (
    ATTENDANCE_STATUS,
    Attendance,
    Banji,
    Course,
    Enrollment,
    Student,
    Subject,
    Xueqi,
)
from ..models.base import now_ts, str_to_ts, ts_to_str
from ..services.crud import int_or

router = APIRouter(tags=["teaching"])


async def _form(request: Request) -> dict:
    return dict(await request.form())


def _scope_banji_ids(request, db) -> list[int] | None:
    """当前用户的班级范围；None 表示不限。"""
    from ..services.permission import data_scope

    user, _cat, _r = require_admin(request, db)
    scope = data_scope(db, user)
    return None if scope["all"] else (scope["banji_ids"] or [0])


def _course_options(db, banji_ids: list[int] | None):
    stmt = select(Course).where(Course.delete_time.is_(None), Course.status == 1)
    if banji_ids is not None:
        stmt = stmt.where(Course.banji_id.in_(banji_ids))
    courses = db.scalars(stmt.order_by(Course.banji_id, Course.subject_id)).all()

    bj = {b.id: b.full_title for b in db.scalars(select(Banji)).all()}
    sub = {s.id: s.title for s in db.scalars(select(Subject)).all()}
    out = []
    for c in courses:
        out.append(
            {
                "id": c.id,
                "title": c.title or f"{bj.get(c.banji_id, '')}{sub.get(c.subject_id, '')}",
                "banji": bj.get(c.banji_id, ""),
                "subject": sub.get(c.subject_id, ""),
                "teacher_id": c.teacher_id,
            }
        )
    return out


def _allowed(course: Course | None, banji_ids: list[int] | None) -> bool:
    if course is None:
        return False
    return banji_ids is None or course.banji_id in banji_ids


def _students_of_course(db, course: Course) -> list[Student]:
    """课程名单：优先取选课记录，没选课的课程退回班级学生。"""
    ids = db.scalars(
        select(Enrollment.student_id).where(
            Enrollment.course_id == course.id,
            Enrollment.delete_time.is_(None),
            Enrollment.status == 1,
        )
    ).all()
    stmt = select(Student).where(Student.delete_time.is_(None), Student.status == 1)
    if ids:
        stmt = stmt.where(Student.id.in_(ids))
    else:
        stmt = stmt.where(Student.banji_id == course.banji_id)
    return db.scalars(stmt.order_by(Student.id)).all()


# ================================================================== 考勤录入


@router.get("/attendance")
def attendance_page(request: Request, course_id: int = 0, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..main import templates

    page = {
        "webtitle": "考勤录入",
        "courses": _course_options(db, _scope_banji_ids(request, db)),
        "today": date.today().isoformat(),
        "preselect": course_id,
        "statuses": [{"value": k, "label": v} for k, v in ATTENDANCE_STATUS.items()],
    }
    return templates.TemplateResponse(
        request, "attendance.html", {"request": request, "page": page}
    )


@router.post("/api/attendance/students")
async def attendance_students(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    course = db.get(Course, int_or(form, "course_id", 0))
    if not _allowed(course, _scope_banji_ids(request, db)):
        return fail("课程不存在或无权访问")
    riqi = str_to_ts(form.get("riqi")) or str_to_ts(date.today().isoformat())

    students = _students_of_course(db, course)
    existing = {
        a.student_id: a
        for a in db.scalars(
            select(Attendance).where(
                Attendance.course_id == course.id, Attendance.riqi == riqi
            )
        ).all()
    }
    rows = []
    for s in students:
        a = existing.get(s.id)
        rows.append(
            {
                "student_id": s.id,
                "xingming": s.xingming,
                "zhuangtai": a.zhuangtai if a else 1,
                "beizhu": a.beizhu or "" if a else "",
                "saved": a is not None,
            }
        )
    return ok("", {"students": rows, "riqi": riqi, "course_id": course.id})


@router.post("/api/attendance/save")
async def attendance_save(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    course = db.get(Course, int_or(form, "course_id", 0))
    if not _allowed(course, _scope_banji_ids(request, db)):
        return fail("课程不存在或无权访问")
    riqi = str_to_ts(form.get("riqi"))
    if not riqi:
        return fail("请选择日期")
    try:
        rows = json.loads(form.get("rows") or "[]")
    except json.JSONDecodeError:
        return fail("提交的数据格式不正确")
    if not rows:
        return fail("没有要保存的记录")

    existing = {
        a.student_id: a
        for a in db.scalars(
            select(Attendance).where(Attendance.course_id == course.id, Attendance.riqi == riqi)
        ).all()
    }
    created = updated = 0
    for row in rows:
        sid = int(row.get("student_id") or 0)
        if not sid:
            continue
        zt = int(row.get("zhuangtai", 1))
        if zt not in ATTENDANCE_STATUS:
            continue
        a = existing.get(sid)
        if a is None:
            db.add(Attendance(course_id=course.id, student_id=sid, riqi=riqi,
                              zhuangtai=zt, beizhu=row.get("beizhu") or None))
            created += 1
        else:
            a.zhuangtai = zt
            a.beizhu = row.get("beizhu") or None
            a.update_time = now_ts()
            updated += 1
    db.commit()
    return ok(f"已保存 {len(rows)} 人：新增 {created}，更新 {updated}",
              {"created": created, "updated": updated})


@router.post("/api/attendance/stats")
async def attendance_stats(request: Request, db: Session = Depends(get_db)):
    """某门课的考勤汇总：按日期出勤构成 + 每个学生的到课率。"""
    form = await _form(request)
    course = db.get(Course, int_or(form, "course_id", 0))
    if not _allowed(course, _scope_banji_ids(request, db)):
        return fail("课程不存在或无权访问")

    records = db.scalars(
        select(Attendance).where(
            Attendance.course_id == course.id, Attendance.delete_time.is_(None)
        )
    ).all()
    by_day: dict[int, dict[int, int]] = {}
    by_student: dict[int, dict[int, int]] = {}
    for a in records:
        by_day.setdefault(a.riqi, {}).setdefault(a.zhuangtai, 0)
        by_day[a.riqi][a.zhuangtai] += 1
        by_student.setdefault(a.student_id, {}).setdefault(a.zhuangtai, 0)
        by_student[a.student_id][a.zhuangtai] += 1

    names = {s.id: s.xingming for s in _students_of_course(db, course)}
    order = sorted(by_day)
    days = [
        {
            "riqi": ts_to_str(d),
            "total": sum(by_day[d].values()),
            "present": sum(v for k, v in by_day[d].items() if k in (1, 2, 3)),
            "absent": by_day[d].get(0, 0),
        }
        for d in order
    ]
    per_student = []
    for sid, cnt in by_student.items():
        total = sum(cnt.values())
        present = sum(v for k, v in cnt.items() if k in (1, 2, 3))
        per_student.append(
            {
                "student_id": sid,
                "xingming": names.get(sid, ""),
                "total": total,
                "absent": cnt.get(0, 0),
                "late": cnt.get(2, 0),
                "leave": cnt.get(3, 0),
                "rate": round(present / total * 100, 1) if total else None,
            }
        )
    per_student.sort(key=lambda r: (r["rate"] is None, r["rate"] or 0))
    return ok("", {"days": days, "students": per_student})


# ================================================================== 选课


@router.get("/enrollment/batch")
def enrollment_batch_page(request: Request, course_id: int = 0, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..main import templates

    page = {
        "webtitle": "批量选课",
        "courses": _course_options(db, _scope_banji_ids(request, db)),
        "preselect": course_id,
    }
    return templates.TemplateResponse(
        request, "enrollment_batch.html", {"request": request, "page": page}
    )


@router.post("/api/enrollment/students")
async def enrollment_students(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    course = db.get(Course, int_or(form, "course_id", 0))
    if not _allowed(course, _scope_banji_ids(request, db)):
        return fail("课程不存在或无权访问")

    enrolled = set(
        db.scalars(
            select(Enrollment.student_id).where(
                Enrollment.course_id == course.id, Enrollment.delete_time.is_(None)
            )
        ).all()
    )
    students = db.scalars(
        select(Student)
        .where(Student.banji_id == course.banji_id,
               Student.delete_time.is_(None), Student.status == 1)
        .order_by(Student.id)
    ).all()
    rows = [
        {"student_id": s.id, "xingming": s.xingming, "enrolled": s.id in enrolled}
        for s in students
    ]
    return ok("", {"students": rows, "course_id": course.id, "enrolled": len(enrolled)})


@router.post("/api/enrollment/batch")
async def enrollment_batch_save(request: Request, db: Session = Depends(get_db)):
    """按提交的勾选结果对齐选课记录：新增勾选的，移除取消勾选的。"""
    form = await _form(request)
    course = db.get(Course, int_or(form, "course_id", 0))
    if not _allowed(course, _scope_banji_ids(request, db)):
        return fail("课程不存在或无权访问")
    try:
        wanted = {int(x) for x in json.loads(form.get("student_ids") or "[]")}
    except (json.JSONDecodeError, TypeError, ValueError):
        return fail("提交的数据格式不正确")

    current = {
        e.student_id: e
        for e in db.scalars(
            select(Enrollment).where(Enrollment.course_id == course.id)
        ).all()
    }
    added = removed = 0
    for sid in wanted:
        e = current.get(sid)
        if e is None:
            db.add(Enrollment(course_id=course.id, student_id=sid,
                              xuanke_time=now_ts(), status=1))
            added += 1
        elif e.delete_time is not None or e.status != 1:
            e.delete_time = None
            e.status = 1
            e.update_time = now_ts()
            added += 1
    for sid, e in current.items():
        if sid not in wanted and e.delete_time is None:
            e.delete_time = now_ts()
            e.update_time = now_ts()
            removed += 1
    db.commit()
    return ok(f"选课已更新：新增 {added}，移除 {removed}",
              {"added": added, "removed": removed, "total": len(wanted)})
