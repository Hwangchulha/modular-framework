# Modular Framework Hotfix: cryptography 의존성 추가

이 ZIP에는 `requirements.txt` 하나만 들어 있습니다.
레포 루트의 기존 `requirements.txt`를 이 파일로 덮어쓰면
`cryptography` 패키지가 누락되어 발생하던
`No module named 'cryptography'` 오류가 해결됩니다.

## 적용 방법
1) 레포 루트에 있는 `requirements.txt`를 백업합니다.
2) 이 ZIP의 `requirements.txt`로 교체합니다.
3) (로컬) `pip install -r requirements.txt` 실행
   (Docker) 이미지 재빌드: `docker build -t modular-framework:dev .`

## 참고
- 파일은 한 줄당 하나의 패키지로 표준화했습니다.
- 기존 파일에 동일 패키지가 있었다면 이 버전이 적용됩니다.
