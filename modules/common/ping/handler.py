from typing import Dict, Any

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    mode = envelope.get("mode", "SINGLE")
    if mode == "SINGLE":
        echo = envelope.get("input", {}).get("echo", "")
        return {"ok": True, "mode": "SINGLE", "data": {"echo": echo}, "metrics": {}}
    elif mode == "BULK":
        opts = envelope.get("options", {}) or {}
        cont = bool(opts.get("continue_on_error", False))
        results = []
        ok_count = 0
        for idx, item in enumerate(envelope.get("inputs", [])):
            try:
                echo = item.get("echo", "")
                results.append({"ok": True, "data": {"echo": echo}, "index": idx})
                ok_count += 1
            except Exception as e:
                results.append({"ok": False, "error": {"code":"ERR_SCHEMA","message":str(e)}, "index": idx})
                if not cont:
                    break
        all_count = len(envelope.get("inputs", []))
        return {
            "ok": ok_count == all_count,
            "mode": "BULK",
            "results": results,
            "partial_ok": 0 < ok_count < all_count
        }
    else:
        return {"ok": False, "mode": mode, "error": {"code":"ERR_UNSUPPORTED_MODE","message":"unsupported"}}
