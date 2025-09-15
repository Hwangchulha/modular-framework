
import os, jwt
from core.contract import InEnvelope, OutEnvelope
from db.sqlite import query_one

def run(env: InEnvelope, ctx) -> OutEnvelope:
    if env.action != "VERIFY" or env.mode != "SINGLE":
        return OutEnvelope(ok=False, mode=env.mode, error={"code":"ERR_ACTION","message":"지원 안함"})
    token = env.input.get("token")
    if not token:
        return OutEnvelope(ok=False, mode="SINGLE", error={"code":"ERR_AUTH","message":"missing token"})
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET","dev-secret"), algorithms=["HS256"])
        uid = payload.get("sub")
        row = query_one("SELECT id, email, created_at FROM auth_users WHERE id=?", (uid,))
        if not row:
            return OutEnvelope(ok=False, mode="SINGLE", error={"code":"ERR_AUTH","message":"user not found"})
        user = {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}
        return OutEnvelope(ok=True, mode="SINGLE", data={"ok": True, "user": user})
    except Exception as ex:
        return OutEnvelope(ok=False, mode="SINGLE", error={"code":"ERR_AUTH","message":str(ex)})
