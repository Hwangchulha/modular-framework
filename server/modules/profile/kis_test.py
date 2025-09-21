
"""
modules.profile.kis_test
------------------------
Connection diagnostics for KIS (한국투자증권) OpenAPI.
Designed to be called via the project's dynamic module loader (handler(payload, context)).
- Does NOT persist or echo full secrets. Keys are redacted in results.
- Tries: config check -> DNS/TCP -> token -> (optional) balance TR handshake
"""
from __future__ import annotations
import os, socket, json, time, traceback
from typing import Any, Dict, Tuple
import requests

__all__ = ["handler"]

SAFE_MASK = "****"

def _mask(s: str | None) -> str | None:
    if not s:
        return s
    if len(s) <= 8:
        return SAFE_MASK
    return s[:4] + SAFE_MASK + s[-2:]

def _norm_env(v: str | None) -> str:
    if not v:
        return "prod"
    v = str(v).strip().lower()
    if v in {"prod", "p", "live", "real"}:
        return "prod"
    return "vts"

def _kis_base(env: str) -> Tuple[str, str, int]:
    if env == "prod":
        return ("openapi.koreainvestment.com", "https", 9443)
    else:
        return ("openapivts.koreainvestment.com", "https", 29443)

def _resolve_config(payload: Dict[str, Any] | None, context: Dict[str, Any] | None) -> Dict[str, Any]:
    payload = payload or {}
    cfg = {}
    cfg.update(payload)

    # From context.profile.kis if available
    if context and isinstance(context, dict):
        prof = context.get("profile") or context.get("user") or {}
        kis = prof.get("kis") if isinstance(prof, dict) else {}
        if isinstance(kis, dict):
            for k, v in kis.items():
                if v not in (None, ""):
                    cfg.setdefault(k, v)

    # From environment
    envmap = {
        "appkey": os.getenv("KIS_APP_KEY"),
        "appsecret": os.getenv("KIS_APP_SECRET"),
        "account_no": os.getenv("KIS_ACCOUNT_NO"),
        "product_code": os.getenv("KIS_ACCOUNT_PRODUCT_CODE") or "01",
        "custtype": os.getenv("KIS_CUSTTYPE") or "P",
        "env": os.getenv("KIS_ENV"),  # prod | vts
        "mock": os.getenv("KIS_MOCK"), # truthy => skip network calls
    }
    for k, v in envmap.items():
        cfg.setdefault(k, v)

    # Normalize
    cfg["product_code"] = str(cfg.get("product_code") or "01")
    cfg["custtype"] = (cfg.get("custtype") or "P").upper()
    cfg["env"] = _norm_env(cfg.get("env"))
    cfg["mock"] = str(cfg.get("mock") or "").lower() in ("1","true","yes","y")
    return cfg

def _step(name: str, fn):
    t0 = time.time()
    ok = False
    meta: Dict[str, Any] = {}
    try:
        meta = fn()
        ok = True
    except Exception as e:
        meta = {"error": str(e), "traceback": traceback.format_exc()}
    finally:
        meta["elapsed_ms"] = int((time.time() - t0) * 1000)
        meta["ok"] = ok
    return {"name": name, **meta}

def handler(payload: Dict[str, Any] | None = None, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = _resolve_config(payload, context)
    env = cfg["env"]
    host, scheme, port = _kis_base(env)
    base = f"{scheme}://{host}:{port}"

    result = {
        "env": env,
        "base": base,
        "input": {
            "appkey": _mask(cfg.get("appkey")),
            "appsecret": _mask(cfg.get("appsecret")),
            "account_no": cfg.get("account_no"),
            "product_code": cfg.get("product_code"),
            "custtype": cfg.get("custtype"),
        },
        "steps": [],
        "summary": [],
    }

    # Step 0: config check
    def s0():
        missing = [k for k in ("appkey","appsecret","account_no") if not cfg.get(k)]
        return {"missing": missing}
    s0r = _step("config", s0)
    result["steps"].append(s0r)

    if s0r.get("missing"):
        result["summary"].append("필수 키 누락: " + ", ".join(s0r["missing"]))

    # If mock requested, stop here
    if cfg["mock"]:
        result["summary"].append("mock 모드이므로 네트워크 테스트를 건너뜀")
        return result

    # Step 1: DNS
    def s1():
        ai = socket.getaddrinfo(host, port)
        return {"addresses": list({f"{a[4][0]}:{a[4][1]}" for a in ai})}
    result["steps"].append(_step("dns", s1))

    # Step 2: TCP
    def s2():
        with socket.create_connection((host, port), timeout=5) as s:
            return {"peer": f"{s.getpeername()[0]}:{s.getpeername()[1]}"}
    result["steps"].append(_step("tcp", s2))

    # Step 3: token
    def s3():
        url = base + "/oauth2/tokenP"
        headers = {"content-type": "application/json; charset=UTF-8"}
        body = {"grant_type": "client_credentials", "appkey": cfg["appkey"], "appsecret": cfg["appsecret"]}
        r = requests.post(url, headers=headers, json=body, timeout=10)
        try:
            r.raise_for_status()
        except Exception:
            return {"status": r.status_code, "body": r.text[:500]}
        data = r.json()
        token = data.get("access_token") or data.get("accessToken")
        return {"status": r.status_code, "has_token": bool(token)}
    result["steps"].append(_step("token", s3))

    # Step 4: lightweight inquire-balance (header only) to validate TR/headers
    def s4():
        url = base + "/uapi/domestic-stock/v1/trading/inquire-balance"
        params = {
            "CANO": cfg.get("account_no") or "",
            "ACNT_PRDT_CD": cfg.get("product_code"),
            "AFHR_FLPR_YN": "N", "OFL_YN": "N", "INQR_DVSN": "02",
            "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": "",
        }
        # get fresh token
        url_token = base + "/oauth2/tokenP"
        headers0 = {"content-type": "application/json; charset=UTF-8"}
        body0 = {"grant_type": "client_credentials", "appkey": cfg["appkey"], "appsecret": cfg["appsecret"]}
        rt = requests.post(url_token, headers=headers0, json=body0, timeout=10)
        rt.raise_for_status()
        token = (rt.json().get("access_token") or rt.json().get("accessToken") or "").strip()
        tr_id = "TTTC8434R" if env == "prod" else "VTTC8434R"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": cfg["appkey"],
            "appsecret": cfg["appsecret"],
            "tr_id": tr_id,
            "custtype": cfg["custtype"],
        }
        r = requests.get(url, headers=headers, params=params, timeout=10)
        # We accept 200 with KIS payload or 4xx with msg codes; both prove routing works
        code = r.status_code
        body = {}
        try:
            body = r.json()
        except Exception:
            pass
        return {"status": code, "rt_cd": body.get("rt_cd"), "msg_cd": body.get("msg_cd"), "msg1": body.get("msg1")}
    result["steps"].append(_step("balance_probe", s4))

    # Verdict
    bad = [s for s in result["steps"] if not s.get("ok")]
    if not bad:
        result["summary"].append("네트워크/토큰/TR 호출까지 정상. 키/계좌/권한이 유효로 보임.")
    else:
        result["summary"].append("실패 단계: " + ", ".join(s["name"] for s in bad))
        for s in bad:
            if s["name"] == "token":
                result["summary"].append("토큰 실패: AppKey/Secret, 허용 IP, 앱 권한 확인 필요.")
            if s["name"] == "balance_probe":
                result["summary"].append("잔고 조회 실패: CANO(8자리), 상품코드(01), TR_ID/환경(prod/vts) 확인.")
    return result
