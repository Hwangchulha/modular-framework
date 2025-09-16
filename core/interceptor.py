import os
import time
import uuid
from typing import Dict, Tuple, Any, Optional
from .errors import err_forbidden, err_secret, err_rate_limit

class TokenBucket:
    def __init__(self, rate_per_sec: float, burst: int):
        self.rate = rate_per_sec
        self.capacity = burst
        self.tokens = burst
        self.timestamp = time.time()

    def allow(self) -> bool:
        now = time.time()
        elapsed = now - self.timestamp
        self.timestamp = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

class CircuitBreaker:
    def __init__(self, threshold: int = 5, cooldown: float = 30.0):
        self.threshold = threshold
        self.cooldown = cooldown
        self.fail_count = 0
        self.open_until = 0.0

    def on_success(self):
        self.fail_count = 0
        self.open_until = 0.0

    def on_failure(self):
        self.fail_count += 1
        if self.fail_count >= self.threshold:
            self.open_until = time.time() + self.cooldown

    def allowed(self) -> bool:
        return time.time() >= self.open_until

class Pipeline:
    def __init__(self, registry):
        self.registry = registry
        self.buckets: Dict[str, TokenBucket] = {}
        self.circuits: Dict[str, CircuitBreaker] = {}

    def _ensure_controls(self, module_name: str, action: str):
        spec = self.registry.get_action_spec(module_name, action) or {}
        res = (spec.get("resources") or {})
        rps = float(res.get("rps", 50))
        burst = int(res.get("burst", 100))
        key = f"{module_name}:{action}"
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(rps, burst)
        if key not in self.circuits:
            self.circuits[key] = CircuitBreaker()

        if not self.circuits[key].allowed():
            raise err_rate_limit("Circuit open", {"module": module_name, "action": action})

        if not self.buckets[key].allow():
            raise err_rate_limit("Rate limit exceeded", {"module": module_name, "action": action})

    def pre(self, headers: Dict[str, str], payload: Dict[str, Any], module_name: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        req_id = headers.get("X-Request-ID") or str(uuid.uuid4())
        action = payload.get("action")
        mode = payload.get("mode", "SINGLE")
        if not action:
            from .errors import err_schema
            raise err_schema("Missing 'action' in envelope")

        required = set(self.registry.get_required_scopes(module_name, action) or [])
        provided = set((headers.get("X-Scopes") or "").split())
        if required and not required.issubset(provided):
            raise err_forbidden("Missing required scopes", {"required": list(required), "provided": list(provided)})

        secrets = (self.registry.get_required_secrets(module_name, action) or [])
        missing = [s for s in secrets if not os.environ.get(s)]
        if missing:
            raise err_secret("Missing required secrets", {"missing": missing})

        self._ensure_controls(module_name, action)

        ctx = {"request_id": req_id, "scopes": list(provided)}
        env = {"start_ts": time.time(), "module": module_name, "action": action, "mode": mode}
        return ctx, env

    def notify(self, module_name: str, action: str, ok: bool):
        key = f"{module_name}:{action}"
        c = self.circuits.get(key)
        if not c:
            return
        if ok:
            c.on_success()
        else:
            c.on_failure()

def build_pipeline(registry) -> Pipeline:
    return Pipeline(registry)
