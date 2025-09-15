
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from core.contract import InEnvelope, Context
from core.runner import execute
from core.errors import FrameworkError
from db.sqlite import init_basic_schema
import importlib.util, os

app = FastAPI(title="Module Framework API", version="1.1.0")

@app.on_event("startup")
async def _startup():
    # 자동 테이블 생성 (sqlite 기반)
    init_basic_schema()

def _ctx_from_request(req: Request) -> Context:
    scopes_hdr = req.headers.get("X-Scopes", "")
    scopes = [s.strip() for s in scopes_hdr.split(",") if s.strip()]
    rid = req.headers.get("X-Request-Id")
    return Context(request_id=rid, scopes=scopes, vars={})

@app.post("/run")
async def run_endpoint(request: Request, name: str = Query(..., description="모듈 이름(e.g., modules.common.ping)")):
    payload = await request.json()
    env = InEnvelope(**payload)
    ctx = _ctx_from_request(request)
    try:
        out = execute(name, env, ctx)
        return JSONResponse(out.model_dump())
    except FrameworkError as fe:
        return JSONResponse(status_code=400, content={"ok": False, "mode": env.mode,
                                                      "error": {"code": fe.code, "message": str(fe), "details": fe.details}})
    except Exception as ex:
        return JSONResponse(status_code=500, content={"ok": False, "mode": env.mode,
                                                      "error": {"code": "ERR_INTERNAL", "message": str(ex)}})

@app.post("/batch/run")
async def batch_endpoint(request: Request, name: str):
    payload = await request.json()
    payload["mode"] = "BULK"
    env = InEnvelope(**payload)
    ctx = _ctx_from_request(request)
    out = execute(name, env, ctx)
    return JSONResponse(out.model_dump())

def _load_page_module(name: str):
    # name='auth' -> pages/auth_main.py
    base = os.path.join("pages", f"{name}_main.py")
    if not os.path.exists(base):
        raise FileNotFoundError(f"page not found: {base}")
    spec = importlib.util.spec_from_file_location(f"pages.{name}_main", base)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod

@app.post("/page/run")
async def page_run(request: Request, name: str = Query(..., description="페이지 이름(e.g., auth)")):
    payload = await request.json()
    page = _load_page_module(name)
    ctx = _ctx_from_request(request)
    # 페이지는 오케스트레이터: 딱 필요한 JSON만 반환
    try:
        out_json = page.run(payload, ctx)
        return JSONResponse(out_json)
    except Exception as ex:
        return JSONResponse(status_code=500, content={"ok": False, "error": {"code": "ERR_PAGE", "message": str(ex)}})

@app.get("/health")
async def health():
    return {"ok": True}
