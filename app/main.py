"""应用入口。"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .core.config import SESSION_COOKIE, Site, STATIC_DIR
from .registry import bind_models
from .routers import (
    api_base,
    api_chengji,
    api_kaoshi,
    api_risk,
    api_teaching,
    api_tongji,
    auth,
    generic,
    page,
    portal,
    report,
)

bind_models()

app = FastAPI(title=Site.webtitle, version=Site.version)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(STATIC_DIR.parent / "templates"))
templates.env.globals.update(
    {
        "XADMIN": "/static/x-admin2.2",
        "STATIC": "/static",
        "webtitle": Site.webtitle,
        "danwei": Site.danwei,
        "version": Site.version,
    }
)

app.include_router(auth.router)
app.include_router(page.router)
app.include_router(generic.router)
app.include_router(portal.router)
app.include_router(api_base.router)
app.include_router(api_kaoshi.router)
app.include_router(api_chengji.router)
app.include_router(api_tongji.router)
app.include_router(api_teaching.router)
app.include_router(api_risk.router)
app.include_router(report.router)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"val": 0, "msg": "接口不存在"}, status_code=404)
    return RedirectResponse("/")


@app.get("/healthz")
def healthz():
    return {"ok": True}
