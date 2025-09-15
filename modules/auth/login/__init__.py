
import os, datetime
from core.contract import InEnvelope, OutEnvelope
from db.sqlite import query_one
import bcrypt, jwt

def _now_utc():
    return datetime.datetime.utcnow()

def _exp(hours: int) -> datetime.datetime:
    return _now_utc() + datetime.timedelta(hours=hours)

def run(env: InEnvelope, ctx) -> OutEnvelope:
    if env.action != "LOGIN" or env.mode != "SINGLE":
        return OutEnvelope(ok=False, mode=env.mode, error={"code":"ERR_ACTION","message":"지원 안함"})
    email = env.input["email"].strip().lower()
    password = env.input["password"]

    row = query_one("SELECT id, email, password_hash, created_at FROM auth_users WHERE email=?", (email,))
    if not row:
        return OutEnvelope(ok=False, mode="SINGLE", error={"code":"ERR_AUTH","message":"invalid credentials"})
    if not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        return OutEnvelope(ok=False, mode="SINGLE", error={"code":"ERR_AUTH","message":"invalid credentials"})

    secret = os.getenv("JWT_SECRET", "dev-secret")
    hours = int(os.getenv("JWT_EXPIRES_HOURS", "168"))  # default 7d
    payload = {"sub": row["id"], "email": row["email"], "iat": int(_now_utc().timestamp()), "exp": int(_exp(hours).timestamp())}
    token = jwt.encode(payload, secret, algorithm="HS256")
    user = {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}
    return OutEnvelope(ok=True, mode="SINGLE", data={"ok": True, "token": token, "user": user})
