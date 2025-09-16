import os, re, ast, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORBIDDEN = {
    "server": {"pages", "ui"},
    "core":   {"pages", "ui", "modules"},
    "pages":  {"db", "modules"},  # pages는 Registry 경유만 허용
}

def layer_of(path: Path) -> str:
    try:
        return path.relative_to(ROOT).parts[0]
    except Exception:
        return ""

def parse_imports(src: str):
    mods = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return mods
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                mods.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    return mods

def find_ui_mounts(src: str):
    bad = []
    patterns = [
        r"\.mount\(\s*[\"']\/ui[\"']",
        r"StaticFiles\s*\(",
        r"Jinja2Templates\s*\(",
    ]
    for p in patterns:
        if re.search(p, src):
            bad.append(p)
    return bad

def scan():
    report = {"forbidden_imports": [], "ui_mounts": [], "missing_manifests": [], "summary": {}}
    for py in ROOT.rglob("*.py"):
        rel = py.relative_to(ROOT).as_posix()
        lyr = layer_of(py)
        if lyr in {"server", "core", "pages"}:
            try:
                src = py.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            mods = parse_imports(src)
            fb = FORBIDDEN.get(lyr, set())
            vio = sorted(list(mods & fb))
            if vio:
                report["forbidden_imports"].append({"file": rel, "layer": lyr, "imports": vio})
            if lyr == "server":
                mounts = find_ui_mounts(src)
                if mounts:
                    report["ui_mounts"].append({"file": rel, "patterns": mounts})

    # manifest 누락 스캔
    modules_dir = ROOT / "modules"
    if modules_dir.exists():
        for mod in [p for p in modules_dir.iterdir() if p.is_dir()]:
            has_manifest = any((mod / f).exists() for f in ("manifest.yaml", "manifest.yml"))
            if not has_manifest:
                report["missing_manifests"].append(mod.relative_to(ROOT).as_posix())

    report["summary"] = {
        "forbidden_imports": len(report["forbidden_imports"]),
        "ui_mounts": len(report["ui_mounts"]),
        "missing_manifests": len(report["missing_manifests"]),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    scan()
