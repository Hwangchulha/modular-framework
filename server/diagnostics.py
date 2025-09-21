
"""
Diagnostics endpoints for Modular Framework
- GET /_diag/ping
- GET /_diag/env
- GET /_diag/import/{dotted_path}
- GET /_diag/crypto
- GET /_diag/requests
"""
from fastapi import APIRouter, Response
import json, sys, platform, importlib, traceback, os

router = APIRouter(tags=["diag"])

def _module_status(name: str):
    try:
        spec = importlib.util.find_spec(name)  # type: ignore[attr-defined]
        present = spec is not None
    except Exception:
        present = False
    version = None
    if present:
        try:
            m = importlib.import_module(name)
            version = getattr(m, "__version__", None)
        except Exception:
            version = None
    return {"present": present, "version": version}

@router.get("/ping")
def ping():
    return {"ok": True}

@router.get("/env")
def env():
    return {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "sys_path": sys.path,
        "cryptography": _module_status("cryptography"),
        "pyjwt": _module_status("jwt"),
        "requests": _module_status("requests"),
    }

@router.get("/crypto")
def crypto():
    try:
        m = importlib.import_module("cryptography")
        return {"present": True, "version": getattr(m, "__version__", None)}
    except Exception:
        tb = traceback.format_exc()
        return Response(json.dumps({"present": False, "traceback": tb}, ensure_ascii=False),
                        media_type="application/json", status_code=500)

@router.get("/requests")
def requests_status():
    try:
        m = importlib.import_module("requests")
        return {"present": True, "version": getattr(m, "__version__", None)}
    except Exception:
        tb = traceback.format_exc()
        return Response(json.dumps({"present": False, "traceback": tb}, ensure_ascii=False),
                        media_type="application/json", status_code=500)

@router.get("/import/{dotted_path}")
def try_import(dotted_path: str):
    try:
        importlib.import_module(dotted_path)
        return {"imported": True, "module": dotted_path}
    except Exception as e:
        tb = traceback.format_exc()
        payload = {
            "imported": False,
            "module": dotted_path,
            "error": str(e),
            "traceback": tb,
            "sys_path": sys.path,
            "hint": "Most common cause: running under a Python that lacks the dependency. Check /_diag/env.executable.",
        }
        return Response(json.dumps(payload, ensure_ascii=False), media_type="application/json", status_code=500)
