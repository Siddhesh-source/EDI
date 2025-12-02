# Setup script for the trading system (Windows PowerShell)

Write-Host "=== Explainable Algorithmic Trading System Setup ===" -ForegroundColor Green
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version
Write-Host "Python version: $pythonVersion"

# Create virtual environment
Write-Host ""
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Copy environment file
if (-not (Test-Path .env)) {
    Write-Host ""
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "Please edit .env file with your configuration" -ForegroundColor Cyan
}

# Start Docker services
Write-Host ""
Write-Host "Starting Docker services (Redis and PostgreSQL)..." -ForegroundColor Yellow
docker-compose up -d

# Wait for services to be ready
Write-Host ""
Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check Docker services
Write-Host ""
Write-Host "Checking Docker services..." -ForegroundColor Yellow
docker-compose ps

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env file with your API keys and configuration"
Write-Host "2. Activate virtual environment: .\venv\Scripts\Activate.ps1"
Write-Host "3. Run tests: pytest"
Write-Host "4. Start the API server: uvicorn src.api.main:app --reload"
Write-Host ""
