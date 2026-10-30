"""通用 JSON 接口：下拉选项等。"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..core.deps import get_db
from ..core.response import ok
from ..services.serialize import resolve_options

router = APIRouter(tags=["base"])


@router.post("/api/options")
async def options(request: Request, db: Session = Depends(get_db)):
    """按 source 返回下拉选项，source 形如 category:101 / school / banji / subject。"""
    form = dict(await request.form())
    return ok("", resolve_options(db, form.get("source")))
