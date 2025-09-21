from typing import Dict, Any, List
import os, json, time, requests
from core import secret_store
from ..auth.handler import _conf, _load_cached, _save_cached

def _mock(uid: str) -> Dict[str, Any]:
    return {
        "account_no": secret_store.get_user_secret(uid, "KIS_ACCOUNT_NO") or "00000000-01",
        "cash": 3_000_000,
        "eval_amount": 4_150_000,
        "pnl": 150_000,
        "positions": [
            {"symbol":"005930","qty":10,"avg_price":70000,"eval_price":72000,"pnl":20000},
            {"symbol":"000660","qty":5,"avg_price":120000,"eval_price":118000,"pnl":-10000},
        ]
    }

def _token(uid: str):
    app_key = secret_store.get_user_secret(uid, "KIS_APP_KEY")
    app_secret = secret_store.get_user_secret(uid, "KIS_APP_SECRET")
    is_paper = (secret_store.get_user_secret(uid, "KIS_IS_PAPER") or "1") == "1"
    base = "https://openapivts.koreainvestment.com:29443" if is_paper else "https://openapi.koreainvestment.com:9443"
    _, _, _, _, token_file = _conf(uid)
    tok = _load_cached(token_file)
    return tok, app_key, app_secret, base, is_paper

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    uid = (ctx or {}).get("user_id")
    if not uid:
        return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"no token"}}
    act = envelope.get("action")
    if act != "SUMMARY":
        return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unsupported action"}}

    acc = secret_store.get_user_secret(uid, "KIS_ACCOUNT_NO")
    prd = secret_store.get_user_secret(uid, "KIS_PRODUCT_CODE") or "01"
    cust = secret_store.get_user_secret(uid, "KIS_CUSTTYPE") or "P"

    tok, app_key, app_secret, base, is_paper = _token(uid)
    if not tok or not app_key or not app_secret or not acc:
        # no credentials -> mock
        return {"ok": True, "mode":"SINGLE", "data": _mock(uid)}

    # KIS balance (best-effort; fallback to mock on failure)
    try:
        # Domestic balance; TR IDs differ by env
        tr_id = "VTTC8434R" if is_paper else "TTTC8434R"
        url = base + "/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "authorization": f"Bearer {tok}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": tr_id,
            "custtype": cust
        }
        params = {
            "CANO": acc[:8],
            "ACNT_PRDT_CD": prd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_ICLD_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        r = requests.get(url, headers=headers, params=params, timeout=10)
        j = r.json()
        # Extremely simplified mapping; schema varies by account
        # If no data, fallback to mock
        if "output1" not in j and "output2" not in j:
            return {"ok": True, "mode":"SINGLE", "data": _mock(uid)}
        cash = int(j.get("output1", [{}])[0].get("dnca_tot_amt", "0")) if isinstance(j.get("output1"), list) else int(j.get("output1", {}).get("dnca_tot_amt","0"))
        positions = []
        for it in j.get("output2", []) or []:
            try:
                positions.append({
                    "symbol": it.get("pdno"),
                    "qty": int(it.get("hldg_qty","0")),
                    "avg_price": float(it.get("pchs_avg_pric","0")),
                    "eval_price": float(it.get("prpr","0")),
                    "pnl": int(float(it.get("evlu_pfls_amt","0")))
                })
            except Exception:
                continue
        eval_amount = sum(int(p["qty"]*p["eval_price"]) for p in positions) + cash
        pnl = sum(int(p["pnl"]) for p in positions)
        return {"ok": True, "mode":"SINGLE", "data":{
            "account_no": acc, "cash": cash, "eval_amount": eval_amount, "pnl": pnl, "positions": positions
        }}
    except Exception:
        return {"ok": True, "mode":"SINGLE", "data": _mock(uid)}
