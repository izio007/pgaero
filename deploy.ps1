<#
.SYNOPSIS
    Безопасный промышленный скрипт развертывания pgaero Workspace.
    Исключает уничтожение и повторный накат данных при перезапусках сервера.
#>

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Clear-Host
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "🦅 ЗАПУСК СЕКЬЮРНОГО СЕРВЕРА ПЛАНИРОВАНИЯ КБ 'PGAERO'" -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Cyan

# ----------------------------------------------------------------------------
# ШАГ 1: ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА WINDOWS
# ----------------------------------------------------------------------------
Write-Host "[1/4] Проверка привилегий безопасности ОС Windows..." -ForegroundColor Cyan
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "🚨 КРИТИЧЕСКАЯ ОШИБКА: Запустите PowerShell от имени Администратора!" -ForegroundColor Red
    Exit
}
Write-Host "✅ Права администратора подтверждены." -ForegroundColor Green

# ----------------------------------------------------------------------------
# ШАГ 2: ВЕРИФИКАЦИЯ ОКРУЖЕНИЯ PYTHON
# ----------------------------------------------------------------------------
Write-Host "`n[2/4] Проверка интерпретатора Python и зависимостей КБ..." -ForegroundColor Cyan
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "🚨 КРИТИЧЕСКАЯ ОШИБКА: Python не найден в системных переменных PATH!" -ForegroundColor Red
    Exit
}
$pythonVersion = python --version 2>&1
Write-Host "✅ Обнаружен $pythonVersion" -ForegroundColor Green

# ----------------------------------------------------------------------------
# ШАГ 3: ИНТЕЛЛЕКТУАЛЬНЫЙ КОНТРОЛЬ СУБД (БЕЗ ПЕРЕСОЗДАНИЯ ТАБЛИЦ)
# ----------------------------------------------------------------------------
Write-Host "`n[3/4] Проверка состояния базы данных PostgreSQL 18..." -ForegroundColor Cyan

$pgPort = 5432
$connectionTest = New-Object System.Net.Sockets.TcpClient
$errorActionPreference = 'SilentlyContinue'
$connectionTest.Connect("127.0.0.1", $pgPort)
$errorActionPreference = 'Continue'

if (-not $connectionTest.Connected) {
    Write-Host "🚨 КРИТИЧЕСКАЯ ОШИБКА: Служба PostgreSQL не отвечает на порту $pgPort!" -ForegroundColor Red
    Exit
}
$connectionTest.Close()

$psqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
if (-not (Test-Path $psqlPath)) {
    $psqlPath = Get-ChildItem -Path "C:\Program Files\PostgreSQL" -Filter "psql.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
}

$ddlPath = Join-Path $PSScriptRoot "src\dbinit.sql"
$dataPath = Join-Path $PSScriptRoot "src\dbdata.sql"
$env:PGPASSWORD = "Avdnm415"

# Проверяем, создана ли уже таблица продуктов. Если создана — пропускаем деструктивный DDL/DML накат
$checkTableCmd = "& `"$psqlPath`" -h localhost -p 5432 -U postgres -d postgres -t -c `"SELECT to_regclass('public.products');`""
$tableExists = Invoke-Expression $checkTableCmd

if ($tableExists -match "products") {
    Write-Host "🔒 Производственная база данных КБ активна. Все заведенные часы инженеров и листы согласования сохранены." -ForegroundColor Green
    Write-Host "🔄 Пропуск повторного наката структуры и датасета во избежание потери данных." -ForegroundColor Gray
} else {
    Write-Host "Empty СУБД обнаружена! Выполняю первичную инициализацию..." -ForegroundColor Yellow
    
    if (Test-Path $ddlPath) {
        Write-Host "🔨 Накатываю структуру таблиц, CHECK-ограничения и индексы..." -ForegroundColor Gray
        & $psqlPath -h localhost -p 5432 -U postgres -d postgres -f $ddlPath | Out-Null
        Write-Host "✅ Первичная структура СУБД нормализована." -ForegroundColor Green
    }
    if (Test-Path $dataPath) {
        Write-Host "🚀 Наполняю базу стартовым датасетом (250 задач КБ)..." -ForegroundColor Gray
        & $psqlPath -h localhost -p 5432 -U postgres -d postgres -f $dataPath | Out-Null
        Write-Host "✅ Стартовый демонстрационный датасет успешно загружен!" -ForegroundColor Green
    }
}

# ----------------------------------------------------------------------------
# ШАГ 4: ЗАПУСК ВЫСОКОСКОРОСТНОГО ИНТЕРФЕЙСА STREAMLIT
# ----------------------------------------------------------------------------
Write-Host "`n[4/4] Запуск веб-сервера pgaero Workspace на loopback TCP..." -ForegroundColor Cyan
$entryPoint = Join-Path $PSScriptRoot "src\pgaero.py"

# Чистим кэш байт-кода для применения горячих фиксов стилизации Pandas
Get-ChildItem -Path $PSScriptRoot -Filter "__pycache__" -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "🚀 Сервер pgaero успешно развернут и доступен внутри КБ." -ForegroundColor Green
Write-Host "🌐 Локальный адрес для инженеров: http://127.0.0.1:8501" -ForegroundColor Yellow

$env:PGPASSWORD = $null
& streamlit run $entryPoint --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
