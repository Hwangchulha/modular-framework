import os, time, jwt, uuid

def _secret():
    # 환경변수 JWT_SECRET이 없으면 런처(start.py)가 data/.jwt_secret을 생성/주입함
    sec = os.environ.get("JWT_SECRET")
    if not sec:
        raise RuntimeError("JWT_SECRET is not set")
    return sec

def issue_access(user_id: str, scopes: list[str] | None = None, minutes: int = 30) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "scopes": scopes or [],
        "iat": now,
        "exp": now + minutes*60,
        "jti": str(uuid.uuid4())
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")

def verify_access(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=["HS256"])
