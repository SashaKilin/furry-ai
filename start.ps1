# FurryArt AI - PowerShell launcher
# Правый клик -> "Запустить с помощью PowerShell"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "   FurryArt AI - Poisk Python..." -ForegroundColor Cyan
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""

# Ищем Python
$pythonPaths = @(
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
    "C:\Python313\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe",
    "C:\Python310\python.exe"
)

$py = $null

# Сначала PATH
$fromPath = Get-Command python -ErrorAction SilentlyContinue
if ($fromPath) {
    $ver = & python -c "import sys; print(sys.version_info >= (3,10))" 2>$null
    if ($ver -eq "True") { $py = "python" }
}

# Потом известные пути
if (-not $py) {
    foreach ($p in $pythonPaths) {
        if (Test-Path $p) { $py = $p; break }
    }
}

if (-not $py) {
    Write-Host "  OSHIBKA: Python ne najden!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Ustanovite Python 3.10+ s sajta:" -ForegroundColor Yellow
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host ""
    Start-Process "https://www.python.org/downloads/"
    pause
    exit 1
}

Write-Host "  Python: $py" -ForegroundColor Green

# Проверяем .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env" -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "  Sozdan .env! Vstavte vash Gemini API klyuch:" -ForegroundColor Yellow
    Write-Host "  https://aistudio.google.com/apikey" -ForegroundColor Yellow
    Write-Host ""
    notepad.exe ".env"
    Write-Host "  Posle sokhraneniya .env nazhmi Enter..."
    Read-Host
}

# Устанавливаем зависимости
Write-Host ""
Write-Host "  Ustanavlivayu zavisimosti..." -ForegroundColor Cyan
& $py -m pip install flask google-generativeai pillow python-dotenv requests --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Oshibka ustanovki paketov!" -ForegroundColor Red
    pause; exit 1
}

Write-Host "  Zavisimosti ustanovleny!" -ForegroundColor Green
Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "   Otkroj brauzer: http://localhost:5000" -ForegroundColor Green
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""

Start-Sleep -Seconds 1
Start-Process "http://localhost:5000"
& $py app.py
