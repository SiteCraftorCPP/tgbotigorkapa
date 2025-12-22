# Остановка локального бота
Get-Process python* -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*Python*"} | Stop-Process -Force
Write-Host "Бот остановлен"

