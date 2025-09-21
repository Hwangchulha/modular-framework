
"""
KIS diagnostics router (final): API + built-in GUI
Mount at /_kisdiag
Endpoints:
  - GET  /_kisdiag/ping
  - POST /_kisdiag/check
  - POST /_kisdiag/account
  - POST /_kisdiag/account/match
  - GET  /_kisdiag/ui    <-- simple HTML GUI (no front-end integration required)
"""
from __future__ import annotations
from fastapi import APIRouter, Body, Response
from typing import Any, Dict, Tuple
import os, requests, time, html

try:
    from server.modules.profile.kis_test import handler as kis_check_handler  # type: ignore
except Exception:
    from modules.profile.kis_test import handler as kis_check_handler  # type: ignore

# Try import UI handler for match()
def _import_ui_handler():
    try:
        from server.modules.broker.kis.accounts import handler as ui_handler  # type: ignore
        return ui_handler
    except Exception:
        try:
            from modules.broker.kis.accounts import handler as ui_handler  # type: ignore
            return ui_handler
        except Exception:
            return None

router = APIRouter(tags=["kis-diag"])

@router.get("/ping")
def ping(): return {"ok": True}

@router.post("/check")
def check(cfg: Dict[str, Any] | None = Body(default=None)):
    return kis_check_handler(cfg, context={})

# Helpers (same as previous patch)
def _norm_env(v: str | None) -> str:
    if not v: return "prod"
    v = str(v).strip().lower()
    if v in {"prod","p","live","real"}: return "prod"
    return "vts"

def _kis_base(env: str) -> Tuple[str,str,int,str]:
    if env == "prod":
        return ("openapi.koreainvestment.com", "https", 9443, "TTTC8434R")
    else:
        return ("openapivts.koreainvestment.com", "https", 29443, "VTTC8434R")

def _to_int(x): 
    if x in (None, ""): return 0
    try: return int(str(x).replace(",",""))
    except: 
        try: return int(float(x))
        except: return 0

def _resolve(cfg):
    cfg = cfg or {}
    return {
        "appkey": cfg.get("appkey") or os.getenv("KIS_APP_KEY"),
        "appsecret": cfg.get("appsecret") or os.getenv("KIS_APP_SECRET"),
        "account_no": cfg.get("account_no") or os.getenv("KIS_ACCOUNT_NO"),
        "product_code": cfg.get("product_code") or os.getenv("KIS_ACCOUNT_PRODUCT_CODE") or "01",
        "custtype": (cfg.get("custtype") or os.getenv("KIS_CUSTTYPE") or "P").upper(),
        "env": _norm_env(cfg.get("env") or os.getenv("KIS_ENV") or "prod"),
    }

def _get_token(base, appkey, appsecret):
    url = base + "/oauth2/tokenP"
    headers = {"content-type": "application/json; charset=UTF-8"}
    body = {"grant_type": "client_credentials", "appkey": appkey, "appsecret": appsecret}
    r = requests.post(url, headers=headers, json=body, timeout=10)
    info = {"status": r.status_code}
    try: r.raise_for_status()
    except Exception:
        return ("", {"status": r.status_code, "body": r.text[:500]})
    data = r.json()
    tok = (data.get("access_token") or data.get("accessToken") or "").strip()
    info["has_token"] = bool(tok)
    return (tok, info)

def _inquire(base, token, appkey, appsecret, account_no, product_code, custtype, tr_id):
    url = base + "/uapi/domestic-stock/v1/trading/inquire-balance"
    params = {"CANO": account_no, "ACNT_PRDT_CD": product_code, "AFHR_FLPR_YN":"N","OFL_YN":"N",
              "INQR_DVSN":"02", "UNPR_DVSN":"01", "FUND_STTL_ICLD_YN":"N","FNCG_AMT_AUTO_RDPT_YN":"N",
              "PRCS_DVSN":"00","CTX_AREA_FK100":"","CTX_AREA_NK100":""}
    headers = {"authorization": f"Bearer {token}","appkey": appkey,"appsecret": appsecret,"tr_id": tr_id,"custtype": custtype}
    r = requests.get(url, headers=headers, params=params, timeout=15)
    meta = {"status": r.status_code}
    try: js = r.json()
    except Exception: js = {"_body": r.text[:500]}
    meta.update({"rt_cd": js.get("rt_cd"), "msg_cd": js.get("msg_cd"), "msg1": js.get("msg1")})
    return js, meta

def _map(account_no, js):
    out2 = js.get("output2") or {}; out1 = js.get("output1") or []
    res = {"account_no": account_no, "cash": _to_int(out2.get("dnca_tot_amt")), "eval_amt": _to_int(out2.get("tot_evlu_amt")),
           "eval_pl": _to_int(out2.get("tot_evlu_pfls_amt")), "position": []}
    for row in out1:
        res["position"].append({"symbol": str(row.get("pdno") or ""), "qty": _to_int(row.get("hldg_qty")),
                                "avg_price": _to_int(row.get("pchs_avg_pric")), "cur_price": _to_int(row.get("prpr")),
                                "pl": _to_int(row.get("evlu_pfls_amt"))})
    return res

