from typing import Dict, Any
from core import telemetry

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    snap = telemetry.snapshot()
    return {"ok": True, "mode": "SINGLE", "data": snap}
