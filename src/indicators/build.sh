#!/bin/bash
# Build script for C++ Technical Indicator Engine

set -e

echo "Building C++ Technical Indicator Engine..."

# Create build directory
mkdir -p build
cd build

# Configure with CMake
cmake ..

# Build
cmake --build . --config Release

# Copy the compiled module to the parent directory
if [ -f "indicators_engine*.so" ]; then
    cp indicators_engine*.so ..
    echo "Build successful! Module copied to src/indicators/"
elif [ -f "indicators_engine*.pyd" ]; then
    cp indicators_engine*.pyd ..
    echo "Build successful! Module copied to src/indicators/"
else
    echo "Warning: Could not find compiled module"
fi

cd ..
echo "Done!"
