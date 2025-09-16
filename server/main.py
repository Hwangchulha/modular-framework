from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from core.registry import Registry
from core.interceptor import build_pipeline
from core.errors import FrameworkError
from core import telemetry

app = FastAPI(title="modular-framework API", version="1.1.0")

registry = Registry()
pipeline = build_pipeline(registry)

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/run")
async def run(request: Request, name: str):
    envelope = {}
    action = "?"
    start_ts = None
    try:
        envelope = await request.json()
        action = envelope.get("action", "?")
        ctx, env = pipeline.pre(dict(request.headers), envelope, name)
        start_ts = env.get("start_ts")
        out = await registry.run(name, envelope, ctx=ctx, env=env)
        ok = bool(out.get("ok", True))
        dur_ms = None
        if start_ts is not None:
            dur_ms = ( ( (import_time := __import__("time")).time() - start_ts) * 1000.0 )
        if dur_ms is not None:
            telemetry.record(name, action, ok, dur_ms)
        pipeline.notify(name, action, ok=ok)
        return JSONResponse(out)
    except FrameworkError as fe:
        if start_ts is not None:
            telemetry.record(name, action, False, ( ( (import_time := __import__("time")).time() - start_ts) * 1000.0 ))
        pipeline.notify(name, action, ok=False)
        return JSONResponse(status_code=fe.http_status, content={
            "ok": False,
            "error": {"code": fe.code, "message": fe.message, "details": fe.details}
        })
    except Exception as e:
        if start_ts is not None:
            telemetry.record(name, action, False, ( ( (import_time := __import__("time")).time() - start_ts) * 1000.0 ))
        pipeline.notify(name, action, ok=False)
        return JSONResponse(status_code=500, content={
            "ok": False,
            "error": {"code": "ERR_INTERNAL", "message": str(e)}
        })
