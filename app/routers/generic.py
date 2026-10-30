"""通用 CRUD 路由：为 registry 中声明的每个模块自动生成列表页、表单页和接口。

生成的接口（以 school 为例）：
    GET    /school              列表页
    GET    /school/create       表单页
    POST   /api/school/list     表格数据（layui 格式）
    POST   /api/school/save     新增 / 更新
    DELETE /api/school/delete   软删除
    POST   /api/school/status   启停开关
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_db, require_admin
from ..core.response import fail, ok, table
from ..models.base import now_ts, str_to_ts
from ..registry import MODULES, Module
from ..services import crud
from ..services.crud import int_or, page_limit
from ..services.serialize import resolve_options, row_to_dict

router = APIRouter()


def _cols(m: Module) -> list[dict]:
    """构造 layui 表格列定义。"""
    cols = []
    for f in m.list_fields():
        if f.name == "status":
            cols.append(
                {"field": "status", "title": "状态", "width": f.width, "templet": "#statusTpl"}
            )
            continue
        col = {"field": f.name, "title": f.label, "width": f.width, "sort": True}
        if f.options_from == "sex":
            # 固定枚举列显示中文标签（见 services.serialize.row_to_dict）
            col["field"] = f"{f.name}_label"
        if f.ref:
            col["field"] = f"{f.name}_name"
        cols.append(col)
    return cols


def _render_list(request, m: Module, db: Session, user):
    from ..main import templates

    page = {
        "webtitle": m.title,
        "dataurl": f"/api/{m.key}/list",
        "create_url": f"/{m.key}/create",
        "delete_url": f"/api/{m.key}/delete",
        "status_url": f"/api/{m.key}/status",
        "cols": _cols(m),
        "toolbar": [{"event": "add", "title": "新增"}, {"event": "delete", "title": "批量删除"}]
        + m.extra_toolbar,
        "rowbar": m.rowbar or [{"event": "edit", "title": "编辑"}],
        "can_delete": True,
        "search_fields": [
            {
                "name": f.name,
                "label": f.label,
                "type": f.type,
                "options": resolve_options(db, f.options_from),
            }
            for f in m.search_defs()
        ],
    }
    # 关键字搜索框：几乎每个列表都需要
    if m.search_fields:
        page["search_fields"].insert(0, {"name": "searchval", "label": "关键字", "type": "text"})
    return templates.TemplateResponse(request, "generic_list.html", {"request": request, "page": page}
    )


def _render_form(request, m: Module, db: Session, obj_id):
    from ..main import templates

    obj = db.get(m.model, obj_id) if obj_id else None
    fields = []
    for f in m.form_fields():
        fields.append(
            {
                "name": f.name,
                "label": f.label,
                "type": f.type,
                "required": f.required,
                "placeholder": f.placeholder,
                "options": resolve_options(db, f.options_from),
            }
        )
    page = {
        "webtitle": ("编辑" if obj else "新增") + m.title,
        "url": f"/api/{m.key}/save",
        "formpost": "POST",
        "fields": fields,
        "obj": row_to_dict(db, obj, m.form_fields()) if obj else {},
    }
    return templates.TemplateResponse(request, "generic_form.html", {"request": request, "page": page}
    )


def _register(m: Module):
    @router.get(f"/{m.key}", name=f"page_{m.key}")
    def _list(request: Request, db: Session = Depends(get_db)):
        user, cat, redirect = require_admin(request, db)
        if redirect:
            return redirect
        return _render_list(request, m, db, user)

    @router.get(f"/{m.key}/create", name=f"form_{m.key}")
    def _form(request: Request, id: int = 0, db: Session = Depends(get_db)):
        user, cat, redirect = require_admin(request, db)
        if redirect:
            return redirect
        return _render_form(request, m, db, id)

    @router.post(f"/api/{m.key}/list")
    async def _data(request: Request, db: Session = Depends(get_db)):
        form = await _async_form(request)
        page_no, limit = page_limit(form)

        stmt = select(m.model).where(m.model.delete_time.is_(None))
        kw = form.get("searchval")
        if kw and m.search_fields:
            cond = crud.keyword_where(m.model, m.search_fields, kw)
            if cond is not None:
                stmt = stmt.where(cond)
        for f in m.search_defs():
            v = form.get(f.name)
            if v not in (None, ""):
                stmt = stmt.where(getattr(m.model, f.name) == v)

        order = getattr(m.model, m.order_by.lstrip("-"))
        stmt = stmt.order_by(order.desc() if m.order_by.startswith("-") else order)

        rows, total = crud.paginate(db, stmt, page_no, limit)
        return table(total, [row_to_dict(db, r, m.list_fields()) for r in rows])

    @router.post(f"/api/{m.key}/save")
    async def _save(request: Request, db: Session = Depends(get_db)):
        form = await _async_form(request)
        obj_id = int_or(form, "id")
        data = {}
        for f in m.form_fields():
            if f.name not in form:
                continue
            raw = form.get(f.name)
            if f.type == "date":
                data[f.name] = str_to_ts(raw)
            elif f.type == "number":
                data[f.name] = int_or(form, f.name)
            elif f.type == "switch":
                data[f.name] = 1 if raw in ("1", "on", "true", 1, True) else 0
            else:
                data[f.name] = raw
        obj = db.get(m.model, obj_id) if obj_id else None
        is_new = obj is None
        if is_new:
            obj = m.model()
            db.add(obj)
        # 新增时表单会带 id=0 的隐藏域，写进去会占掉 0 号主键
        pk = m.model.__mapper__.primary_key[0].name
        for k, v in data.items():
            if k == pk and is_new:
                continue
            setattr(obj, k, v)
        obj.update_time = now_ts()
        db.commit()
        db.refresh(obj)
        return ok("保存成功", {"id": obj.id})

    @router.delete(f"/api/{m.key}/delete")
    async def _delete(request: Request, id: str = "", db: Session = Depends(get_db)):
        # 优先取查询串，其次取表单体：直接 curl/fetch 调 DELETE 时常不带 body
        id_str = id or (await _async_form(request)).get("id", "")
        n = crud.soft_delete(db, m.model, str(id_str))
        return ok(f"已删除 {n} 条") if n else fail("没有可删除的记录")

    @router.post(f"/api/{m.key}/status")
    async def _status(request: Request, db: Session = Depends(get_db)):
        form = await _async_form(request)
        oid = int_or(form, "id")
        val = int_or(form, "value", 0)
        field_name = form.get("ziduan") or "status"
        if not hasattr(m.model, field_name):
            return fail("字段不存在")
        return (
            ok("已修改")
            if crud.set_status(db, m.model, oid, val, field_name)
            else fail("记录不存在")
        )


async def _async_form(request: Request) -> dict:
    body = await request.form()
    return dict(body)


for _m in MODULES:
    _register(_m)
