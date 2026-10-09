@echo off
chcp 65001 >nul
rem タスクスケジューラから 23:00 / 23:30 / 0:00 に呼ばれる。取り込んで GitHub に送るだけ(Firebase は触らない)
cd /d %~dp0
if not exist logs mkdir logs
echo ===== %date% %time% >> logs\auto.log
git pull -q --rebase >> logs\auto.log 2>&1
"C:\Users\shios\AppData\Local\Programs\Python\Python39\python.exe" -X utf8 scrape.py >> logs\auto.log 2>&1 || exit /b 1
git add data/data.json
git diff --cached --quiet || (git commit -q -m "試合結果を更新(PC)" && git push -q) >> logs\auto.log 2>&1
