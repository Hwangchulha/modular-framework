@echo off
cd /d C:\modular-framework

:: commit 메시지에 오늘 날짜 넣기
set msg=update-%date:~0,10% %time:~0,5%

git add .
git commit -m "%msg%"
git push

pause
