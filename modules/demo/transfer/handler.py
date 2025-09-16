from typing import Dict, Any
import os, json, time, uuid

def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # -> modules
def _data_dir():
    return os.path.join(os.path.dirname(_repo_root()), "data")
def _acc_state_path():
    return os.path.join(_data_dir(), "state_accounts.json")
def _demo_acc_path():
    return os.path.join(_data_dir(), "demo_accounts.json")
def _banks_path():
    return os.path.join(_data_dir(), "banks.json")
def _txlog_path():
    return os.path.join(_data_dir(), "state_transfers.json")

def _ensure_acc_state():
    st = _acc_state_path(); dm = _demo_acc_path()
    os.makedirs(_data_dir(), exist_ok=True)
    if not os.path.exists(st):
        with open(dm,"r",encoding="utf-8") as f:
            demo = json.load(f)
        json.dump(demo, open(st,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

def _load_accounts():
    _ensure_acc_state()
    return json.load(open(_acc_state_path(),"r",encoding="utf-8"))

def _save_accounts(items):
    json.dump(items, open(_acc_state_path(),"w",encoding="utf-8"), ensure_ascii=False, indent=2)

def _find_acc(items, acc_id):
    for a in items:
        if a.get("id")==acc_id: return a
    return None

def _load_banks():
    return json.load(open(_banks_path(),"r",encoding="utf-8"))

def _log_tx(entry: dict):
    p = _txlog_path()
    hist = []
    if os.path.exists(p):
        try:
            hist = json.load(open(p,"r",encoding="utf-8"))
        except Exception:
            hist = []
    hist.append(entry)
    json.dump(hist, open(p,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

def _quote(from_acc, to_bank_code, amount) -> int:
    # Demo 룰: 동일 은행은 0원, 타행 500원
    fee = 0 if from_acc.get("bank_code")==to_bank_code else 500
    return int(fee)

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    action = envelope.get("action")
    body = envelope.get("input",{})

    if action == "VALIDATE":
        reasons = []
        fa = body.get("from_account_id")
        tb = body.get("to_bank_code")
        tan = body.get("to_account_no")
        rn = body.get("receiver_name")
        amt = int(body.get("amount",0))
        if amt <= 0: reasons.append("금액이 0 이하")
        if not fa: reasons.append("출금계좌 누락")
        if not tb: reasons.append("입금은행 누락")
        if not tan: reasons.append("입금계좌번호 누락")
        if not rn: reasons.append("받는분 누락")
        # 잔액 체크
        if fa:
            accs = _load_accounts()
            a = _find_acc(accs, fa)
            if not a: reasons.append("알 수 없는 출금계좌")
            elif amt > int(a.get("balance",0)): reasons.append("잔액 부족")
        return {"ok": True, "mode":"SINGLE", "data":{"valid": len(reasons)==0, "reasons": reasons}}

    elif action == "QUOTE":
        fa = body.get("from_account_id")
        amt = int(body.get("amount",0))
        accs = _load_accounts()
        a = _find_acc(accs, fa)
        if not a:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unknown from_account"}}
        fee = _quote(a, body.get("to_bank_code"), amt)
        return {"ok": True, "mode":"SINGLE", "data":{"fee": fee, "currency": a.get("currency","KRW")}}

    elif action == "SUBMIT":
        fa = body.get("from_account_id")
        amt = int(body.get("amount",0))
        tb = body.get("to_bank_code")
        tan = body.get("to_account_no")
        rn = body.get("receiver_name")
        memo = body.get("memo","")
        accs = _load_accounts()
        a = _find_acc(accs, fa)
        if not a:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unknown from_account"}}
        fee = _quote(a, tb, amt)
        total = amt + fee
        bal = int(a.get("balance",0))
        if amt <= 0 or total > bal:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"잔액 부족 또는 잘못된 금액"}}
        a["balance"] = bal - total
        _save_accounts(accs)
        tx = {
            "tx_id": str(uuid.uuid4()),
            "ts": time.time(),
            "from_account_id": fa,
            "to_bank_code": tb,
            "to_account_no": tan,
            "receiver_name": rn,
            "amount": amt,
            "fee": fee,
            "memo": memo,
            "status": "DONE"
        }
        _log_tx(tx)
        return {"ok": True, "mode":"SINGLE", "data":{"tx_id": tx["tx_id"], "fee": fee, "amount": amt, "new_balance": a["balance"], "status":"DONE"}}

    else:
        return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unsupported action"}}
