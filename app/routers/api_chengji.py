"""Grade entry (在线 / 表格导入)与GradeQuery。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_db, require_admin
from ..core.response import fail, ok, table
from ..models import Banji, Chengji, Kaohao, Kaoshi, KaoshiSet, Student, Subject
from ..models.base import now_ts
from ..services import chengji_io
from ..services.crud import int_or

router = APIRouter(tags=["chengji"])


async def _form(request: Request) -> dict:
    return dict(await request.form())


def _scope(request: Request, db):
    """当前登录者的数据范围。"""
    from ..services.permission import data_scope

    user, _cat, _r = require_admin(request, db)
    return data_scope(db, user)


def _visible_banjis(request: Request, db) -> list:
    """按数据权限返回当前用户可见的Class。"""
    from ..services.permission import data_scope

    user, _cat, _r = require_admin(request, db)
    sc = data_scope(db, user)
    q = select(Banji).where(Banji.delete_time.is_(None))
    if not sc["all"]:
        q = q.where(Banji.id.in_(sc["banji_ids"] or [0]))
    return list(db.scalars(q.order_by(Banji.paixu)).all())


def _subjects(db, kaoshi_id: int, ruxuenian: int = 0):
    q = select(KaoshiSet).where(KaoshiSet.kaoshi_id == kaoshi_id, KaoshiSet.delete_time.is_(None))
    if ruxuenian:
        q = q.where(KaoshiSet.ruxuenian == ruxuenian)
    sids = [r[0] for r in db.execute(select(KaoshiSet.subject_id).where(
        KaoshiSet.kaoshi_id == kaoshi_id, KaoshiSet.delete_time.is_(None))).all()]
    if not sids:
        return []
    return db.scalars(select(Subject).where(Subject.id.in_(sids)).order_by(Subject.paixu)).all()


# ================================================================== 页面


@router.get("/luru")
def luru_page(request: Request, kaoshi_id: int = 0, m: str = "online", db: Session = Depends(get_db)):
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
    banjis = [{"id": b.id, "title": b.full_title} for b in _visible_banjis(request, db)]
    return templates.TemplateResponse(request, "luru.html",
        {
            "request": request,
            "exams": exams,
            "banjis": banjis,
            "kaoshi_id": kaoshi_id,
            "mode": m,
            "page": {"webtitle": "Grade entry"},
        },
    )


@router.get("/chengji")
def chengji_page(request: Request, kaoshi_id: int = 0, db: Session = Depends(get_db)):
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
    banjis = [{"id": b.id, "title": b.full_title} for b in _visible_banjis(request, db)]
    return templates.TemplateResponse(request, "chengji.html",
        {
            "request": request,
            "exams": exams,
            "banjis": banjis,
            "kaoshi_id": kaoshi_id,
            "page": {"webtitle": "GradeQuery"},
        },
    )


# ================================================================== 在线录入


@router.post("/api/luru/subjects")
async def luru_subjects(request: Request, db: Session = Depends(get_db)):
    """某场Exam可选Subject。"""
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    subs = _subjects(db, kid)
    return ok("", [{"id": s.id, "title": s.title} for s in subs])


@router.post("/api/luru/matrix")
async def luru_matrix(request: Request, db: Session = Depends(get_db)):
    """返回「Student × Subject」的Grade矩阵, 用于Online entry。"""
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    banji_id = int_or(form, "banji_id", 0)
    if not kid or not banji_id:
        return ok("", {"subjects": [], "rows": []})

    # 越权保护：教师只能录入自己可见班级的成绩
    sc = _scope(request, db)
    if not sc["all"] and banji_id not in set(sc["banji_ids"]):
        return ok("", {"subjects": [], "rows": []})

    subs = _subjects(db, kid)
    khs = db.scalars(
        select(Kaohao)
        .where(Kaohao.kaoshi_id == kid, Kaohao.banji_id == banji_id, Kaohao.delete_time.is_(None))
        .order_by(Kaohao.paixu)
    ).all()

    cj = {}
    if khs:
        for kh_id, sid, defen in db.execute(
            select(Chengji.kaohao_id, Chengji.subject_id, Chengji.defen).where(
                Chengji.kaohao_id.in_([k.id for k in khs])
            )
        ).all():
            cj[(kh_id, sid)] = None if defen is None else float(defen)

    rows = []
    for k in khs:
        stu = db.get(Student, k.student_id)
        rows.append(
            {
                "kaohao_id": k.id,
                "kaohao": k.kaohao,
                "student_name": stu.xingming if stu else "",
                "scores": {s.id: cj.get((k.id, s.id)) for s in subs},
            }
        )
    return ok("", {"subjects": [{"id": s.id, "title": s.title} for s in subs], "rows": rows})


@router.post("/api/luru/save")
async def luru_save(request: Request, db: Session = Depends(get_db)):
    """保存一整屏Grade。scores 为 JSON 字符串: [{kaohao_id, subject_id, defen}]"""
    import json

    form = await _form(request)
    raw = form.get("scores") or "[]"
    try:
        items = json.loads(raw)
    except (ValueError, TypeError):
        return fail("Malformed data")
    user, cat, _ = require_admin(request, db)
    uid = user.id if user else 0

    n = 0
    for it in items:
        kh_id = int(it.get("kaohao_id") or 0)
        sid = int(it.get("subject_id") or 0)
        if not kh_id or not sid:
            continue
        v = it.get("defen")
        defen = None
        if v not in (None, "", "null"):
            try:
                defen = round(float(v), 1)
            except (TypeError, ValueError):
                continue
        cj = db.scalars(
            select(Chengji).where(Chengji.kaohao_id == kh_id, Chengji.subject_id == sid)
        ).first()
        if cj is None:
            cj = Chengji(kaohao_id=kh_id, subject_id=sid, user_id=uid)
            db.add(cj)
        cj.defen = defen
        cj.user_id = uid
        cj.update_time = now_ts()
        n += 1
    db.commit()
    return ok(f"Saved {n} grade rows", {"count": n})


# ================================================================== 表格导入导出


@router.get("/api/luru/export")
def luru_export(kaoshi_id: int = 0, banji_id: int = 0, db: Session = Depends(get_db)):
    if not kaoshi_id:
        return fail("Select an exam first")
    buf = chengji_io.export_template(kaoshi_id, banji_id or None, db)
    ks = db.get(Kaoshi, kaoshi_id)
    name = f"{ks.title if ks else 'grades'}_grade_template.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_quote(name)}"},
    )


def _quote(name: str) -> str:
    from urllib.parse import quote

    return quote(name)


@router.post("/api/luru/import")
async def luru_import(
    request: Request,
    kaoshi_id: int = Form(0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user, cat, _ = require_admin(request, db)
    uid = user.id if user else 0
    if not kaoshi_id:
        return fail("Select an exam first")
    content = await file.read()
    try:
        res = chengji_io.import_scores(kaoshi_id, content, uid, db)
    except Exception as e:  # noqa: BLE001
        return fail(f"Import failed: {e}")
    err = res["err"]
    return ok(res["success"] + (f" ({len(err)} rows with errors)" if err else ""), {"success": res["success"], "err": err[:50]})


# ================================================================== 成绩查询


@router.post("/api/chengji/list")
async def chengji_list(request: Request, db: Session = Depends(get_db)):
    """StudentGrade清单: 一行一个Student, 一列一个Subject。"""
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    banji_id = int_or(form, "banji_id")
    kw = (form.get("searchval") or "").strip()
    page_no = int(form.get("page") or 1)
    limit = int(form.get("limit") or 20)

    if not kid:
        return table(0, [])

    subs = _subjects(db, kid)
    q = select(Kaohao).where(Kaohao.kaoshi_id == kid, Kaohao.delete_time.is_(None))
    if banji_id:
        q = q.where(Kaohao.banji_id == banji_id)
    else:
        sc = _scope(request, db)
        if not sc["all"]:
            q = q.where(Kaohao.banji_id.in_(sc["banji_ids"] or [0]))

    khs = list(db.scalars(q.order_by(Kaohao.banji_id, Kaohao.paixu)).all())
    if kw:
        ids = [k.student_id for k in khs]
        matched = {
            s.id
            for s in db.scalars(select(Student).where(Student.id.in_(ids))).all()
            if kw in (s.xingming or "")
        }
        khs = [k for k in khs if k.student_id in matched]

    total = len(khs)
    khs = khs[(page_no - 1) * limit : page_no * limit]

    cj = {}
    if khs:
        for kh_id, sid, defen, bpaixu in db.execute(
            select(Chengji.kaohao_id, Chengji.subject_id, Chengji.defen, Chengji.bpaixu).where(
                Chengji.kaohao_id.in_([k.id for k in khs])
            )
        ).all():
            cj[(kh_id, sid)] = (None if defen is None else float(defen), bpaixu)

    bj = {b.id: b.full_title for b in db.scalars(select(Banji)).all()}
    data = []
    for k in khs:
        stu = db.get(Student, k.student_id)
        row = {
            "id": k.id,
            "kaohao": k.kaohao,
            "student_name": stu.xingming if stu else "",
            "banji_name": bj.get(k.banji_id, ""),
        }
        total_score = 0.0
        has_all = True
        for s in subs:
            v, _p = cj.get((k.id, s.id), (None, None))
            row[f"s{s.id}"] = v
            if v is None:
                has_all = False
            else:
                total_score += v
        row["total"] = round(total_score, 1) if has_all else None
        data.append(row)

    return table(total, data)


@router.post("/api/chengji/subjects")
async def chengji_subjects(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    subs = _subjects(db, kid)
    return ok("", [{"id": s.id, "title": s.title} for s in subs])
