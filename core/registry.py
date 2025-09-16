import json
import importlib
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import yaml
from jsonschema import validate as jsonschema_validate, ValidationError

from .errors import err_schema, err_internal, err_unsupported_mode

class Registry:
    def __init__(self, modules_root: Path | None = None):
        self.modules_root = Path(modules_root or Path(__file__).resolve().parent.parent / "modules")
        self._handlers: Dict[str, Any] = {}
        self._manifests: Dict[str, Dict[str, Any]] = {}
        self._schemas: Dict[Tuple[str, str, str], Dict[str, Any]] = {}  # (module, action, in|out)

    def _module_dir(self, module_name: str) -> Path:
        parts = module_name.split(".")
        if parts[0] != "modules":
            raise ValueError("module_name must start with 'modules.'")
        return self.modules_root.joinpath(*parts[1:])

    def _load_manifest(self, module_name: str) -> Dict[str, Any]:
        if module_name in self._manifests:
            return self._manifests[module_name]
        moddir = self._module_dir(module_name)
        mani_path = moddir / "manifest.yaml"
        if not mani_path.exists():
            raise FileNotFoundError(f"manifest.yaml not found for {module_name}")
        mani = yaml.safe_load(mani_path.read_text(encoding="utf-8"))
        for k in ("name", "version", "engine_api", "actions"):
            if k not in mani:
                raise ValueError(f"manifest missing {k}")
        if mani["name"] != module_name:
            raise ValueError(f"manifest name mismatch: {mani['name']} != {module_name}")
        # engine_api 간단 체크
        if not str(mani.get("engine_api", "")).startswith("^1.4"):
            pass
        self._manifests[module_name] = mani
        # preload schemas
        actions = mani.get("actions", {})
        for act, spec in actions.items():
            in_schema_path = spec.get("input_schema")
            out_schema_path = spec.get("output_schema")
            if in_schema_path:
                self._schemas[(module_name, act, "in")] = json.loads((self._module_dir(module_name) / in_schema_path).read_text(encoding="utf-8"))
            if out_schema_path:
                self._schemas[(module_name, act, "out")] = json.loads((self._module_dir(module_name) / out_schema_path).read_text(encoding="utf-8"))
        return mani

    def get_manifest(self, module_name: str) -> Dict[str, Any]:
        return self._load_manifest(module_name)

    def get_action_spec(self, module_name: str, action: str) -> Optional[Dict[str, Any]]:
        mani = self._load_manifest(module_name)
        return mani.get("actions", {}).get(action)

    def get_required_scopes(self, module_name: str, action: str) -> Optional[list]:
        spec = self.get_action_spec(module_name, action) or {}
        return spec.get("required_scopes")

    def get_required_secrets(self, module_name: str, action: str) -> Optional[list]:
        spec = self.get_action_spec(module_name, action) or {}
        return spec.get("secrets")

    def _load_handler(self, module_name: str):
        if module_name in self._handlers:
            return self._handlers[module_name]
        handler_mod_name = f"{module_name}.handler"
        try:
            mod = importlib.import_module(handler_mod_name)
        except Exception as e:
            raise err_internal(f"Failed to import handler for {module_name}: {e}")
        if not hasattr(mod, "run") or not callable(getattr(mod, "run")):
            raise err_internal(f"{handler_mod_name} has no 'run' callable")
        self._handlers[module_name] = mod
        return mod

    async def run(self, module_name: str, envelope: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None, env: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        mani = self._load_manifest(module_name)
        handler = self._load_handler(module_name)

        action = envelope.get("action")
        mode = envelope.get("mode", "SINGLE")
        if action not in mani.get("actions", {}):
            raise err_schema(f"Unknown action '{action}' for {module_name}")
        supported_modes = mani["actions"][action].get("modes", ["SINGLE"])
        if mode not in supported_modes:
            raise err_unsupported_mode(f"Action '{action}' does not support mode '{mode}' for {module_name}")

        try:
            if mode == "SINGLE":
                sch_in = self._schemas.get((module_name, action, "in"))
                if sch_in is not None:
                    jsonschema_validate(envelope.get("input", {}), sch_in)
            elif mode == "BULK":
                sch_in = self._schemas.get((module_name, action, "in"))
                if sch_in is not None:
                    for item in envelope.get("inputs", []):
                        jsonschema_validate(item, sch_in)
            else:
                raise err_unsupported_mode("Unsupported mode")
        except ValidationError as ve:
            raise err_schema("Input schema validation failed", {"error": str(ve)})

        result = await handler.run(envelope, ctx=ctx, env=env)

        try:
            sch_out = self._schemas.get((module_name, action, "out"))
            if sch_out is not None:
                if result.get("mode") == "SINGLE" and "data" in result:
                    jsonschema_validate(result.get("data", {}), sch_out)
        except ValidationError as ve:
            raise err_schema("Output schema validation failed", {"error": str(ve)})
        return result
