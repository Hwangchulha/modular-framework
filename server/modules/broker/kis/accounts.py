
"""
KIS 계좌 잔고/포지션 조회 (실계좌/모의계좌 전환 지원)
- 모듈 경로: modules.broker.kis.accounts
- import 대상: handler
- 요구: requests
- 입력(source):
    - payload 또는 context.profile.kis 에 다음 키 존재
      appkey, appsecret, account_no(CANO 8자리), product_code(ACNT_PRDT_CD, 기본 "01"),
      custtype("P" 개인 / "B" 법인, 기본 "P"),
      env("prod"|"vts"|"P"|"V"|"live"|"real"|"paper", 기본은 'prod')
- 반환 형식(프론트에서 이미 쓰던 JSON 구조 유지):
  {
    "account_no": "...",
    "cash": <int>,
    "eval_amt": <int>,
    "eval_pl": <int>,
    "position": [
      {"symbol": "005930", "qty": 1, "avg_price": 60000, "cur_price": 61000, "pl": 1000},
      ...
    ]
  }
"""
from __future__ import annotations

import os
import time
import json
from typing import Dict, Any, Tuple
import requests

__all__ = ["handler"]

def _norm_env(v: str | None) -> str:
    if not v:
        return "prod"
    v = v.strip().lower()
    if v in {"prod", "p", "live", "real"}:
        return "prod"
    return "vts"

def _kis_base(env: str) -> Tuple[str, str]:
    # host, default TR_ID for 잔고조회
    if env == "prod":
        return ("https://openapi.koreainvestment.com:9443", "TTTC8434R")
    else:
        return ("https://openapivts.koreainvestment.com:29443", "VTTC8434R")

def _to_int(x: Any) -> int:
    if x is None or x == "":
        return 0
    try:
        return int(str(x).replace(",", ""))
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return 0

def _get_from(cfg: Dict[str, Any], key: str, default=None):
    for k in (key, key.upper(), key.lower()):
        if k in cfg and cfg[k] not in (None, ""):
            return cfg[k]
    return default

def _resolve_config(payload: Dict[str, Any] | None, context: Dict[str, Any] | None) -> Dict[str, Any]:
    cfg = {}
    payload = payload or {}
    # flat in payload
    cfg.update(payload)
    # nested path: context.profile.kis
    if context:
        prof = context.get("profile") or context.get("user") or {}
        kis = prof.get("kis") if isinstance(prof, dict) else {}
        if isinstance(kis, dict):
            for k, v in kis.items():
                if v not in (None, ""):
                    cfg.setdefault(k, v)
    # env vars as fallback
    envmap = {
        "appkey": os.getenv("KIS_APP_KEY"),
        "appsecret": os.getenv("KIS_APP_SECRET"),
        "account_no": os.getenv("KIS_ACCOUNT_NO"),
        "product_code": os.getenv("KIS_ACCOUNT_PRODUCT_CODE") or "01",
        "custtype": os.getenv("KIS_CUSTTYPE") or "P",
        "env": os.getenv("KIS_ENV"),  # prod | vts
    }
    for k, v in envmap.items():
        cfg.setdefault(k, v)
    # normalize
    cfg["product_code"] = _get_from(cfg, "product_code", "01")
    cfg["custtype"] = _get_from(cfg, "custtype", "P")
    cfg["env"] = _norm_env(_get_from(cfg, "env", "prod"))
    cfg["appkey"] = _get_from(cfg, "appkey")
    cfg["appsecret"] = _get_from(cfg, "appsecret")
    cfg["account_no"] = _get_from(cfg, "account_no") or _get_from(cfg, "cano")
    missing = [k for k in ("appkey", "appsecret", "account_no") if not cfg.get(k)]
    if missing:
        raise ValueError(f"KIS config missing: {missing}. Provide via payload/context.profile.kis or env.")
    return cfg

def _get_token(base: str, appkey: str, appsecret: str, timeout: int = 10) -> str:
    url = base + "/oauth2/tokenP"
    headers = {"content-type": "application/json; charset=UTF-8"}
    body = {"grant_type": "client_credentials", "appkey": appkey, "appsecret": appsecret}
    r = requests.post(url, headers=headers, json=body, timeout=timeout)
    try:
        r.raise_for_status()
    except Exception:
        # include response text for easier debugging
        raise RuntimeError(f"KIS token error: {r.status_code} {r.text}") from None
    data = r.json()
    token = data.get("access_token") or data.get("accessToken")
    if not token:
        raise RuntimeError(f"KIS token response missing access_token: {data}")
    return token

def _inquire_balance(base: str, token: str, appkey: str, appsecret: str, account_no: str,
                     product_code: str, custtype: str, tr_id: str, timeout: int = 15) -> Dict[str, Any]:
    url = base + "/uapi/domestic-stock/v1/trading/inquire-balance"
    params = {
        "CANO": account_no,           # 계좌번호 8자리
        "ACNT_PRDT_CD": product_code, # 01 보통
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "N",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": appkey,
        "appsecret": appsecret,
        "tr_id": tr_id,
        "custtype": custtype or "P",
    }
    r = requests.get(url, headers=headers, params=params, timeout=timeout)
    try:
        r.raise_for_status()
    except Exception:
        raise RuntimeError(f"KIS inquire-balance HTTP error: {r.status_code} {r.text}") from None
    data = r.json()
    # KIS returns rt_cd "0" on success
    if str(data.get("rt_cd")) not in ("0", "00", "0000"):
        # include message codes
        raise RuntimeError(f"KIS inquire-balance returned error: {data.get('msg_cd')} {data.get('msg1')}")
    return data

def _map_response(account_no: str, data: Dict[str, Any]) -> Dict[str, Any]:
    out2 = data.get("output2") or {}
    out1 = data.get("output1") or []
    result = {
        "account_no": account_no,
        "cash": _to_int(out2.get("dnca_tot_amt")),
        "eval_amt": _to_int(out2.get("tot_evlu_amt")),
        "eval_pl": _to_int(out2.get("tot_evlu_pfls_amt")),
        "position": [],
    }
    for row in out1:
        result["position"].append({
            "symbol": str(row.get("pdno") or ""),
            "qty": _to_int(row.get("hldg_qty")),
            "avg_price": _to_int(row.get("pchs_avg_pric")),
            "cur_price": _to_int(row.get("prpr")),
            "pl": _to_int(row.get("evlu_pfls_amt")),
        })
    return result

def handler(payload: Dict[str, Any] | None = None, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Entry point expected by the framework.
    """
    cfg = _resolve_config(payload, context)
    base, tr_id = _kis_base(cfg["env"])
    token = _get_token(base, cfg["appkey"], cfg["appsecret"])
    data = _inquire_balance(base, token, cfg["appkey"], cfg["appsecret"],
                            cfg["account_no"], cfg["product_code"], cfg["custtype"], tr_id)
    return _map_response(cfg["account_no"], data)
