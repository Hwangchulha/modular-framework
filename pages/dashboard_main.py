# pages orchestrator example
from core.registry import Registry

registry = Registry()

async def RUN(input: dict):
    a = await registry.run("modules.common.ping", {"action":"PING","mode":"SINGLE","input":{"echo":"hi"}})
    return {"summary": {"ping": a.get("data")}}
