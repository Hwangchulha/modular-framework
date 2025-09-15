
from core.contract import Context, InEnvelope
from core.runner import execute

def run(params, ctx: Context):
    # params 예시:
    # { "op": "render" | "signup" | "login", "input": {...} }
    op = (params or {}).get("op", "render")
    if op == "render":
        return {
            "view": "auth",
            "forms": {
                "signup": {"fields": [{"name":"email","type":"email"},{"name":"password","type":"password"}]},
                "login": {"fields": [{"name":"email","type":"email"},{"name":"password","type":"password"}]}
            }
        }
    if op == "signup":
        # modules.auth.users REGISTER
        data = (params or {}).get("input", {})
        out = execute("modules.auth.users",
                      InEnvelope(action="REGISTER", mode="SINGLE", input={"email": data.get("email"), "password": data.get("password")}),
                      ctx)
        return {"op":"signup", "result": out.model_dump()}
    if op == "login":
        data = (params or {}).get("input", {})
        out = execute("modules.auth.login",
                      InEnvelope(action="LOGIN", mode="SINGLE", input={"email": data.get("email"), "password": data.get("password")}),
                      ctx)
        return {"op":"login", "result": out.model_dump()}
    return {"ok": False, "error": {"code":"ERR_OP","message": f"unknown op: {op}"}}
