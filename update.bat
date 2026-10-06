@echo off
rem 手動で最新結果を取り込む。普段は GitHub Actions が毎晩自動でやるので不要。
rem league.json やデザイン(template.html)を変えたときは、これで Firebase に公開し直す。
cd /d %~dp0
"C:\Users\shios\AppData\Local\Programs\Python\Python39\python.exe" -X utf8 scrape.py || goto :err
git add data/data.json
git diff --cached --quiet || (git commit -q -m "試合結果を更新(手動)" && git pull -q --rebase && git push -q)
call firebase deploy --only hosting || goto :err
echo.
echo 公開しました: https://mleague-nakama.web.app
pause
exit /b 0
:err
echo エラーで止まりました。上のメッセージを確認してください。
pause
exit /b 1
