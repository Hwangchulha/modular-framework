
from core.contract import InEnvelope, OutEnvelope

def run(env: InEnvelope, ctx) -> OutEnvelope:
    if env.action != "PING":
        return OutEnvelope(ok=False, mode=env.mode,
                           error={"code":"ERR_ACTION","message":f"지원 안함: {env.action}"})
    if env.mode == "SINGLE":
        echo = (env.input or {}).get("echo")
        return OutEnvelope(ok=True, mode="SINGLE", data={"pong": True, "echo": echo})
    else:
        results = []
        for i, it in enumerate(env.inputs or []):
            results.append({"ok": True, "data": {"pong": True, "echo": it.get("echo")}, "index": i})
        return OutEnvelope(ok=True, mode="BULK", results=results)
