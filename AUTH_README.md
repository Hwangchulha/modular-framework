
# Auth Page + Auto Table

## 서버 실행(도커)
docker-compose up --build

## 페이지 사용
### 렌더 정보(필드 스펙)
Invoke-RestMethod -Uri 'http://localhost:8000/page/run?name=auth' -Method POST -ContentType 'application/json' -Body '{"op":"render"}'

### 회원가입
Invoke-RestMethod -Uri 'http://localhost:8000/run?name=modules.auth.users' -Method POST -ContentType 'application/json' -Body '{"action":"REGISTER","mode":"SINGLE","input":{"email":"you@example.com","password":"secret"}}'

### 로그인(JWT 발급)
Invoke-RestMethod -Uri 'http://localhost:8000/run?name=modules.auth.login' -Method POST -ContentType 'application/json' -Body '{"action":"LOGIN","mode":"SINGLE","input":{"email":"you@example.com","password":"secret"}}'

### 페이지 오케스트레이터 경유
Invoke-RestMethod -Uri 'http://localhost:8000/page/run?name=auth' -Method POST -ContentType 'application/json' -Body '{"op":"signup","input":{"email":"you@example.com","password":"secret"}}'
Invoke-RestMethod -Uri 'http://localhost:8000/page/run?name=auth' -Method POST -ContentType 'application/json' -Body '{"op":"login","input":{"email":"you@example.com","password":"secret"}}'

## 자동 테이블 생성
- 서버 startup 이벤트에서 sqlite 기반 테이블(`auth_users`) 자동 생성
- DB 파일 경로: `DB_URL=sqlite:///data/app.db`
