#!/bin/bash

echo "Setting up Trading Dashboard..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "Error: Node.js version 18 or higher is required. Current version: $(node -v)"
    exit 1
fi

echo "Node.js version: $(node -v) ✓"

# Install dependencies
echo "Installing dependencies..."
npm install

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo ".env file created. Please update it with your API configuration."
else
    echo ".env file already exists ✓"
fi

echo ""
echo "Setup complete! ✓"
echo ""
echo "To start the development server, run:"
echo "  npm run dev"
echo ""
echo "The dashboard will be available at http://localhost:3000"
