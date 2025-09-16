# Step 3 — 인증/보안 고도화 (지침 v1.4 준수)

이 번들은 기존 레포에 **그대로 덮어쓰기**하면 됩니다.

## 포함 사항
- **core/interceptor.py**: client_ip 추출(X-Forwarded-For, X-Real-IP, X-Client-IP) → ctx.client_ip
- **server/main.py**: Request.client.host를 X-Client-IP로 전달
- **core/ratelimit.py**: 경량 레이트리미터(슬라이딩 윈도우)
- **modules.auth._store**: DB 경로 수정(루트/data), 컬럼(role), 테이블(reset_tokens), 비밀번호 변경·재설정 지원
- **modules.auth.users**: REGISTER/GET/UPDATE + **CHANGE_PASSWORD** 추가
- **modules.auth.reset**(신규): REQUEST/CONFIRM (비밀번호 재설정)
- **modules.auth.login**: 로그인 **레이트리미트(이메일+IP)**, **리프레시 토큰 회전(ROTATE)**
- **ui_web/**: 로그인/회원가입/프로필에
  - “비밀번호 변경” 카드
  - “비밀번호 재설정” 탭(코드 요청/확정 — 데모에선 코드 응답 표시)
  - 에러 메시지 개선

## 사용법
1) `start.py` 실행 → [의존성 설치/점검] → API 시작 → Web UI 시작
2) Web UI
   - (회원가입) → (로그인)
   - 프로필 탭에서 **비밀번호 변경**
   - 비밀번호를 잊었으면 "비밀번호 재설정" 탭에서 **요청 → 코드 입력 → 새 비번 설정**

> 운영에서는 코드 전송을 이메일/SMS로 대체하세요. 여기선 데모이므로 응답으로 코드를 보여줍니다.
