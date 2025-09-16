from typing import Dict, Any
import json, os

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    mode = envelope.get("mode","SINGLE")
    if mode != "SINGLE":
        return {"ok": False, "mode": mode, "error": {"code": "ERR_UNSUPPORTED_MODE","message": "Only SINGLE supported"}}
    # banks.json
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # -> modules/
    data_path = os.path.join(os.path.dirname(root), "data", "banks.json")
    with open(data_path, "r", encoding="utf-8") as f:
        banks = json.load(f)
    return {"ok": True, "mode": "SINGLE", "data": {"banks": banks}}
