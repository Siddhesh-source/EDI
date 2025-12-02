# Build script for C++ Technical Indicator Engine (Windows PowerShell)

Write-Host "Building C++ Technical Indicator Engine..." -ForegroundColor Green

# Create build directory
if (-not (Test-Path "build")) {
    New-Item -ItemType Directory -Path "build" | Out-Null
}

Set-Location build

# Configure with CMake
Write-Host "Configuring with CMake..." -ForegroundColor Yellow
cmake ..

if ($LASTEXITCODE -ne 0) {
    Write-Host "CMake configuration failed!" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Build
Write-Host "Building..." -ForegroundColor Yellow
cmake --build . --config Release

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Copy the compiled module to the parent directory
$module = Get-ChildItem -Filter "indicators_engine*.pyd" -Recurse | Select-Object -First 1
if ($null -eq $module) {
    $module = Get-ChildItem -Filter "indicators_engine*.so" -Recurse | Select-Object -First 1
}

if ($null -ne $module) {
    Copy-Item $module.FullName -Destination ".." -Force
    Write-Host "Build successful! Module copied to src/indicators/" -ForegroundColor Green
} else {
    Write-Host "Warning: Could not find compiled module" -ForegroundColor Yellow
}

Set-Location ..
Write-Host "Done!" -ForegroundColor Green
