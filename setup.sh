#!/bin/bash

echo "========================================="
echo "  Code Editor Pro - Setup Script"
echo "========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker is installed"
echo "✅ Docker Compose is installed"
echo ""

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p static
mkdir -p workspace

echo "✅ Directories created"
echo ""

# Build Docker image
echo "🔨 Building Docker image..."
docker-compose build

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Failed to build Docker image"
    exit 1
fi

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "To start the editor:"
echo "  docker-compose up -d"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop the editor:"
echo "  docker-compose down"
echo ""
echo "Access the editor at: http://localhost:5000"
echo "Default login: demo / demo123"
echo ""
echo "========================================="