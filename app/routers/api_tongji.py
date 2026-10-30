"""统计分析：执行统计、三级统计表、图表数据。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_db, require_admin
from ..core.response import fail, ok, table
from ..models import Banji, Kaoshi, KaoshiSet, School, Subject, TongjiBj, TongjiNj, TongjiSch
from ..services import tongji as tj_service
from ..services.crud import int_or

router = APIRouter(tags=["tongji"])


async def _form(request: Request) -> dict:
    return dict(await request.form())


def _exam_options(db):
    return [
        {"id": k.id, "title": k.title}
        for k in db.scalars(
            select(Kaoshi).where(Kaoshi.delete_time.is_(None)).order_by(Kaoshi.bfdate.desc())
        ).all()
    ]


def _subject_options(db, kaoshi_id: int = 0):
    subs = db.scalars(
        select(Subject).where(Subject.delete_time.is_(None)).order_by(Subject.paixu)
    ).all()
    return [{"id": s.id, "title": s.title} for s in subs]


# ================================================================== 页面


def _page(request, db, level: str, title: str):
    from ..main import templates

    return templates.TemplateResponse(request, "tongji.html",
        {
            "request": request,
            "exams": _exam_options(db),
            "subjects": _subject_options(db),
            "level": level,
            "page": {"webtitle": title},
        },
    )


@router.get("/tongji/bj")
def bj_page(request: Request, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    return _page(request, db, "bj", "班级成绩统计")


@router.get("/tongji/nj")
def nj_page(request: Request, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    return _page(request, db, "nj", "年级成绩统计")


@router.get("/tongji/sch")
def sch_page(request: Request, db: Session = Depends(get_db)):
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return redirect
    return _page(request, db, "sch", "全校成绩统计")


# ================================================================== 执行统计


@router.post("/api/tongji/run")
async def run(request: Request, db: Session = Depends(get_db)):
    """重算三级统计。"""
    user, cat, redirect = require_admin(request, db)
    if redirect:
        return fail("未登录")
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    if not kid:
        return fail("请先选择考试")
    res = tj_service.tongji(kid)
    return ok(
        f"统计完成：班级 {res['bj']} 条、年级 {res['nj']} 条、全校 {res['sch']} 条", res
    )


@router.post("/api/tongji/order")
async def order(request: Request, db: Session = Depends(get_db)):
    """计算排名与位置百分位。"""
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    if not kid:
        return fail("请先选择考试")
    n = tj_service.save_order(kid)
    return ok(f"已更新 {n} 条成绩的排名", {"count": n})


@router.post("/api/tongji/biaozhunfen")
async def biaozhunfen(request: Request, db: Session = Depends(get_db)):
    """计算标准分（依赖全校统计已执行）。"""
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    if not kid:
        return fail("请先选择考试")
    n = tj_service.biaozhunfen(kid)
    if n == 0:
        return fail("请先执行全校统计")
    return ok(f"已计算 {n} 条标准分", {"count": n})


# ================================================================== 统计表数据


def _base_rows(db, model, kid, subject_id, extra_label: bool = False, banji_id: int = 0):
    q = select(model).where(model.kaoshi_id == kid, model.delete_time.is_(None))
    if subject_id is not None:
        q = q.where(model.subject_id == subject_id)
    if banji_id and hasattr(model, "banji_id"):
        q = q.where(model.banji_id == banji_id)
    return db.scalars(q).all()


def _dump(r, name: str):
    return {
        "id": r.id,
        "name": name,
        "subject_id": r.subject_id,
        "stu_cnt": r.stu_cnt,
        "chengji_cnt": r.chengji_cnt,
        "avg": _f(r.avg),
        "defenlv": _f(r.defenlv),
        "biaozhuncha": _f(r.biaozhuncha),
        "youxiu": r.youxiu,
        "youxiulv": _f(r.youxiulv),
        "lianghao": r.lianghao,
        "lianghaolv": _f(r.lianghaolv),
        "jige": r.jige,
        "jigelv": _f(r.jigelv),
        "canshilv": _f(r.canshilv),
        "chashenglv": _f(r.chashenglv),
        "max": _f(r.max),
        "min": _f(r.min),
        "q1": _f(r.q1),
        "q2": _f(r.q2),
        "q3": _f(r.q3),
        "zhongweishu": _f(r.zhongweishu),
        "zhongshu": r.zhongshu,
    }


def _f(v):
    return None if v is None else float(v)


def _scope(request, db):
    """当前登录者的数据范围；未登录返回空范围。"""
    from ..services.permission import data_scope

    user, _cat, _r = require_admin(request, db)
    return data_scope(db, user)


@router.post("/api/tongji/bj_list")
async def bj_list(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    sid = int_or(form, "subject_id")
    if not kid:
        return table(0, [])
    bj = {b.id: b.full_title for b in db.scalars(select(Banji)).all()}
    rows = _base_rows(db, TongjiBj, kid, sid)
    sc = _scope(request, db)
    if not sc["all"]:
        rows = [r for r in rows if r.banji_id in set(sc["banji_ids"])]
    data = [_dump(r, bj.get(r.banji_id, "")) for r in rows]
    data.sort(key=lambda x: (x["avg"] is None, -(x["avg"] or 0)))
    return table(len(data), data)


@router.post("/api/tongji/nj_list")
async def nj_list(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    sid = int_or(form, "subject_id")
    if not kid:
        return table(0, [])
    sch = {s.id: s.title for s in db.scalars(select(School)).all()}
    rows = _base_rows(db, TongjiNj, kid, sid)
    sc = _scope(request, db)
    if not sc["all"]:
        keys = {tuple(k) for k in sc["nj_keys"]}
        rows = [r for r in rows if (r.school_id, r.ruxuenian) in keys]
    data = [_dump(r, f"{sch.get(r.school_id, '')} {r.ruxuenian}级") for r in rows]
    data.sort(key=lambda x: (x["avg"] is None, -(x["avg"] or 0)))
    return table(len(data), data)


@router.post("/api/tongji/sch_list")
async def sch_list(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    sid = int_or(form, "subject_id")
    if not kid:
        return table(0, [])
    rows = _base_rows(db, TongjiSch, kid, sid)
    sc = _scope(request, db)
    if not sc["all"]:
        rs = set(sc["ruxuenians"])
        rows = [r for r in rows if r.ruxuenian in rs]
    data = [_dump(r, f"{r.ruxuenian}级") for r in rows]
    data.sort(key=lambda x: (x["avg"] is None, -(x["avg"] or 0)))
    return table(len(data), data)


# ================================================================== 图表数据


@router.post("/api/tongji/chart")
async def chart(request: Request, db: Session = Depends(get_db)):
    """图表数据。type=avg 平均分对比；type=rate 优秀/及格率；type=score 分数段人数。"""
    from ..models import Chengji, Kaohao

    form = await _form(request)
    kid = int_or(form, "kaoshi_id", 0)
    sid = int_or(form, "subject_id")
    level = form.get("level") or "bj"
    ctype = form.get("type") or "avg"
    if not kid:
        return ok("", {"categories": [], "series": []})

    if ctype == "score":
        return _score_segment(db, kid, sid)

    model = {"bj": TongjiBj, "nj": TongjiNj, "sch": TongjiSch}.get(level, TongjiBj)
    rows = _base_rows(db, model, kid, sid)
    bj = {b.id: b.full_title for b in db.scalars(select(Banji)).all()}
    sch = {s.id: s.title for s in db.scalars(select(School)).all()}

    cats, avgs, youxiu, jige = [], [], [], []
    for r in rows:
        if level == "bj":
            cats.append(bj.get(r.banji_id, ""))
        elif level == "nj":
            cats.append(f"{sch.get(r.school_id, '')}{r.ruxuenian}级")
        else:
            cats.append(f"{r.ruxuenian}级")
        avgs.append(_f(r.avg))
        youxiu.append(_f(r.youxiulv))
        jige.append(_f(r.jigelv))

    if ctype == "rate":
        series = [
            {"name": "优秀率", "data": youxiu},
            {"name": "及格率", "data": jige},
        ]
    else:
        series = [{"name": "平均分", "data": avgs}]
    return ok("", {"categories": cats, "series": series})


def _score_segment(db, kid, subject_id):
    """分数段人数分布：按 10 分一段统计。"""
    from ..models import Chengji, Kaohao

    rows = db.execute(
        select(Chengji.defen)
        .join(Kaohao, Kaohao.id == Chengji.kaohao_id)
        .where(Kaohao.kaoshi_id == kid, Chengji.subject_id == subject_id)
    ).scalars().all()
    values = [float(v) for v in rows if v is not None]
    buckets = [0] * 10
    labels = [f"{i*10}-{i*10+9}" for i in range(9)] + ["90-100"]
    for v in values:
        idx = min(int(v // 10), 9)
        buckets[idx] += 1
    return ok("", {"categories": labels, "series": [{"name": "人数", "data": buckets}]})
