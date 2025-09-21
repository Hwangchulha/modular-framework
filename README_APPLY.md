# Hotfix — KIS 계좌 조회 ImportError (`No module named 'requests'`) + 진단
이 패치는 `modules.broker.kis.accounts` 임포트 시 `requests` 누락으로
실패하는 문제를 해결하고, 확인용 진단 엔드포인트를 추가합니다.

## 포함물
- server/diagnostics.py : `/_diag` 라우터 (env, import, crypto, requests)
- tools/diag_env.py     : 콘솔 진단 스크립트
- requirements.txt      : `requests>=2.32` 포함한 표준 포맷
- apply_patch.py        : 자동 적용 스크립트

## 적용
1) 레포 루트에 ZIP 풀기
2) `python apply_patch.py`
3) 의존성 설치 또는 Docker 재빌드
   - `pip install -r requirements.txt`
   - (Docker) `docker build -t modular-framework:dev .`
4) 서버 재시작 → 확인
   - `GET /_diag/env`  : `"requests": {"present": true, ...}` 이어야 함
   - `GET /_diag/import/modules.broker.kis.accounts` : 200이면 OK

## 비고
- 여전히 실패한다면, 서버가 **다른 파이썬/컨테이너**로 실행 중일 수 있습니다.
  `/_diag/env`의 `"executable"` 경로로 실제 런타임을 확인하세요.
- 이 패치는 의존성/진단만 다룹니다. KIS API 키/계정 권한 문제는 별개입니다.

---
데이터/연동은 지연·오류 가능, 이 자료는 **투자권유가 아닙니다**.
