@echo off
rem 公式サイトから最新結果を取り込み、docs\index.html を作り直して Firebase に公開する
cd /d %~dp0
"C:\Users\shios\AppData\Local\Programs\Python\Python39\python.exe" -X utf8 scrape.py || goto :err
call firebase deploy --only hosting || goto :err
echo.
echo 公開しました: https://mleague-nakama.web.app
start "" https://mleague-nakama.web.app
pause
exit /b 0
:err
echo エラーで止まりました。上のメッセージを確認してください。
pause
exit /b 1
