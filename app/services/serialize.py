"""把模型对象序列化成前端要的字典, 并解析下拉选项 / 外键显示名。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from ..models import Admin, Banji, Category, Course, School, Student, Subject, Teacher, Xueqi
from ..models.base import ts_to_str

SEX_LABELS = {0: "Female", 1: "Male", 2: "Unknown"}

SEX_OPTIONS = [{"value": k, "label": v} for k, v in SEX_LABELS.items()]


def resolve_options(db, source: Optional[str]) -> list[dict]:
    """把 options_from 解析成 [{value, label}]。"""
    if not source:
        return []
    if source == "sex":
        return SEX_OPTIONS
    if source.startswith("category:"):
        pid = int(source.split(":")[1])
        rows = db.scalars(
            select(Category)
            .where(Category.p_id == pid, Category.delete_time.is_(None))
            .order_by(Category.paixu)
        ).all()
        return [{"value": r.id, "label": r.title} for r in rows]
    return [{"value": r[0], "label": r[1]} for r in _rows(db, source)]


def _rows(db, source: str):
    if source == "school":
        q = select(School.id, School.title).where(School.delete_time.is_(None))
    elif source == "banji":
        rows = db.scalars(
            select(Banji).where(Banji.delete_time.is_(None)).order_by(Banji.school_id, Banji.paixu)
        ).all()
        return [(r.id, r.full_title) for r in rows]
    elif source == "subject":
        q = select(Subject.id, Subject.title).where(Subject.delete_time.is_(None))
    elif source == "teacher":
        q = select(Teacher.id, Teacher.xingming).where(Teacher.delete_time.is_(None))
    elif source == "student":
        q = select(Student.id, Student.xingming).where(Student.delete_time.is_(None))
    elif source == "admin":
        q = select(Admin.id, Admin.xingming).where(Admin.delete_time.is_(None))
    elif source == "xueqi":
        q = select(Xueqi.id, Xueqi.title).where(Xueqi.delete_time.is_(None))
    elif source == "course":
        rows = db.scalars(
            select(Course).where(Course.delete_time.is_(None)).order_by(Course.banji_id, Course.title)
        ).all()
        return [(r.id, r.title) for r in rows]
    else:
        return []
    return db.execute(q).all()


_REF_CACHE: dict[tuple, dict] = {}


def _ref_map(db, table: str, attr: str) -> dict:
    """缓存 {id: 显示名}。"""
    key = (table, attr)
    if key in _REF_CACHE:
        return _REF_CACHE[key]
    if table == "category":
        rows = db.scalars(select(Category)).all()
        m = {r.id: getattr(r, attr, "") for r in rows}
    elif table == "school":
        rows = db.scalars(select(School)).all()
        m = {r.id: getattr(r, attr, "") for r in rows}
    elif table == "banji":
        rows = db.scalars(select(Banji)).all()
        m = {r.id: (r.full_title if attr == "full_title" else getattr(r, attr, "")) for r in rows}
    elif table == "subject":
        rows = db.scalars(select(Subject)).all()
        m = {r.id: getattr(r, attr, "") for r in rows}
    elif table == "teacher":
        rows = db.scalars(select(Teacher)).all()
        m = {r.id: getattr(r, attr, "") for r in rows}
    elif table == "xueqi":
        rows = db.scalars(select(Xueqi)).all()
        m = {r.id: getattr(r, attr, "") for r in rows}
    elif table == "course":
        rows = db.scalars(select(Course)).all()
        m = {r.id: getattr(r, attr, "") for r in rows}
    else:
        m = {}
    _REF_CACHE[key] = m
    return m


def clear_cache():
    _REF_CACHE.clear()


def row_to_dict(db, obj, fields, extra: Optional[dict] = None) -> dict:
    """按 fields 声明把 ORM 对象转成字典。

    * date 字段自动转成 YYYY-MM-DD
    * 声明了 ref 的外键字段，额外输出 ``{name}_name``
    """
    out = {"id": obj.id}
    for f in fields:
        val = getattr(obj, f.name, None)
        if f.type == "date":
            out[f.name] = ts_to_str(val)
        elif val is None:
            out[f.name] = ""
        else:
            out[f.name] = val
        if f.options_from == "sex":
            # 性别是固定枚举：额外输出中文标签，列表里直接显示「男 / 女」而不是 0 / 1
            out[f"{f.name}_label"] = SEX_LABELS.get(val, "")
        if f.ref:
            table, attr = f.ref.split(".", 1)
            out[f"{f.name}_name"] = _ref_map(db, table, attr).get(val, "")
    if extra:
        out.update(extra)
    return out
