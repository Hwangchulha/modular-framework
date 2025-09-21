Hotfix: auth DB migration + case-insensitive email lookups
- Fixes 'table users has no column named role' by auto-migrating schema.
- Adds modules.ops.dbmigrate with actions: CHECK, MIGRATE.
- Updates modules/auth/_store.py to:
  * add 'role' column if missing
  * create 'reset_tokens' table if missing
  * treat email lookups as case-insensitive (lower(email)=?)
  * provide password reset helpers (create_reset/consume_reset)
Usage:
1) Replace files by unzipping at repo root.
2) In GUI, API 시작 후 임포트 진단이 통과하면 다음 중 하나:
   - (권장) POST /run?name=modules.ops.dbmigrate with action=MIGRATE
   - 또는 회원가입/로그인 시 자동 init()로도 적용됨.
