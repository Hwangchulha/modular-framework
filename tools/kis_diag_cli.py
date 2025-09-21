
#!/usr/bin/env python
"""
CLI to run KIS connection diagnostics without HTTP.
Usage:
    python tools/kis_diag_cli.py --appkey XXX --appsecret YYY --account-no 12345678 --env prod
Or rely on env vars:
    KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NO, KIS_ENV=prod|vts
"""
import argparse, json, os, sys
try:
    from server.modules.profile.kis_test import handler as kis_diag_handler  # type: ignore
except Exception:
    from modules.profile.kis_test import handler as kis_diag_handler  # type: ignore

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--appkey")
    p.add_argument("--appsecret")
    p.add_argument("--account-no")
    p.add_argument("--product-code", default="01")
    p.add_argument("--custtype", default="P")
    p.add_argument("--env", default=os.getenv("KIS_ENV", "prod"))
    args = p.parse_args()

    payload = {
        "appkey": args.appkey or os.getenv("KIS_APP_KEY"),
        "appsecret": args.appsecret or os.getenv("KIS_APP_SECRET"),
        "account_no": args.account_no or os.getenv("KIS_ACCOUNT_NO"),
        "product_code": args.product_code,
        "custtype": args.custtype,
        "env": args.env,
    }
    res = kis_diag_handler(payload, context={})
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
