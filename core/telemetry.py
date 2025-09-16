# 경량 텔레메트리(프로세스 내)
import time
from collections import defaultdict, deque

_METRICS = {
    "calls": defaultdict(int),           # key: f"{module}:{action}"
    "ok": defaultdict(int),
    "fail": defaultdict(int),
    "latency_ms": defaultdict(lambda: deque(maxlen=200)),  # 최근 200개
}

def record(module: str, action: str, ok: bool, ms: float):
    key = f"{module}:{action}"
    _METRICS["calls"][key] += 1
    if ok: _METRICS["ok"][key] += 1
    else:  _METRICS["fail"][key] += 1
    _METRICS["latency_ms"][key].append(ms)

def snapshot():
    out = []
    for key, calls in _METRICS["calls"].items():
        ok = _METRICS["ok"][key]
        fail = _METRICS["fail"][key]
        lat = list(_METRICS["latency_ms"][key])
        lat_sorted = sorted(lat)
        def perc(p):
            if not lat_sorted: return None
            i = int(len(lat_sorted)*p)
            i = min(max(i, 0), len(lat_sorted)-1)
            return lat_sorted[i]
        out.append({
            "key": key,
            "calls": calls,
            "ok": ok,
            "fail": fail,
            "p50_ms": perc(0.50),
            "p95_ms": perc(0.95),
            "p99_ms": perc(0.99),
            "last_ms": lat[-1] if lat else None,
        })
    return {"ts": time.time(), "series": sorted(out, key=lambda x: x["key"])}