@router.post("/account")
def account(cfg: Dict[str, Any] | None = Body(default=None)):
    cfg = _resolve(cfg); env = cfg["env"]
    host, scheme, port, tr_id = _kis_base(env); base = f"{scheme}://{host}:{port}"
    tok, tmeta = _get_token(base, cfg["appkey"], cfg["appsecret"])
    if not tok: 
        return {"ok": False, "meta": {"env": env, "host": host, "tr_id": tr_id, "tmeta": tmeta}, "hint": "토큰 실패"}
    raw, rmeta = _inquire(base, tok, cfg["appkey"], cfg["appsecret"], cfg["account_no"], cfg["product_code"], cfg["custtype"], tr_id)
    mapped = _map(cfg["account_no"], raw)
    return {"ok": True if str(rmeta.get("rt_cd")) in ("0","00","0000") else False,
            "meta": {"env": env, "host": host, "tr_id": tr_id, "http": rmeta, "token": {"has_token": True}},
            "raw": raw, "mapped": mapped}

@router.post("/account/match")
def account_match(cfg: Dict[str, Any] | None = Body(default=None)):
    left = account(cfg)
    ui_handler = _import_ui_handler()
    if ui_handler is None:
        return {"ok": False, "error": "UI handler import 실패", "left": left}
    try:
        ui = ui_handler(cfg, context={})
    except Exception as e:
        return {"ok": False, "error": f"UI handler 실행 오류: {e}", "left": left}
    # naive diff
    def D(a,b): return a if a==b else {"left":a,"ui":b}
    diff = {}
    for k in ("account_no","cash","eval_amt","eval_pl"):
        if left.get("mapped",{}).get(k) != (ui or {}).get(k): diff[k]=D(left.get("mapped",{}).get(k), (ui or {}).get(k))
    # position by symbol
    amap = {p["symbol"]:p for p in left.get("mapped",{}).get("position",[])}
    bmap = {p["symbol"]:p for p in (ui or {}).get("position",[])}
    syms = set(amap)|set(bmap); pos = {}
    for s in syms:
        if amap.get(s) != bmap.get(s): pos[s]={"left":amap.get(s),"ui":bmap.get(s)}
    if pos: diff["position"]=pos
    return {"ok": True, "left_ok": left.get("ok"), "diff": diff, "left": left, "ui_handler_result": ui}

@router.get("/ui")
def ui_page() -> Response:
    # Return a single-file HTML app that calls the endpoints above
    html_doc = """
    <!doctype html><html><head>
    <meta charset='utf-8'/>
    <title>KIS 진단</title>
    <meta name='viewport' content='width=device-width,initial-scale=1'/>
    <style>
      body{background:#0b1220;color:#cfe3ff;font-family:ui-sans-serif,system-ui,Segoe UI,Roboto,Apple SD Gothic Neo,Noto Sans KR,Apple Color Emoji;line-height:1.4;margin:0;padding:24px}
      h1{margin:0 0 6px 0} .hint{color:#7f92b8} .row{display:flex;gap:8px;flex-wrap:wrap}
      input,select{background:#141b2d;color:#cfe3ff;border:1px solid #334;border-radius:6px;padding:8px}
      button{background:#141b2d;color:#cfe3ff;border:1px solid #334;border-radius:6px;padding:8px 14px;cursor:pointer}
      pre{background:#0b1220;border:1px solid #1f2a44;border-radius:8px;padding:12px;overflow:auto;font-size:12px}
      .mt12{margin-top:12px}
    </style></head><body>
      <h1>KIS 진단 (API 내장 GUI)</h1>
      <div class='hint'>버튼만 누르면 됩니다. 실/모의는 env로 전환.</div>
      <div class='row mt12'>
        <label>env <select id='env'><option value='prod'>prod(실)</option><option value='vts'>vts(모의)</option></select></label>
        <label>account_no <input id='account_no' placeholder='CANO 8자리'></label>
        <label>product_code <input id='product_code' value='01'></label>
        <label>custtype <input id='custtype' value='P'></label>
        <label>appkey <input id='appkey' placeholder='App Key'></label>
        <label>appsecret <input id='appsecret' placeholder='App Secret'></label>
      </div>
      <div class='mt12'>
        <button id='btnCheck'>연결 점검</button>
        <button id='btnAccount'>잔고 원본 호출</button>
        <button id='btnMatch'>UI 결과와 비교</button>
        <button id='btnSave'>입력 저장</button>
      </div>
      <div class='mt12'><pre id='out'></pre></div>
      <script>
        const storeKey = 'kis.gui.cfg';
        function load(){ try{const s=localStorage.getItem(storeKey); if(!s) return; const j=JSON.parse(s);
          for(const k in j){ const el=document.getElementById(k); if(el) el.value=j[k]; }
        }catch(e){} }
        function save(){ const keys=['env','account_no','product_code','custtype','appkey','appsecret']; const j={};
          keys.forEach(k=>{ const el=document.getElementById(k); if(el) j[k]=el.value; }); localStorage.setItem(storeKey, JSON.stringify(j)); alert('저장됨'); }
        async function post(path){
          const body={env:env.value, account_no:account_no.value, product_code:product_code.value, custtype:custtype.value, appkey:appkey.value, appsecret:appsecret.value};
          const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
          let js; try{js=await res.json();}catch(e){js={_raw: await res.text()}} js._http={status:res.status};
          out.textContent = JSON.stringify(js, null, 2);
        }
        btnCheck.onclick = ()=>post('/_kisdiag/check');
        btnAccount.onclick = ()=>post('/_kisdiag/account');
        btnMatch.onclick = ()=>post('/_kisdiag/account/match');
        btnSave.onclick = save;
        load();
      </script>
    </body></html>
    """.strip()
    return Response(content=html_doc, media_type="text/html")
