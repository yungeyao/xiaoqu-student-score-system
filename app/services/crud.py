"""列表查询与写操作的公共辅助。

layui table 会带 page / limit 两个分页参数，搜索条件以表单字段提交。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session


def page_limit(form: dict) -> tuple[int, int]:
    try:
        page = int(form.get("page") or 1)
    except (TypeError, ValueError):
        page = 1
    try:
        limit = int(form.get("limit") or 10)
    except (TypeError, ValueError):
        limit = 10
    return max(page, 1), max(limit, 1)


def keyword_where(model, fields: list[str], keyword: Optional[str]):
    """对若干字符串字段做模糊匹配。"""
    if not keyword or not fields:
        return None
    kw = f"%{keyword.strip()}%"
    conds = []
    for f in fields:
        col = getattr(model, f, None)
        if col is not None:
            conds.append(col.like(kw))
    return or_(*conds) if conds else None


def paginate(db: Session, stmt, page: int, limit: int):
    """执行分页查询，返回 (rows, total)。"""
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.offset((page - 1) * limit).limit(limit)).scalars().all()
    return rows, total


def int_or(form: dict, key: str, default=None):
    v = form.get(key)
    if v in (None, "", "undefined"):
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def save_one(db: Session, model, form: dict, obj_id: Optional[int], fields: list[str]):
    """新增或更新一条记录，只写入 fields 中声明过的字段。

    新增时**必须跳过主键**：表单为表示「新建」会带一个 ``id=0`` 的隐藏域，
    若照写会把主键设成 0（SQLite 允许），该行之后无法按 id 编辑或删除。
    """
    obj = db.get(model, obj_id) if obj_id else None
    is_new = obj is None
    if is_new:
        obj = model()
        db.add(obj)

    pk = model.__mapper__.primary_key[0].name
    for f in fields:
        if f == pk and is_new:
            continue
        if f in form:
            setattr(obj, f, form.get(f))
    db.commit()
    db.refresh(obj)
    return obj


def soft_delete(db: Session, model, id_str: str) -> int:
    """软删除，支持逗号分隔的批量 id。"""
    from ..models.base import now_ts

    ids = [int(x) for x in str(id_str).split(",") if str(x).strip().isdigit()]
    if not ids:
        return 0
    cnt = 0
    for i in ids:
        obj = db.get(model, i)
        if obj is not None:
            obj.delete_time = now_ts()
            cnt += 1
    db.commit()
    return cnt


def set_status(db: Session, model, obj_id: int, value: int, field: str = "status") -> bool:
    obj = db.get(model, obj_id)
    if obj is None:
        return False
    setattr(obj, field, value)
    db.commit()
    return True
