
# 모듈형 시스템 프레임워크 — 스캐폴드

## 빠른 시작
```bash
# 1) 의존성 설치
pip install -r requirements.txt

# 2) 개발 서버
uvicorn server.main:app --reload

# 3) 헬스체크
curl http://localhost:8000/health

# 4) PING (SINGLE)
curl -X POST "http://localhost:8000/run?name=modules.common.ping"       -H "Content-Type: application/json"       -d '{"action":"PING","mode":"SINGLE","input":{"echo":"world"}}'

# 5) CREATE (스코프 필요)
curl -X POST "http://localhost:8000/run?name=modules.foo.bar"       -H "Content-Type: application/json" -H "X-Scopes: foo:create"       -d '{"action":"CREATE","mode":"SINGLE","input":{"name":"alpha"}}'

# 6) BULK auto_fanout
curl -X POST "http://localhost:8000/run?name=modules.foo.bar"       -H "Content-Type: application/json" -H "X-Scopes: foo:create"       -d '{"action":"CREATE","mode":"BULK","inputs":[{"name":"a"},{"name":"b"}],"options":{"auto_fanout":true}}'
```

## 디렉터리
- `/core`: 계약/레지스트리/실행기/보안
- `/server`: API Shell (`POST /run`)
- `/modules`: 기능 모듈(핫로딩)
- `/pages`: 오케스트레이션(화면 1장 = 1 메인)
- `/db`: 테이블 모듈 + SQL 모듈(스텁)
- `/jobs`: 스케줄러/워커(스텁)
- `/compose`: 개발용 도커 컴포즈
- `/.env.example`: 환경변수 샘플

## 설계 원칙 반영
- 코어 불변, 확장은 모듈 추가만
- Envelope 통신 (SINGLE/BULK)
- manifest 기반 스키마/권한/시크릿
- 파일 저장 → 핫로딩 즉시 반영
