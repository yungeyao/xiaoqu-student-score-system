"""统一响应格式。

前端（static/x-admin2.2/js/mytable.js 与各页面脚本）按两种格式消费接口：
  * 业务接口  -> {"val": 1|0, "msg": "...", "data": {...}}
  * 表格接口  -> {"code": 0, "msg": "", "count": N, "data": [...]}
"""
from typing import Any

from fastapi.responses import JSONResponse


def ok(msg: str = "操作成功", data: Any = None) -> dict:
    return {"val": 1, "msg": msg, "data": data}


def fail(msg: str = "操作失败", data: Any = None) -> dict:
    return {"val": 0, "msg": msg, "data": data}


def table(count: int, rows: list, msg: str = "") -> dict:
    """layui table 的数据接口格式，code=0 表示成功。"""
    return {"code": 0, "msg": msg, "count": count, "data": rows}


def json_ok(msg: str = "操作成功", data: Any = None) -> JSONResponse:
    return JSONResponse(ok(msg, data))


def json_fail(msg: str = "操作失败", data: Any = None) -> JSONResponse:
    return JSONResponse(fail(msg, data))
