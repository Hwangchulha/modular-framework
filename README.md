# modular-framework — 지침 v1.4 정렬판 (GUI First)

이 리포는 **모듈 추가만으로 확장**, **코어 불변**, **/run 엔벨로프 계약**, **GUI 우선 실행**을 강제합니다.

## 빠른 시작 (GUI First)

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run ui/dev_launcher.py
```

- Launcher에서 **Run server** 버튼을 누르면 API 서버가 올라갑니다.
- 서버는 **UI를 서빙하지 않습니다.** (분리 프로세스)
- 상태/헬스는 `/health`에서 확인, 실행 로그는 Launcher에서 확인하세요.

> 참고(Advanced): CLI로 직접 실행하려면 `uvicorn server.main:app --reload`

## API 계약 (Envelope)

**POST /run?name=<module_name>** 에 JSON 바디:

```json
{
  "action": "PING",
  "mode": "SINGLE",
  "input": { "echo": "hi" },
  "options": { "dry_run": false },
  "request_id": "optional-uuid"
}
```

응답 예시(SINGLE):

```json
{
  "ok": true,
  "mode": "SINGLE",
  "data": { "echo": "hi" },
  "metrics": {}
}
```

응답 예시(BULK):

```json
{
  "ok": false,
  "mode": "BULK",
  "results": [
    {"ok": true, "data": {"echo": "a"}, "index": 0},
    {"ok": false, "error": {"code":"ERR_SCHEMA","message":"..."},"index": 1}
  ],
  "partial_ok": true
}
```

### BULK 규칙
- 기본값: `continue_on_error=false`
- `results[]`와 `partial_ok`는 필수

## 디렉터리 구조

```
/core      # contract, registry(핫로더), interceptor, errors
/server    # API 쉘: /health, POST /run, /batch/*
/modules   # 기능 모듈(각 모듈은 manifest.yaml 필수)
/pages     # 오케스트레이션(하위 모듈 호출→JSON). 직접 DB/모듈 import 금지
/db        # 테이블/SQL 모듈(스캐폴드)
/jobs      # 스케줄러/워커(스캐폴드)
/ui        # GUI Dev Launcher(서버와 분리, 서버가 UI 서빙 금지)
/.github   # LayerGuard/CI
policy_guard.py  # 레이어 가드(금지 import/manifest 누락/서버-UI 결합 감지)
```

## 레이어 가드(강제 규칙)

- `server` → `pages|ui` import **금지**
- `core`   → `pages|modules|ui` import **금지**
- `pages`  → `db|modules` 직접 import **금지** (반드시 Registry 경유)

PR에서 위반 시 CI가 실패합니다.

## 모듈 계약 (manifest.yaml)

각 모듈은 반드시 `manifest.yaml`을 포함해야 합니다.

```yaml
name: modules.common.ping
version: 1.4.0
engine_api: "^1.4"
actions:
  PING:
    modes: [SINGLE]
    input_schema: schema/in.json
    output_schema: schema/out.json
    required_scopes: []
    secrets: []
    resources: { rps: 50, burst: 100 }
```

## 실행 방법 요약

- GUI: `streamlit run ui/dev_launcher.py` → 버튼으로 Run/Stop/Logs
- API: `POST /run?name=modules.common.ping` with Envelope
- 금지: 서버가 UI를 서빙하거나, 서버/코어가 pages/modules를 import
