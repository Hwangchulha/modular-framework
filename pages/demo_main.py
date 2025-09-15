
from core.contract import Context, InEnvelope
from core.runner import execute

# action="RUN" 고정: UI가 바로 그리는 JSON을 리턴
def run(_env, _ctx):
    # 예시: ping -> bar.create 순으로 호출
    ctx = Context(scopes=["foo:create"])  # 실제 서비스에선 요청 컨텍스트를 주입
    pong = execute("modules.common.ping",
                   InEnvelope(action="PING", mode="SINGLE", input={"echo":"hi"}),
                   ctx)
    created = execute("modules.foo.bar",
                      InEnvelope(action="CREATE", mode="SINGLE", input={"name":"alpha","tags":["x"]}),
                      ctx)
    return {
        "widgets": [
            {"type":"kpi", "title":"health", "value": pong.data},
            {"type":"card", "title":"new foo", "value": created.data}
        ]
    }
