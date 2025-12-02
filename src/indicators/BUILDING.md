# Building the C++ Technical Indicator Engine

This guide provides detailed instructions for building the C++ Technical Indicator Engine on different platforms.

## Prerequisites

### All Platforms

1. **Python 3.8+** with pip
2. **pybind11** Python package:
   ```bash
   pip install pybind11
   ```

### Windows

1. **CMake 3.12+**: Download from https://cmake.org/download/
   - During installation, select "Add CMake to system PATH"

2. **Visual Studio 2017 or later** with C++ tools:
   - Download Visual Studio Community (free) from https://visualstudio.microsoft.com/
   - During installation, select "Desktop development with C++"
   - This includes the MSVC compiler

3. **Alternative**: MinGW-w64 (if not using Visual Studio)
   - Download from https://www.mingw-w64.org/
   - Add to PATH

### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install build-essential cmake python3-dev
```

### Linux (Fedora/RHEL)

```bash
sudo dnf install gcc gcc-c++ cmake python3-devel
```

### macOS

```bash
# Install Xcode Command Line Tools
xcode-select --install

# Install CMake via Homebrew
brew install cmake
```

## Building

### Quick Build (Recommended)

#### Windows PowerShell

```powershell
cd src/indicators
.\build.ps1
```

#### Linux/macOS

```bash
cd src/indicators
chmod +x build.sh
./build.sh
```

### Manual Build

If the automated scripts don't work, follow these steps:

#### Step 1: Create Build Directory

```bash
cd src/indicators
mkdir build
cd build
```

#### Step 2: Configure with CMake

**Windows (Visual Studio):**
```powershell
cmake ..
```

**Windows (MinGW):**
```powershell
cmake -G "MinGW Makefiles" ..
```

**Linux/macOS:**
```bash
cmake ..
```

#### Step 3: Build

**All Platforms:**
```bash
cmake --build . --config Release
```

#### Step 4: Copy Module

The compiled module will be in the build directory:
- **Windows**: `indicators_engine.pyd`
- **Linux**: `indicators_engine.so`
- **macOS**: `indicators_engine.so`

Copy it to the `src/indicators/` directory:

**Windows:**
```powershell
copy Release\indicators_engine.pyd ..
```

**Linux/macOS:**
```bash
cp indicators_engine*.so ..
```

## Verification

Test that the module loads correctly:

```python
python -c "from src.indicators import TechnicalIndicatorEngine; print('Success!')"
```

Run the test suite:

```bash
pytest tests/test_indicators.py -v
```

## Troubleshooting

### "pybind11 not found"

**Solution:**
```bash
pip install pybind11
```

If CMake still can't find it:
```bash
pip install "pybind11[global]"
```

### "Python.h not found" (Linux)

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# Fedora/RHEL
sudo dnf install python3-devel
```

### "CMake not found"

**Windows:**
- Download and install from https://cmake.org/download/
- Restart PowerShell/Command Prompt after installation

**Linux:**
```bash
sudo apt-get install cmake  # Ubuntu/Debian
sudo dnf install cmake      # Fedora/RHEL
```

**macOS:**
```bash
brew install cmake
```

### "No C++ compiler found"

**Windows:**
- Install Visual Studio with C++ tools
- Or install MinGW-w64

**Linux:**
```bash
sudo apt-get install build-essential
```

**macOS:**
```bash
xcode-select --install
```

### Build succeeds but module not found at runtime

**Solution:**
Ensure the compiled module (`.pyd` or `.so`) is in `src/indicators/` directory:

```bash
ls src/indicators/indicators_engine.*
```

If not present, manually copy from build directory.

### "ImportError: DLL load failed" (Windows)

**Solution:**
- Ensure Visual C++ Redistributable is installed
- Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe

### Permission denied when running build script

**Linux/macOS:**
```bash
chmod +x build.sh
```

## Development Build

For development with debug symbols:

```bash
cd src/indicators/build
cmake -DCMAKE_BUILD_TYPE=Debug ..
cmake --build .
```

## Clean Build

To start fresh:

```bash
cd src/indicators
rm -rf build
rm indicators_engine.*
```

Then rebuild using the instructions above.

## Performance Optimization

The Release build includes optimizations. For maximum performance:

**GCC/Clang:**
```bash
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-O3 -march=native" ..
```

**MSVC:**
```bash
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build . --config Release
```

## Cross-Platform Notes

### Windows Paths

Use forward slashes or escaped backslashes in CMake:
```cmake
set(MY_PATH "C:/path/to/file")
# or
set(MY_PATH "C:\\path\\to\\file")
```

### Python Version

If you have multiple Python versions, specify explicitly:

```bash
cmake -DPYTHON_EXECUTABLE=/path/to/python3 ..
```

### 32-bit vs 64-bit

Ensure Python and compiler architecture match:
- 64-bit Python requires 64-bit compiler
- 32-bit Python requires 32-bit compiler

Check Python architecture:
```python
import platform
print(platform.architecture())
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Install dependencies
  run: |
    pip install pybind11
    
- name: Build C++ module
  run: |
    cd src/indicators
    mkdir build && cd build
    cmake ..
    cmake --build . --config Release
```

### Docker Example

```dockerfile
FROM python:3.10

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/indicators src/indicators
RUN cd src/indicators && \
    mkdir build && cd build && \
    cmake .. && \
    cmake --build . --config Release && \
    cp indicators_engine*.so ..
```

## Support

If you encounter issues not covered here:

1. Check CMake output for specific error messages
2. Verify all prerequisites are installed
3. Try a clean build
4. Check Python and compiler versions match (32/64-bit)

For persistent issues, the Python fallback implementation can be used (though it's not yet fully implemented).
