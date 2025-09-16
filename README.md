# Step — 네트워크 접근 가능한 Web UI + 로그인/회원가입/프로필(세션/자동로그인)

이 번들은 기존 레포(`modular-framework`)에 **그대로 덮어쓰기**하면 됩니다.

## 무엇이 추가되었나
- **ui_web/**: 별도 웹 서버(독립 프로세스). 정적 SPA(HTML/JS/CSS) 제공 — 다른 네트워크에서 접속 가능.
- **start.py**: GUI에서 **API 서버**와 **Web UI 서버**를 각각 실행/중단. ‘외부 접속 허용(0.0.0.0)’ 토글, 포트 설정, UI 열기/URL 복사 제공.
- **인증 모듈**(manifest+schema+handler):
  - `modules.auth.users`: REGISTER, GET, UPDATE
  - `modules.auth.login`: LOGIN, REFRESH, LOGOUT, WHOAMI
  - 저장소: `data/auth.db` (SQLite, PBKDF2 해시)
- **JWT 유틸 + 인터셉터 확장**
  - `core/jwt_utils.py`: 액세스 토큰(JWT) 발급/검증
  - 인터셉터가 `Authorization: Bearer <JWT>`를 파싱하여 `scopes`/`user_id`를 컨텍스트에 주입
- **CORS 허용**: API 서버가 외부 UI에서의 호출을 허용(개발 기본: 모든 오리진 허용)

## 실행 (GUI만)
1) `start.py` 더블클릭 → **[의존성 설치/점검]**
2) **API 서버 시작** → **Web UI 시작** (필요 시 ‘외부 접속 허용’ 체크)
3) **[Open Web UI]** 버튼 클릭 또는 표시된 URL로 접속(같은 네트워크의 다른 PC/모바일에서 접근 가능)
4) Web UI에서 **회원가입 → 로그인 → 프로필 보기/수정**
   - **자동 로그인**: 로그인 시 ‘자동 로그인’ 체크하면 refresh token을 로컬 저장(localStorage)하고, 페이지 재접속 시 자동 로그인 시도

> 서버는 여전히 **/run + Envelope**만 처리. Web UI는 **별도 프로세스**에서 정적 제공(지침 준수: API 서버가 UI를 서빙하지 않음).
