from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from core.registry import Registry
from core.interceptor import build_pipeline
from core.errors import FrameworkError

app = FastAPI(title="modular-framework API", version="1.0.0")

registry = Registry()
pipeline = build_pipeline(registry)

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/run")
async def run(request: Request, name: str):
    envelope = {}
    action = "?"
    try:
        envelope = await request.json()
        action = envelope.get("action", "?")
        ctx, env = pipeline.pre(dict(request.headers), envelope, name)
        out = await registry.run(name, envelope, ctx=ctx, env=env)
        pipeline.notify(name, action, ok=bool(out.get("ok", True)))
        return JSONResponse(out)
    except FrameworkError as fe:
        pipeline.notify(name, action, ok=False)
        return JSONResponse(status_code=fe.http_status, content={
            "ok": False,
            "error": {"code": fe.code, "message": fe.message, "details": fe.details}
        })
    except Exception as e:
        pipeline.notify(name, action, ok=False)
        return JSONResponse(status_code=500, content={
            "ok": False,
            "error": {"code": "ERR_INTERNAL", "message": str(e)}
        })
