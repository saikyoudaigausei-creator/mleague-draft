# タスクスケジューラから 21:00〜0:00 の30分おきに呼ばれる。
# 公式サイトから取り込み、変化があれば GitHub に送る(アプリは GitHub の data.json を読む)。Firebase は触らない。
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [Text.Encoding]::UTF8  # python の UTF-8 出力をログで文字化けさせない
Set-Location $PSScriptRoot
$git = Join-Path $env:USERPROFILE "OneDrive\デスクトップ\Claude\Git\cmd\git.exe"
$py = "C:\Users\shios\AppData\Local\Programs\Python\Python39\python.exe"
New-Item -ItemType Directory -Force logs | Out-Null
$log = "logs\auto.log"

function Log($s) { Add-Content -Path $log -Value $s -Encoding UTF8 }
Log "===== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
& $git pull -q --rebase 2>&1 | ForEach-Object { Log $_ }
& $py -X utf8 scrape.py 2>&1 | ForEach-Object { Log $_ }
if ($LASTEXITCODE -ne 0) { Log "scrape.py 失敗"; exit 1 }
& $git add data/data.json
& $git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    & $git commit -q -m "試合結果を更新(PC)" 2>&1 | ForEach-Object { Log $_ }
    & $git push -q 2>&1 | ForEach-Object { Log $_ }
    Log "GitHub に送信"
}
