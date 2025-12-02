#!/bin/bash
# Setup script for the trading system

set -e

echo "=== Explainable Algorithmic Trading System Setup ==="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Copy environment file
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your configuration"
fi

# Start Docker services
echo ""
echo "Starting Docker services (Redis and PostgreSQL)..."
docker-compose up -d

# Wait for services to be ready
echo ""
echo "Waiting for services to be ready..."
sleep 5

# Check Docker services
echo ""
echo "Checking Docker services..."
docker-compose ps

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys and configuration"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run tests: pytest"
echo "4. Start the API server: uvicorn src.api.main:app --reload"
echo ""
