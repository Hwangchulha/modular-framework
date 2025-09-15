
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from core.contract import InEnvelope, Context
from core.runner import execute
from core.errors import FrameworkError

app = FastAPI(title="Module Framework API", version="1.0.0")

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

@app.get("/health")
async def health():
    return {"ok": True}
