
import os, json, traceback
from typing import Dict, Any, List
from jsonschema import validate as jsonschema_validate, ValidationError as JsonSchemaError

from core.contract import InEnvelope, OutEnvelope, ResultItem, ErrorObj, Context
from core.errors import UnsupportedMode, SchemaValidationError, ModuleExecutionError, ManifestError
from core.registry import load as load_module
from core.security import check_required_scopes, required_secrets

def _read_schema(base_dir: str, rel_path: str) -> Dict[str, Any]:
    path = os.path.join(base_dir, rel_path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _ensure_mode(manifest: Dict[str, Any], action: str, mode: str):
    actions = manifest.get("actions", {})
    if action not in actions:
        raise ManifestError(f"정의되지 않은 액션: {action}")
    modes = actions[action].get("modes", ["SINGLE"])
    if mode not in modes:
        raise UnsupportedMode(f"요청 모드 {mode}는 지원 목록 {modes}에 없음")

def _validate_schema(base_dir: str, manifest: Dict[str, Any], action: str, payload: Dict[str, Any], *, in_out: str):
    a = manifest.get("actions", {}).get(action, {})
    key = "input_schema" if in_out == "in" else "output_schema"
    schema_rel = a.get(key)
    if not schema_rel:
        return  # 스키마 선언 없으면 통과
    try:
        schema = _read_schema(base_dir, schema_rel)
        jsonschema_validate(payload, schema)
    except JsonSchemaError as e:
        raise SchemaValidationError(str(e)) from e

def _load_secrets_to_ctx(ctx: Context, manifest: Dict[str, Any], action: str):
    for s in required_secrets(manifest, action):
        if s in ctx.secrets:
            continue
        v = os.getenv(s)
        if v is not None:
            ctx.secrets[s] = v

def execute(module_name: str, env: InEnvelope, ctx: Context) -> OutEnvelope:
    h = load_module(module_name)  # 핫로딩
    _ensure_mode(h.manifest, env.action, env.mode)
    check_required_scopes(h.manifest, env.action, ctx.scopes)
    _load_secrets_to_ctx(ctx, h.manifest, env.action)

    # Schema 검증(IN)
    if env.mode == "SINGLE" and env.input is not None:
        _validate_schema(h.base_dir, h.manifest, env.action, env.input, in_out="in")
    elif env.mode == "BULK":
        for i, it in enumerate(env.inputs or []):
            _validate_schema(h.base_dir, h.manifest, env.action, it, in_out="in")

    # auto_fanout
    action_def = h.manifest["actions"][env.action]
    supports_bulk = "BULK" in action_def.get("modes", ["SINGLE"])
    if env.mode == "BULK" and not supports_bulk and (env.options and env.options.auto_fanout):
        results: List[ResultItem] = []
        all_ok = True
        for i, it in enumerate(env.inputs or []):
            sub = InEnvelope(action=env.action, mode="SINGLE", input=it, request_id=env.request_id)
            try:
                out = h.module.run(sub, ctx)
                data = out.data or {}
                # Schema 검증(OUT)
                _validate_schema(h.base_dir, h.manifest, env.action, data, in_out="out")
                results.append(ResultItem(ok=True, data=data, index=i))
            except Exception as ex:
                all_ok = False
                results.append(ResultItem(ok=False, error=ErrorObj(code=getattr(ex, "code", "ERR_MODULE"),
                                                                  message=str(ex)), index=i))
        return OutEnvelope(ok=all_ok, mode="BULK", results=results, partial_ok=(not all_ok))

    # 모듈 직접 실행
    try:
        out = h.module.run(env, ctx)
        # OUT Schema
        if out.data is not None:
            _validate_schema(h.base_dir, h.manifest, env.action, out.data, in_out="out")
        return out
    except Exception as ex:
        raise ModuleExecutionError(f"{ex}") from ex
