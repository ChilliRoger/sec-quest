# Windows PowerShell Pre-Validation Commands
# ============================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  sec-quest Pre-Validation (Windows)" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Check file structure
Write-Host "[1/5] Checking file structure..." -ForegroundColor Yellow
$requiredFiles = @(
    "Dockerfile",
    "openenv.yaml", 
    "inference.py",
    "models.py",
    "client.py",
    "__init__.py",
    "README.md",
    "pyproject.toml"
)

$missing = @()
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file MISSING" -ForegroundColor Red
        $missing += $file
    }
}

if ($missing.Count -gt 0) {
    Write-Host "`nERROR: Missing required files!" -ForegroundColor Red
    exit 1
}

# Step 2: Check server files
Write-Host "`n[2/5] Checking server directory..." -ForegroundColor Yellow
$serverFiles = @(
    "server\app.py",
    "server\environment.py",
    "server\grader.py",
    "server\tasks.py",
    "server\requirements.txt",
    "server\__init__.py"
)

foreach ($file in $serverFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file MISSING" -ForegroundColor Red
        $missing += $file
    }
}

# Step 3: Check if Docker is available
Write-Host "`n[3/5] Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Docker installed: $dockerVersion" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Docker not found" -ForegroundColor Red
        Write-Host "    Install from: https://docs.docker.com/desktop/install/windows-install/" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ Docker not found" -ForegroundColor Red
    Write-Host "    Install from: https://docs.docker.com/desktop/install/windows-install/" -ForegroundColor Yellow
}

# Step 4: Check if openenv-core is installed
Write-Host "`n[4/5] Checking openenv-core..." -ForegroundColor Yellow
try {
    $openenvCheck = python -c "import openenv; print(openenv.__version__)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ openenv-core installed: v$openenvCheck" -ForegroundColor Green
    } else {
        Write-Host "  ✗ openenv-core not installed" -ForegroundColor Red
        Write-Host "    Install with: pip install openenv-core" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ openenv-core not installed" -ForegroundColor Red
    Write-Host "    Install with: pip install openenv-core" -ForegroundColor Yellow
}

# Step 5: Check Python dependencies
Write-Host "`n[5/5] Checking Python environment..." -ForegroundColor Yellow
$pythonPackages = @("fastapi", "uvicorn", "pydantic", "openai", "requests")
foreach ($pkg in $pythonPackages) {
    try {
        $null = python -c "import $pkg" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ $pkg installed" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $pkg not installed" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ✗ $pkg not installed" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Pre-validation check complete!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Install missing dependencies if any" -ForegroundColor White
Write-Host "2. Build Docker image: docker build -t sec-quest ." -ForegroundColor White
Write-Host "3. Run server: python -m uvicorn server.app:app --host 0.0.0.0 --port 7860" -ForegroundColor White
Write-Host "4. Test inference: python inference.py --url http://localhost:7860`n" -ForegroundColor White
