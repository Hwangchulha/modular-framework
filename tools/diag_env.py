#!/usr/bin/env python
"""
CLI: quick diagnostics for cryptography/requests and module import
Usage:
    python tools/diag_env.py
    python tools/diag_env.py modules.broker.kis.accounts
"""
import sys, importlib, traceback, platform, json

def status():
    out = {
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
    }
    for mod in ["cryptography", "jwt", "requests"]:
        try:
            m = importlib.import_module(mod)
            out[mod] = {"present": True, "version": getattr(m, "__version__", None)}
        except Exception:
            out[mod] = {"present": False, "traceback": traceback.format_exc()}
    return out

def try_import(dotted_path: str):
    try:
        importlib.import_module(dotted_path)
        return {"imported": True, "module": dotted_path}
    except Exception as e:
        return {"imported": False, "module": dotted_path, "error": str(e), "traceback": traceback.format_exc()}

if __name__ == "__main__":
    print(json.dumps(status(), ensure_ascii=False, indent=2))
    if len(sys.argv) > 1:
        print(json.dumps(try_import(sys.argv[1]), ensure_ascii=False, indent=2))
