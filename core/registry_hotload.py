import importlib
import sys
from types import ModuleType

def hot_swap(mod_name: str) -> ModuleType:
    new_mod = importlib.import_module(mod_name)
    if not hasattr(new_mod, "run"):
        raise RuntimeError(f"Module {mod_name} has no 'run' callable")
    old_mod = sys.modules.get(mod_name)
    sys.modules[mod_name] = new_mod
    return old_mod
