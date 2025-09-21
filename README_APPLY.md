# KIS Account Debug Extension
**문제**: 연결 테스트는 OK인데, 계좌 조회 화면의 데이터가 이상하거나 모의처럼 보이는 경우
**해결**: 실제 KIS 응답 RAW와 UI 매핑 결과를 한 번에 비교할 수 있는 엔드포인트 추가

## 추가된 엔드포인트 (이미 /_kisdiag 라우터가 등록되어 있어야 함)
- `POST /_kisdiag/account`
  - 입력(JSON): `appkey, appsecret, account_no, product_code="01", custtype="P", env="prod|vts"`
  - 출력: `raw`(KIS 원본), `mapped`(UI형태), `meta`(TR_ID/환경/HTTP코드) 포함
- `POST /_kisdiag/account/match`
  - 위 `raw`→`mapped` 결과와 **현재 UI 핸들러(`modules.broker.kis.accounts`)의 결과를 비교(diff)**

## 적용
1) ZIP을 레포 루트에 풀기
2) `python apply_patch.py`
3) 서버 재시작
4) 아래처럼 호출
   ```bash
   curl -X POST http://<host>:<port>/_kisdiag/account \
     -H "Content-Type: application/json" \
     -d '{"appkey":"...", "appsecret":"...", "account_no":"12345678", "env":"prod"}'
   ```
   또는
   ```bash
   curl -X POST http://<host>:<port>/_kisdiag/account/match -H "Content-Type: application/json" -d '{...}'
   ```

## 기대 효과
- **실제 응답(raw)** 에 종목/잔고가 들어오는지, TR/환경이 올바른지 즉시 확인
- UI 쪽 매핑/캐시/모의데이터 경로가 섞였는지 `diff`에서 바로 확인

---
데이터/연동은 지연·오류 가능, 본 자료는 **투자권유가 아닙니다**. KIS/OpenAPI 약관 및 키/계좌 정보 보안을 준수하세요.
