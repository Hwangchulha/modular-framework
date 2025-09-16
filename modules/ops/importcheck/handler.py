from typing import Dict, Any
import importlib, traceback

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    targets = envelope.get("input",{}).get("targets",[])
    results = []
    for name in targets:
        try:
            importlib.import_module(name)
            results.append({"name": name, "ok": True, "err": None})
        except Exception:
            results.append({"name": name, "ok": False, "err": traceback.format_exc()})
    return {"ok": True, "mode":"SINGLE", "data":{"results": results}}
