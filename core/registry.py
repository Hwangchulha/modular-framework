
import importlib.util, sys, os, yaml
from dataclasses import dataclass
from typing import Any, Dict

_MODULE_CACHE: dict[str, "ModuleHandle"] = {}

@dataclass
class ModuleHandle:
    name: str
    module: Any
    manifest: Dict[str, Any]
    mtime: float
    base_dir: str

def _module_dir(name: str) -> str:
    # "modules.foo.bar" -> "modules/foo/bar"
    return os.path.join("modules", *name.split(".")[1:]) if name.startswith("modules.")                else os.path.join("modules", *name.split("."))

def _max_mtime(path: str) -> float:
    m = 0.0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                m = max(m, os.path.getmtime(fp))
            except FileNotFoundError:
                pass
    return m

def _load_python_module(mod_name: str, base_dir: str):
    init_py = os.path.join(base_dir, "__init__.py")
    spec = importlib.util.spec_from_file_location(mod_name, init_py)
    if spec is None or spec.loader is None:
        raise ImportError(f"모듈 로드 실패: {mod_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)  # type: ignore
    return module

def _load_manifest(base_dir: str, py_mod) -> Dict[str, Any]:
    manifest_path = os.path.join(base_dir, "manifest.yaml")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    if hasattr(py_mod, "META"):
        return py_mod.META
    raise RuntimeError("manifest.yaml 또는 META가 필요합니다.")

def load(name: str) -> ModuleHandle:
    base_dir = _module_dir(name)
    if not os.path.isdir(base_dir):
        raise RuntimeError(f"모듈 디렉터리 없음: {base_dir}")
    current_mtime = _max_mtime(base_dir)
    cached = _MODULE_CACHE.get(name)
    if cached and cached.mtime >= current_mtime:
        return cached
    py_mod = _load_python_module(name, base_dir)
    manifest = _load_manifest(base_dir, py_mod)
    handle = ModuleHandle(name=name, module=py_mod, manifest=manifest,
                          mtime=current_mtime, base_dir=base_dir)
    _MODULE_CACHE[name] = handle
    return handle
