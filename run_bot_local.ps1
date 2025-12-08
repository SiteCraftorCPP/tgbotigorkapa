# Скрипт для запуска бота локально на Windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Запуск Crypto Signal Bot локально" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Переход в директорию проекта
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Активация виртуального окружения
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "✅ Активация виртуального окружения..." -ForegroundColor Green
    & ".\venv\Scripts\Activate.ps1"
} else {
    Write-Host "❌ Виртуальное окружение не найдено!" -ForegroundColor Red
    exit 1
}

# Проверка версии Python
Write-Host ""
Write-Host "📦 Версия Python:" -ForegroundColor Yellow
python --version

# Проверка .env файла
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "⚠️  ВНИМАНИЕ: Файл .env не найден!" -ForegroundColor Yellow
    Write-Host "   Создайте файл .env с необходимыми настройками" -ForegroundColor Yellow
}

# Запуск бота
Write-Host ""
Write-Host "🚀 Запуск бота..." -ForegroundColor Green
Write-Host "   Для остановки нажмите Ctrl+C" -ForegroundColor Gray
Write-Host ""

python main.py



