
#!/usr/bin/env python
"""
Apply account debug extension:
- Overwrite server/kis_diag.py with extended endpoints
- Ensure router mounted at /_kisdiag
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
print(f"[apply] repo root = {REPO_ROOT}")

# write kis_diag.py
src = REPO_ROOT / "server/kis_diag.py"
data = src.read_text(encoding="utf-8")
dst = REPO_ROOT / "server/kis_diag.py"
dst.write_text(data, encoding="utf-8")
print("[apply] updated server/kis_diag.py")

# ensure include in server/main.py
main_py = REPO_ROOT / "server" / "main.py"
if main_py.exists():
    text = main_py.read_text(encoding="utf-8")
    changed = False
    if "from server.kis_diag import router as kis_diag_router" not in text:
        text = "from server.kis_diag import router as kis_diag_router\n" + text
        changed = True
    m = re.search(r"^(\s*)(\w+)\s*=\s*FastAPI\(", text, flags=re.M)
    app_var = m.group(2) if m else "app"
    inc = f"{app_var}.include_router(kis_diag_router, prefix=\"/_kisdiag\")"
    if inc not in text:
        text = text.rstrip() + "\n\n" + inc + "\n"
        changed = True
    if changed:
        main_py.write_text(text, encoding="utf-8")
        print("[apply] Patched server/main.py")
    else:
        print("[apply] server/main.py already set.")
else:
    print("[apply] WARNING: server/main.py not found. Mount router manually.")
