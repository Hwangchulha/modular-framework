
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, HTMLResponse
from core.contract import InEnvelope, Context
from core.runner import execute
from core.errors import FrameworkError
from db.sqlite import init_basic_schema
import importlib.util, os

app = FastAPI(title="Module Framework API", version="1.2.0")

@app.on_event("startup")
async def _startup():
    # 자동 테이블 생성
    init_basic_schema()

def _ctx_from_request(req: Request) -> Context:
    scopes_hdr = req.headers.get("X-Scopes", "")
    scopes = [s.strip() for s in scopes_hdr.split(",") if s.strip()]
    rid = req.headers.get("X-Request-Id")
    return Context(request_id=rid, scopes=scopes, vars={})

@app.post("/run")
async def run_endpoint(request: Request, name: str = Query(..., description="모듈 이름(e.g., modules.common.ping)")):
    payload = await request.json()
    env = InEnvelope(**payload)
    ctx = _ctx_from_request(request)
    try:
        out = execute(name, env, ctx)
        return JSONResponse(out.model_dump())
    except FrameworkError as fe:
        return JSONResponse(status_code=400, content={"ok": False, "mode": env.mode,
                                                      "error": {"code": fe.code, "message": str(fe), "details": fe.details}})
    except Exception as ex:
        return JSONResponse(status_code=500, content={"ok": False, "mode": env.mode,
                                                      "error": {"code": "ERR_INTERNAL", "message": str(ex)}})

@app.post("/batch/run")
async def batch_endpoint(request: Request, name: str):
    payload = await request.json()
    payload["mode"] = "BULK"
    env = InEnvelope(**payload)
    ctx = _ctx_from_request(request)
    out = execute(name, env, ctx)
    return JSONResponse(out.model_dump())

def _load_page_module(name: str):
    # name='auth' -> pages/auth_main.py
    base = os.path.join("pages", f"{name}_main.py")
    if not os.path.exists(base):
        raise FileNotFoundError(f"page not found: {base}")
    spec = importlib.util.spec_from_file_location(f"pages.{name}_main", base)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod

@app.post("/page/run")
async def page_run(request: Request, name: str = Query(..., description="페이지 이름(e.g., auth)")):
    payload = await request.json()
    page = _load_page_module(name)
    ctx = _ctx_from_request(request)
    try:
        out_json = page.run(payload, ctx)
        return JSONResponse(out_json)
    except Exception as ex:
        return JSONResponse(status_code=500, content={"ok": False, "error": {"code": "ERR_PAGE", "message": str(ex)}})

@app.get("/ui/auth", response_class=HTMLResponse)
async def ui_auth():
    # 정적 파일 없이 바로 HTML 반환 (간단/무의존)
    html_path = os.path.join("ui", "auth.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    # 폴백: 내장 HTML
    return HTMLResponse("""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>Auth</title>
    <style>
      :root { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, 'Noto Sans KR', sans-serif; }
      body { margin: 0; background: #0b0c0f; color: #e6e7ea; }
      .wrap { max-width: 640px; margin: 48px auto; padding: 24px; background: #12141a; border: 1px solid #23262d; border-radius: 12px; }
      h1 { margin: 0 0 16px; font-size: 20px; }
      .row { display: flex; gap: 16px; }
      .card { flex: 1; padding: 16px; border: 1px solid #23262d; border-radius: 12px; background:#0f1116; }
      label { display:block; font-size: 12px; color:#aab1bb; margin: 8px 0 4px; }
      input { width:100%; padding:10px 12px; border-radius: 8px; border:1px solid #2c313a; background:#12141a; color:#e6e7ea; }
      button { margin-top:12px; padding:10px 14px; border-radius: 8px; border:1px solid #2f6feb; background:#3b82f6; color:white; cursor:pointer; }
      button:disabled { opacity:.6; cursor:not-allowed }
      pre { background:#0b0c0f; padding:12px; border-radius:8px; overflow:auto; border:1px solid #23262d; }
      .kpi { margin-bottom: 16px; display:flex; align-items:center; gap:8px; }
      .dot { width:10px; height:10px; border-radius:50%; }
      .ok { background:#22c55e; } .bad { background:#ef4444; }
      .msg { font-size:12px; color:#aab1bb; }
    </style>
    </head>
    <body>
      <div class="wrap">
        <div class="kpi"><div id="dot" class="dot bad"></div><div id="health" class="msg">백엔드 연결 중...</div></div>
        <h1>로그인 / 회원가입</h1>
        <div class="row">
          <div class="card">
            <h3>회원가입</h3>
            <label>이메일</label>
            <input id="su_email" type="email" placeholder="you@example.com">
            <label>비밀번호</label>
            <input id="su_pw" type="password" placeholder="******">
            <button id="btn_signup">가입</button>
            <pre id="out_signup"></pre>
          </div>
          <div class="card">
            <h3>로그인</h3>
            <label>이메일</label>
            <input id="li_email" type="email" placeholder="you@example.com">
            <label>비밀번호</label>
            <input id="li_pw" type="password" placeholder="******">
            <button id="btn_login">로그인</button>
            <pre id="out_login"></pre>
          </div>
        </div>
      </div>
      <script>
        const j = x => JSON.stringify(x, null, 2);
        async function ping() {
          try {
            const r = await fetch('/health');
            const ok = r.ok;
            document.getElementById('dot').className = 'dot ' + (ok ? 'ok' : 'bad');
            document.getElementById('health').textContent = ok ? '백엔드 연결 OK' : '백엔드 연결 실패';
          } catch(e) {
            document.getElementById('dot').className = 'dot bad';
            document.getElementById('health').textContent = '백엔드 연결 실패';
          }
        }
        async function signup() {
          const email = document.getElementById('su_email').value.trim();
          const password = document.getElementById('su_pw').value;
          setBusy('btn_signup', true);
          try {
            const r = await fetch('/run?name=modules.auth.users', {
              method:'POST',
              headers:{'Content-Type':'application/json'},
              body: JSON.stringify({action:'REGISTER', mode:'SINGLE', input:{email, password}})
            });
            const data = await r.json();
            document.getElementById('out_signup').textContent = j(data);
          } catch(e) {
            document.getElementById('out_signup').textContent = '요청 실패: ' + e;
          } finally { setBusy('btn_signup', false); }
        }
        async function login() {
          const email = document.getElementById('li_email').value.trim();
          const password = document.getElementById('li_pw').value;
          setBusy('btn_login', true);
          try {
            const r = await fetch('/run?name=modules.auth.login', {
              method:'POST',
              headers:{'Content-Type':'application/json'},
              body: JSON.stringify({action:'LOGIN', mode:'SINGLE', input:{email, password}})
            });
            const data = await r.json();
            if (data?.data?.token) {
              localStorage.setItem('jwt', data.data.token);
            }
            document.getElementById('out_login').textContent = j(data);
          } catch(e) {
            document.getElementById('out_login').textContent = '요청 실패: ' + e;
          } finally { setBusy('btn_login', false); }
        }
        function setBusy(id, on){ const b=document.getElementById(id); b.disabled=on; b.textContent = on ? '처리 중...' : (id==='btn_signup'?'가입':'로그인'); }
        document.getElementById('btn_signup').addEventListener('click', signup);
        document.getElementById('btn_login').addEventListener('click', login);
        ping(); setInterval(ping, 3000);
      </script>
    </body>
    </html>""")

@app.get("/health")
async def health():
    return {"ok": True}
