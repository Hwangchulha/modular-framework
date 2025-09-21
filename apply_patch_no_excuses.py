
#!/usr/bin/env python
"""
Apply "no excuses" KIS diag patch:
  - Overwrite server/kis_diag.py (adds /_kisdiag/ui)
  - Mount router at /_kisdiag in server/main.py (idempotent)
  - Copy kisdiag-launcher.js into possible web roots (ui/public, ui_web/public, public)
  - Auto-inject <script src="/kisdiag-launcher.js"> into Vite index.html and Next _app.tsx if present
"""
import re, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
print(f"[apply] repo root = {ROOT}")

def write_from(rel_src: str, rel_dst: str):
    data = (ROOT / rel_src).read_text(encoding='utf-8')
    out = ROOT / rel_dst
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(data, encoding='utf-8')
    print(f"[apply] wrote {rel_dst}")

# 1) server route
write_from('server/kis_diag.py', 'server/kis_diag.py')

# 2) ensure router mounted
main_py = ROOT / 'server' / 'main.py'
if main_py.exists():
    text = main_py.read_text(encoding='utf-8')
    changed = False
    if "from server.kis_diag import router as kis_diag_router" not in text:
        text = "from server.kis_diag import router as kis_diag_router\n" + text
        changed = True
    m = re.search(r'^(\s*)(\w+)\s*=\s*FastAPI\(', text, flags=re.M)
    app_var = m.group(2) if m else "app"
    inc_line = f"{app_var}.include_router(kis_diag_router, prefix=\"/_kisdiag\")"
    if inc_line not in text:
        text = text.rstrip() + "\n\n" + inc_line + "\n"
        changed = True
    if changed:
        main_py.write_text(text, encoding='utf-8')
        print("[apply] Patched server/main.py to include /_kisdiag router")
    else:
        print("[apply] server/main.py already had /_kisdiag router")
else:
    print("[apply] WARNING: server/main.py not found")

# 3) static launcher script(s)
for rel in ['ui/public/kisdiag-launcher.js','ui_web/public/kisdiag-launcher.js','public/kisdiag-launcher.js']:
    if (ROOT / rel).parent.exists():
        write_from(rel, rel)
    else:
        # create parent and write anyway
        write_from(rel, rel)

# 4) inject into Vite index.html (ui/index.html or ui/public/index.html or index.html at root)
def inject_script_in_html(path: Path):
    html = path.read_text(encoding='utf-8')
    if 'kisdiag-launcher.js' in html:
        print(f"[apply] {path} already has launcher")
        return
    if '</body>' in html:
        html = html.replace('</body>', '  <script src="/kisdiag-launcher.js"></script>\n</body>')
    else:
        html = html + '\n<script src="/kisdiag-launcher.js"></script>\n'
    path.write_text(html, encoding='utf-8')
    print(f"[apply] injected launcher into {path}")

candidates = [ROOT/'ui'/'index.html', ROOT/'ui'/'public'/'index.html', ROOT/'index.html']
for p in candidates:
    if p.exists():
        inject_script_in_html(p)

# 5) inject into Next.js _app.tsx under ui_web/pages/_app.tsx or pages/_app.tsx
def inject_script_in_app(path: Path):
    text = path.read_text(encoding='utf-8')
    changed = False
    if "from 'next/script'" not in text and 'from "next/script"' not in text:
        text = "import Script from 'next/script'\n" + text
        changed = True
    if "kisdiag-launcher.js" not in text:
        # naive replace of fragment close if present
        if '</>' in text:
            text = text.replace('</>', "<>\n  <Script src=\"/kisdiag-launcher.js\" strategy=\"afterInteractive\" />\n</>")
            changed = True
        else:
            # append at end
            text = text + "\nexport const KISDiagScript = () => <Script src=\"/kisdiag-launcher.js\" strategy=\"afterInteractive\" />;\n"
            changed = True
    if changed:
        path.write_text(text, encoding='utf-8')
        print(f"[apply] patched {path}")
    else:
        print(f"[apply] {path} already had launcher")

for p in [ROOT/'ui_web'/'pages'/'_app.tsx', ROOT/'pages'/'_app.tsx']:
    if p.exists():
        inject_script_in_app(p)

print("\n[apply] Done. 재시작 후:")
print("  - API GUI:   http://<host>:8000/_kisdiag/ui  (항상 됨)")
print("  - 웹 화면:   페이지 우하단 'KIS 진단' 버튼이 떠야 함 (Ctrl/Cmd+Shift+D 단축키)")
