# Step 2 — 이체 메인 화면 (One‑File GUI 탭)

이 번들은 기존 레포에 **그대로 덮어쓰기**하면 됩니다.

## 포함된 것
- `start.py`: 탭(Notebook) 추가 — **운영/서버**, **이체** 두 개 탭
- `modules/demo/banks` : 은행 목록 제공 (LIST)
- `modules/demo/accounts` : 데모 계좌 상태 저장/조회 (LIST, BALANCE, INIT, DEBIT, CREDIT)
- `modules/demo/transfer` : 이체 유효성 검사/수수료/실행 (VALIDATE, QUOTE, SUBMIT)
- `data/`: 데모 은행/계좌 JSON, 런타임 상태 파일 위치

## 쓰는 법 (GUI만)
1) `start.py` 더블클릭 → **[의존성 설치/점검]** (최초 1회)
2) **[서버 실행]**
3) **[이체] 탭**으로 이동
   - (필요 시) **[데모 데이터 초기화]** → 기본 계좌/잔액 로드
   - **출금계좌/입금은행/입금계좌/금액/받는분/메모** 입력
   - **[수수료 미리보기]** → QUOTE
   - **[이체 실행]** → SUBMIT → 결과/에러 표시

> 모든 호출은 `/run` 엔드포인트 + Envelope 규약을 통해 이뤄집니다. 서버는 UI를 서빙하지 않습니다.
