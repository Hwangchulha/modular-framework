
def run(query: str, params: dict | None = None):
    # 실제 DB 연결 대신 스텁
    return {"rows": [], "meta": {"query": query, "params": params or {}}}
