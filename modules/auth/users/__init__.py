
import uuid, datetime, sqlite3
from core.contract import InEnvelope, OutEnvelope
from db.sqlite import execute, query_one, init_basic_schema
import bcrypt

def _now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def run(env: InEnvelope, ctx) -> OutEnvelope:
    # 테이블이 없다면 보장
    init_basic_schema()

    if env.action == "REGISTER" and env.mode == "SINGLE":
        email = env.input["email"].strip().lower()
        password = env.input["password"]
        # hash
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        uid = str(uuid.uuid4())
        ts = _now_iso()
        try:
            execute("INSERT INTO auth_users(id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (uid, email, pw_hash, ts))
        except sqlite3.IntegrityError:
            return OutEnvelope(ok=False, mode="SINGLE", error={"code":"ERR_CONFLICT","message":"email already registered"})
        return OutEnvelope(ok=True, mode="SINGLE", data={"id": uid, "email": email, "created_at": ts})

    if env.action == "GET" and env.mode == "SINGLE":
        id_ = (env.input or {}).get("id")
        email = (env.input or {}).get("email")
        row = None
        if id_:
            row = query_one("SELECT id, email, created_at FROM auth_users WHERE id=?", (id_,))
        elif email:
            row = query_one("SELECT id, email, created_at FROM auth_users WHERE email=?", (email.strip().lower(),))
        if not row:
            return OutEnvelope(ok=True, mode="SINGLE", data={"found": False})
        user = {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}
        return OutEnvelope(ok=True, mode="SINGLE", data={"found": True, "user": user})

    return OutEnvelope(ok=False, mode=env.mode, error={"code":"ERR_ACTION","message":f"지원 안함: {env.action}"})
