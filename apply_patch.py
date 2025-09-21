
#!/usr/bin/env python
"""
Apply hotfix to the local 'modular-framework' repo.
- Ensures requirements.txt contains cryptography/PyJWT/requests
- Injects diagnostics router into server/main.py (/_diag)
- Drops server/diagnostics.py and tools/diag_env.py into place

Run:  python apply_patch.py
"""
import os, re, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
print(f"[apply] repo root = {REPO_ROOT}")

def write_file(rel_path: str, content: str, mode: str = "w"):
    path = REPO_ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8") as f:
        f.write(content)
    print(f"[apply] wrote {rel_path}")

# copy staged files (placed by unzip)
def copy_from_staged(src_rel: str, dst_rel: str):
    src = REPO_ROOT / src_rel
    data = src.read_text(encoding="utf-8")
    write_file(dst_rel, data)

def normalize_requirements():
    req = REPO_ROOT / "requirements.txt"
    wanted = set([
        "fastapi>=0.110",
        "uvicorn>=0.23",
        "pydantic>=2.5",
        "jsonschema>=4.19",
        "PyYAML>=6.0",
        "PyJWT>=2.8",
        "cryptography>=42",
        "requests>=2.32",
    ])
    if not req.exists():
        print("[apply] requirements.txt not found; creating baseline.")
        req.write_text("\n".join(sorted(wanted, key=str.lower)) + "\n", encoding="utf-8")
        return

    text = req.read_text(encoding="utf-8")
    tokens = re.split(r"[\s,]+", text.strip())
    tokens = [t for t in tokens if t and not t.startswith("#")]
    existing_names = {t.split(">")[0].lower() for t in tokens}
    for w in wanted:
        n = w.split(">")[0].lower()
        if n not in existing_names:
            tokens.append(w)
    normalized = "\n".join(sorted(set(tokens), key=str.lower)) + "\n"
    req.write_text(normalized, encoding="utf-8")
    print("[apply] requirements.txt normalized and ensured dependencies.")

def inject_diag_router():
    main_py = REPO_ROOT / "server" / "main.py"
    if not main_py.exists():
        print("[apply] WARNING: server/main.py not found. Skipping router injection.")
        return
    text = main_py.read_text(encoding="utf-8")
    changed = False

    if "from server.diagnostics import router as diag_router" not in text:
        text = 'from server.diagnostics import router as diag_router\n' + text
        changed = True

    import re
    m = re.search(r"^(\s*)(\w+)\s*=\s*FastAPI\(", text, flags=re.M)
    app_var = m.group(2) if m else "app"

    include_line = f"{app_var}.include_router(diag_router, prefix=\"/_diag\")"
    if include_line not in text:
        text = text.rstrip() + "\n\n" + include_line + "\n"
        changed = True

    if changed:
        backup = main_py.with_suffix(".py.bak")
        backup.write_text(main_py.read_text(encoding="utf-8"), encoding="utf-8")
        main_py.write_text(text, encoding="utf-8")
        print(f"[apply] Patched server/main.py (backup: {backup.name}).")
    else:
        print("[apply] server/main.py already configured.")

# Copy staged files into repo
copy_from_staged("server/diagnostics.py", "server/diagnostics.py")
copy_from_staged("tools/diag_env.py", "tools/diag_env.py")
normalize_requirements()
inject_diag_router()

print("\n[apply] Done. Next:")
print("  pip install -r requirements.txt")
print("  restart API, then GET /_diag/env and /_diag/import/modules.broker.kis.accounts")
