
# 다음 스텝 패치 (보호 페이지 + 토큰 검증 + 로그아웃)
- modules.auth.me (VERIFY): JWT 검증하고 사용자 프로필 반환
- /ui/account: 로그인 필요 페이지 (없으면 /ui/auth로 안내)
- 로그아웃 버튼: localStorage의 jwt 제거 후 /ui/auth 이동

## 사용
1) 압축을 프로젝트 루트에 풀어 덮어쓰기
2) 도커 사용 중이면 재빌드/재기동 없이도 대개 바로 동작 (필요하면 up -d --build)
3) 브라우저에서: 
   - /ui/auth 에서 로그인 -> 토큰 저장
   - /ui/account 로 이동하여 내 정보 확인
