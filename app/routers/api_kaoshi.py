"""Exams: Exam CRUD, Subject分数线设置, Exam no.生成。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_db, require_admin
from ..core.response import fail, ok, table
from ..models import (
    Banji,
    Chengji,
    Kaohao,
    Kaoshi,
    KaoshiSet,
    School,
    Student,
    Subject,
    Xueqi,
)
from ..models.base import now_ts, str_to_ts, ts_to_str
from ..registry import BANJI, XUEQI
from ..services import crud, kaohao as kh_service
from ..services.chengji_io import export_template, import_scores
from ..services.crud import int_or, page_limit
from ..services.serialize import resolve_options, row_to_dict

router = APIRouter(tags=["kaoshi"])


async def _form(request: Request) -> dict:
    return dict(await request.form())


# ================================================================== 考试列表


@router.get("/kaoshi")
def kaoshi_page(request: Request, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..main import templates

    page = {
        "webtitle": "Exams",
        "dataurl": "/api/kaoshi/list",
        "create_url": "/kaoshi/create",
        "delete_url": "/api/kaoshi/delete",
        "status_url": "/api/kaoshi/status",
        "cols": [
            {"field": "id", "title": "ID", "width": 60},
            {"field": "title", "title": "ExamName", "width": 180},
            {"field": "xueqi_name", "title": "Semester", "width": 120},
            {"field": "category_name", "title": "Category", "width": 100},
            {"field": "bfdate", "title": "Start date", "width": 110},
            {"field": "enddate", "title": "End date", "width": 110},
            {"field": "luru", "title": "Open for entry", "width": 100, "templet": "#luruTpl"},
            {"field": "status", "title": "Status", "width": 80, "templet": "#statusTpl"},
        ],
        "toolbar": [{"event": "add", "title": "New exam"}, {"event": "delete", "title": "Bulk delete"}],
        "rowbar": [
            {"event": "edit", "title": "Edit"},
            {"event": "set", "title": "Subject settings",
             "js": "xadmin.add_tab('Subject settings', '/kaoshi/set?id=' + obj.data.id);"},
            {"event": "kaohao", "title": "Exam numbers",
             "js": "xadmin.add_tab('Exam numbers', '/kaohao?kaoshi_id=' + obj.data.id);"},
            {"event": "luru", "title": "Enter grades",
             "js": "xadmin.add_tab('Grade entry', '/luru?kaoshi_id=' + obj.data.id);"},
            {"event": "tongji", "title": "Analytics",
             "js": "xadmin.add_tab('Analytics', '/chengji?kaoshi_id=' + obj.data.id);"},
        ],
        "can_delete": True,
        "search_fields": [{"name": "searchval", "label": "Keyword", "type": "text"}],
    }
    return templates.TemplateResponse(request, "generic_list.html", {"request": request, "page": page})


@router.get("/kaoshi/create")
def kaoshi_form(request: Request, id: int = 0, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..main import templates

    obj = db.get(Kaoshi, id) if id else None
    data = {}
    if obj:
        data = {
            "id": obj.id, "title": obj.title, "zuzhi_id": obj.zuzhi_id,
            "xueqi_id": obj.xueqi_id, "category_id": obj.category_id,
            "bfdate": ts_to_str(obj.bfdate), "enddate": ts_to_str(obj.enddate),
            "luru": obj.luru, "status": obj.status, "beizhu": obj.beizhu or "",
        }
    page = {
        "webtitle": ("Edit" if obj else "New") + "Exam",
        "url": "/api/kaoshi/save",
        "formpost": "POST",
        "fields": [
            {"name": "title", "label": "ExamName", "type": "text", "required": True},
            {"name": "zuzhi_id", "label": "Organising school", "type": "select",
             "options": [{"value": s.id, "label": s.title}
                         for s in db.scalars(select(School).where(School.delete_time.is_(None))).all()]},
            {"name": "xueqi_id", "label": "Semester", "type": "select",
             "options": [{"value": x.id, "label": x.title}
                         for x in db.scalars(select(Xueqi).where(Xueqi.delete_time.is_(None))).all()]},
            {"name": "category_id", "label": "Exam type", "type": "select",
             "options": resolve_options(db, "category:109")},
            {"name": "bfdate", "label": "Start date", "type": "date"},
            {"name": "enddate", "label": "End date", "type": "date"},
            {"name": "luru", "label": "Open for entry", "type": "switch"},
            {"name": "status", "label": "Status", "type": "switch"},
            {"name": "beizhu", "label": "Note", "type": "textarea"},
        ],
        "obj": data,
    }
    return templates.TemplateResponse(request, "generic_form.html", {"request": request, "page": page})


@router.post("/api/kaoshi/list")
async def kaoshi_list(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    page_no, limit = page_limit(form)
    stmt = select(Kaoshi).where(Kaoshi.delete_time.is_(None))
    kw = form.get("searchval")
    if kw:
        stmt = stmt.where(Kaoshi.title.like(f"%{kw}%"))
    stmt = stmt.order_by(Kaoshi.bfdate.desc())
    rows, total = crud.paginate(db, stmt, page_no, limit)

    xq = {x.id: x.title for x in db.scalars(select(Xueqi)).all()}
    cats = resolve_options(db, "category:109")
    cat_map = {c["value"]: c["label"] for c in cats}

    data = [
        {
            "id": r.id, "title": r.title, "xueqi_name": xq.get(r.xueqi_id, ""),
            "category_name": cat_map.get(r.category_id, ""),
            "bfdate": ts_to_str(r.bfdate), "enddate": ts_to_str(r.enddate),
            "luru": r.luru, "status": r.status,
        }
        for r in rows
    ]
    return table(total, data)


@router.post("/api/kaoshi/save")
async def kaoshi_save(request: Request, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return fail("Not signed in")
    form = await _form(request)
    oid = int_or(form, "id")
    obj = db.get(Kaoshi, oid) if oid else None
    if obj is None:
        obj = Kaoshi(user_id=user.id)
        db.add(obj)
    obj.title = form.get("title") or ""
    obj.zuzhi_id = int_or(form, "zuzhi_id", 0)
    obj.xueqi_id = int_or(form, "xueqi_id", 0)
    obj.category_id = int_or(form, "category_id", 0)
    obj.bfdate = str_to_ts(form.get("bfdate")) or now_ts()
    obj.enddate = str_to_ts(form.get("enddate")) or now_ts()
    obj.luru = 1 if form.get("luru") in ("1", "on", "true") else 0
    obj.status = 1 if form.get("status") in ("1", "on", "true") else 0
    obj.beizhu = form.get("beizhu")
    obj.update_time = now_ts()
    db.commit()
    return ok("Saved", {"id": obj.id})


@router.delete("/api/kaoshi/delete")
async def kaoshi_delete(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    n = crud.soft_delete(db, Kaoshi, str(form.get("id", "")))
    return ok(f"Deleted {n} rows") if n else fail("No record to delete")


@router.post("/api/kaoshi/status")
async def kaoshi_status(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    return (
        ok("Updated")
        if crud.set_status(db, Kaoshi, int_or(form, "id"), int_or(form, "value", 0),
                           form.get("ziduan") or "status")
        else fail("Record not found")
    )


# ================================================================== 学科分数线设置


@router.get("/kaoshi/set")
def kaoshi_set_page(request: Request, id: int = 0, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..main import templates

    ks = db.get(Kaoshi, id)
    banjis = db.scalars(select(Banji).where(Banji.delete_time.is_(None))).all()
    grades = sorted({b.ruxuenian for b in banjis if b.ruxuenian})
    subjects = db.scalars(
        select(Subject)
        .where(Subject.kaoshi == 1, Subject.delete_time.is_(None))
        .order_by(Subject.paixu)
    ).all()
    return templates.TemplateResponse(request, "kaoshi_set.html",
        {
            "request": request,
            "kaoshi": ks,
            "grades": grades,
            "subjects": [{"id": s.id, "title": s.title} for s in subjects],
            "page": {"webtitle": f"{ks.title if ks else ''} - Subject settings", "kaoshi_id": id},
        },
    )


@router.post("/api/kaoshi/set_list")
async def set_list(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    rows = db.scalars(
        select(KaoshiSet).where(KaoshiSet.kaoshi_id == kid, KaoshiSet.delete_time.is_(None))
    ).all()
    subj = {s.id: s.title for s in db.scalars(select(Subject)).all()}
    data = [
        {
            "id": r.id, "ruxuenian": r.ruxuenian, "nianjiname": r.nianjiname,
            "subject_name": subj.get(r.subject_id, ""), "subject_id": r.subject_id,
            "manfen": r.manfen, "youxiu": r.youxiu, "lianghao": r.lianghao, "jige": r.jige,
        }
        for r in rows
    ]
    return table(len(data), data)


@router.post("/api/kaoshi/set_save")
async def set_save(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    oid = int_or(form, "id")
    obj = db.get(KaoshiSet, oid) if oid else None
    if obj is None:
        return fail("Record not found")
    for f in ("manfen", "youxiu", "lianghao", "jige"):
        v = int_or(form, f)
        if v is not None:
            setattr(obj, f, v)
    obj.update_time = now_ts()
    db.commit()
    return ok("Saved")


@router.post("/api/kaoshi/set_init")
async def set_init(request: Request, db: Session = Depends(get_db)):
    """为某Grade初始化Subject分数线: 把「Takes exams」的SubjectAll按默认Full mark写入。"""
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    ruxuenian = int_or(form, "ruxuenian", 0)
    if not kid or not ruxuenian:
        return fail("Exam or grade is missing")

    nianjiname = form.get("nianjiname") or kh_service._nianji_name(ruxuenian)
    exist = {
        r.subject_id
        for r in db.scalars(
            select(KaoshiSet).where(
                KaoshiSet.kaoshi_id == kid,
                KaoshiSet.ruxuenian == ruxuenian,
                KaoshiSet.delete_time.is_(None),
            )
        ).all()
    }
    added = 0
    for s in db.scalars(
        select(Subject).where(Subject.kaoshi == 1, Subject.delete_time.is_(None)).order_by(Subject.paixu)
    ).all():
        if s.id in exist:
            continue
        db.add(
            KaoshiSet(
                kaoshi_id=kid, ruxuenian=ruxuenian, nianjiname=nianjiname, subject_id=s.id,
                manfen=100, youxiu=85, lianghao=75, jige=60,
            )
        )
        added += 1
    db.commit()
    return ok(f"Initialised {added} subjects", {"added": added})


@router.delete("/api/kaoshi/set_delete")
async def set_delete(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    n = crud.soft_delete(db, KaoshiSet, str(form.get("id", "")))
    return ok(f"Deleted {n} rows") if n else fail("No record to delete")


# ================================================================== 考号


@router.get("/kaohao")
def kaohao_page(request: Request, kaoshi_id: int = 0, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..main import templates

    exams = [
        {"id": k.id, "title": k.title}
        for k in db.scalars(
            select(Kaoshi).where(Kaoshi.delete_time.is_(None)).order_by(Kaoshi.bfdate.desc())
        ).all()
    ]
    return templates.TemplateResponse(request, "kaohao.html",
        {
            "request": request,
            "exams": exams,
            "kaoshi_id": kaoshi_id,
            "page": {"webtitle": "Exam numbers"},
        },
    )


@router.post("/api/kaohao/list")
async def kaohao_list(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    banji_id = int_or(form, "banji_id")
    stmt = select(Kaohao).where(Kaohao.kaoshi_id == kid, Kaohao.delete_time.is_(None))
    if banji_id:
        stmt = stmt.where(Kaohao.banji_id == banji_id)
    rows = db.scalars(stmt.order_by(Kaohao.school_id, Kaohao.banji_id, Kaohao.paixu)).all()

    stu = {s.id: s.xingming for s in db.scalars(select(Student)).all()}
    bj = {b.id: b.full_title for b in db.scalars(select(Banji)).all()}

    data = [
        {
            "id": r.id, "kaohao": r.kaohao, "student_name": stu.get(r.student_id, ""),
            "banji_name": bj.get(r.banji_id, ""), "nianji": r.nianji,
            "ruxuenian": r.ruxuenian, "paixu": r.paixu,
        }
        for r in rows
    ]
    return table(len(data), data)


@router.get("/kaohao/print")
def kaohao_print(request: Request, kaoshi_id: int = 0, db: Session = Depends(get_db)):
    """试卷标签: 可直接打印的Exam no.贴纸。"""
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..main import templates

    ks = db.get(Kaoshi, kaoshi_id)
    rows = db.scalars(
        select(Kaohao)
        .where(Kaohao.kaoshi_id == kaoshi_id, Kaohao.delete_time.is_(None))
        .order_by(Kaohao.banji_id, Kaohao.paixu)
    ).all()
    stu = {s.id: s.xingming for s in db.scalars(select(Student)).all()}
    bj = {b.id: b.full_title for b in db.scalars(select(Banji)).all()}
    labels = [
        {
            "kaohao": r.kaohao,
            "xingming": stu.get(r.student_id, ""),
            "banji": bj.get(r.banji_id, ""),
        }
        for r in rows
    ]
    return templates.TemplateResponse(request, "kaohao_print.html",
        {"request": request, "kaoshi": ks, "labels": labels, "page": {"webtitle": "Label sheet"}},
    )


@router.post("/api/kaohao/generate")
async def kaohao_generate(request: Request, db: Session = Depends(get_db)):
    """为选中的Class生成Exam no.。"""
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    banji_ids = [int(x) for x in str(form.get("banji_ids", "")).split(",") if x.strip().isdigit()]
    if not kid:
        return fail("Select an exam first")
    if not banji_ids:
        return fail("Select a class first")
    res = kh_service.generate(kid, banji_ids, db)
    return ok(f"Created {res['created']} exam numbers, skipped {res['skipped']} existing", res)


@router.post("/api/kaohao/clear")
async def kaohao_clear(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    if not kid:
        return fail("Select an exam first")
    # 先删成绩，再删考号
    kh_ids = [k.id for k in db.scalars(select(Kaohao).where(Kaohao.kaoshi_id == kid)).all()]
    if kh_ids:
        db.query(Chengji).filter(Chengji.kaohao_id.in_(kh_ids)).delete(synchronize_session=False)
    n = kh_service.delete_by_kaoshi(kid, db)
    return ok(f"Cleared {n} exam numbers and their grades")
