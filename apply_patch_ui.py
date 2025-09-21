
#!/usr/bin/env python
"""
Apply UI KIS diag buttons:
- Adds pages/kisdiag.tsx & components/JsonCard.tsx
- Adds public/kisdiag-launcher.js
- Ensures pages/_app.tsx (or ui_web/pages/_app.tsx) includes launcher Script
- Also writes the same under ui_web/ if that app is used
"""
import os, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
print(f"[apply] repo root = {ROOT}")

def write(rel_src: str, rel_dst: str):
    data = (ROOT / rel_src).read_text(encoding='utf-8')
    dst = ROOT / rel_dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(data, encoding='utf-8')
    print(f"[apply] wrote {rel_dst}")

# Place files for root Next.js app
write('pages/kisdiag.tsx', 'pages/kisdiag.tsx')
write('components/JsonCard.tsx', 'components/JsonCard.tsx')
write('public/kisdiag-launcher.js', 'public/kisdiag-launcher.js')

# Ensure _app.tsx has the Script
app_path = ROOT / 'pages' / '_app.tsx'
if app_path.exists():
    text = app_path.read_text(encoding='utf-8')
    changed = False
    if "kisdiag-launcher.js" not in text:
        # naive inject: add Script import and tag
        if "from 'next/script'" not in text and 'from "next/script"' not in text:
            text = "import Script from 'next/script'\n" + text
        if "kisdiag-launcher.js" not in text:
            text = text.replace("</>", "<>\n  <Script src=\"/kisdiag-launcher.js\" strategy=\"afterInteractive\" />\n</>")
            changed = True
    if changed:
        app_path.write_text(text, encoding='utf-8')
        print("[apply] patched pages/_app.tsx to include launcher")
    else:
        print("[apply] pages/_app.tsx already includes launcher or could not patch safely")
else:
    write('pages/_app.tsx', 'pages/_app.tsx')

# Also install to ui_web/ if present
if (ROOT / 'ui_web').exists():
    write('ui_web/pages/kisdiag.tsx', 'ui_web/pages/kisdiag.tsx')
    write('ui_web/components/JsonCard.tsx', 'ui_web/components/JsonCard.tsx')
    write('ui_web/public/kisdiag-launcher.js', 'ui_web/public/kisdiag-launcher.js')
    uapp = ROOT / 'ui_web' / 'pages' / '_app.tsx'
    if uapp.exists():
        t = uapp.read_text(encoding='utf-8')
        changed = False
        if "kisdiag-launcher.js" not in t:
            if "from 'next/script'" not in t and 'from "next/script"' not in t:
                t = "import Script from 'next/script'\n" + t
            t = t.replace("</>", "<>\n  <Script src=\"/kisdiag-launcher.js\" strategy=\"afterInteractive\" />\n</>")
            changed = True
        if changed:
            uapp.write_text(t, encoding='utf-8')
            print("[apply] patched ui_web/pages/_app.tsx to include launcher")
        else:
            print("[apply] ui_web/pages/_app.tsx already includes launcher or could not patch safely")
    else:
        # write a minimal wrapper (does not break if existing app already has one elsewhere)
        write('pages/_app.tsx', 'ui_web/pages/_app.tsx')

print("\n[apply] Done. Next: re-run the web UI. 화면 오른쪽 아래 'KIS 진단' 버튼을 눌러 주세요.")
