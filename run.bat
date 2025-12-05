@echo off
chcp 65001 >nul
echo =======================================
echo Control Chart 분석 시스템 시작
echo =======================================
echo.
echo 브라우저가 자동으로 열립니다...
echo 종료하려면 Ctrl+C를 누르세요.
echo.
python -m streamlit run app.py
pause
