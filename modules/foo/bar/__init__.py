
import uuid
from core.contract import InEnvelope, OutEnvelope

def run(env: InEnvelope, ctx) -> OutEnvelope:
    if env.action == "CREATE" and env.mode == "SINGLE":
        # 시크릿은 ctx.secrets 에 자동 주입됨(core.runner)
        _ak = ctx.secrets.get("FOO_APP_KEY")
        _as = ctx.secrets.get("FOO_APP_SECRET")
        name = env.input["name"]
        tags = env.input.get("tags", [])
        rid = str(uuid.uuid4())
        return OutEnvelope(ok=True, mode="SINGLE", data={"id": rid, "name": name, "tags": tags})
    return OutEnvelope(ok=False, mode=env.mode, error={"code":"ERR_ACTION","message":"지원 안함"})
