
from typing import Dict, Any, List
from core.errors import AuthzDenied

def check_required_scopes(manifest: Dict[str, Any], action: str, have_scopes: List[str]):
    actions = manifest.get("actions", {})
    a = actions.get(action, {})
    need = set(a.get("required_scopes", []))
    if need and not need.issubset(set(have_scopes)):
        raise AuthzDenied(f"필요 스코프: {sorted(need)}")

def required_secrets(manifest: Dict[str, Any], action: str) -> list[str]:
    a = manifest.get("actions", {}).get(action, {})
    return a.get("secrets", []) or []
