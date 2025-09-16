from typing import Dict, Any, List
import os, json

def _paths():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # -> modules
    repo = os.path.dirname(root)
    data_dir = os.path.join(repo, "data")
    os.makedirs(data_dir, exist_ok=True)
    demo = os.path.join(data_dir, "demo_accounts.json")
    state = os.path.join(data_dir, "state_accounts.json")
    return demo, state

def _ensure_state():
    demo, state = _paths()
    if not os.path.exists(state):
        with open(demo,"r",encoding="utf-8") as f:
            demo_accounts = json.load(f)
        with open(state,"w",encoding="utf-8") as f:
            json.dump(demo_accounts, f, ensure_ascii=False, indent=2)

def _load_state() -> List[dict]:
    _ensure_state()
    _, state = _paths()
    return json.load(open(state,"r",encoding="utf-8"))

def _save_state(items: List[dict]):
    _, state = _paths()
    json.dump(items, open(state,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

def _find(accs: List[dict], acc_id: str):
    for a in accs:
        if a.get("id")==acc_id: return a
    return None

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    action = envelope.get("action")
    if action == "LIST":
        items = _load_state()
        return {"ok": True, "mode":"SINGLE", "data":{"accounts": items}}
    elif action == "BALANCE":
        acc_id = envelope.get("input",{}).get("account_id")
        items = _load_state()
        a = _find(items, acc_id)
        if not a: return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unknown account"}}
        return {"ok": True, "mode":"SINGLE", "data":{"account_id": acc_id, "balance": a.get("balance",0)}}
    elif action == "INIT":
        demo, state = _paths()
        demo_accounts = json.load(open(demo,"r",encoding="utf-8"))
        json.dump(demo_accounts, open(state,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        return {"ok": True, "mode":"SINGLE", "data":{"ok": True}}
    elif action == "DEBIT":
        acc_id = envelope.get("input",{}).get("account_id")
        amount = int(envelope.get("input",{}).get("amount",0))
        items = _load_state()
        a = _find(items, acc_id)
        if not a: return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unknown account"}}
        bal = int(a.get("balance",0))
        if amount <= 0 or amount > bal:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"insufficient balance or invalid amount"}}
        a["balance"] = bal - amount
        _save_state(items)
        return {"ok": True, "mode":"SINGLE", "data":{"account_id": acc_id, "balance": a["balance"]}}
    elif action == "CREDIT":
        # For demo we don't maintain external banks, so just echo success.
        acc_id = envelope.get("input",{}).get("account_id")
        amount = int(envelope.get("input",{}).get("amount",0))
        items = _load_state()
        a = _find(items, acc_id)
        if not a:
            # external credit: noop success for demo
            return {"ok": True, "mode":"SINGLE", "data":{"account_id": acc_id or "external", "balance": None}}
        a["balance"] = int(a.get("balance",0)) + amount
        _save_state(items)
        return {"ok": True, "mode":"SINGLE", "data":{"account_id": acc_id, "balance": a["balance"]}}
    else:
        return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unsupported action"}}
