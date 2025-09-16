from core.registry import Registry
registry = Registry()

async def RUN(input: dict):
    snap = await registry.run("modules.ops.snapshot", {"action":"SNAPSHOT","mode":"SINGLE","input":{}})
    return {"ops": snap.get("data")}
