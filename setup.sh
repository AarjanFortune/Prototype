#!/bin/bash

# Guitar Transcription Web App - Quick Start Script
# This script automates the setup process

set -e

echo "🎸 Guitar Transcription Web App - Setup Script"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check prerequisites
echo "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.10+"
    exit 1
fi
print_status "Python 3 found: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js not found. Please install Node.js 16+"
    exit 1
fi
print_status "Node.js found: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    print_error "npm not found. Please install npm"
    exit 1
fi
print_status "npm found: $(npm --version)"

# Check FFmpeg (optional but recommended)
if ! command -v ffmpeg &> /dev/null; then
    print_info "FFmpeg not found (optional). YouTube downloads will fail without it."
    print_info "Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
else
    print_status "FFmpeg found: $(ffmpeg -version | head -1)"
fi

echo ""
echo "Setting up backend..."

# Create backend virtual environment
if [ ! -d "backend/venv" ]; then
    print_info "Creating Python virtual environment..."
    cd backend
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

cd backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies
print_info "Installing Python dependencies (this may take a few minutes)..."
pip install --upgrade pip
pip install -r requirements.txt
print_status "Python dependencies installed"

# Create necessary directories
mkdir -p models uploads temp
print_status "Created model and upload directories"

cd ..

echo ""
echo "Setting up frontend..."

cd frontend

# Install npm dependencies
print_info "Installing npm dependencies..."
npm install
print_status "npm dependencies installed"

cd ..

echo ""
echo "=============================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=============================================="
echo ""
echo "Next steps:"
echo ""
echo "Terminal 1 - Start Backend:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  python -m uvicorn main:app --reload"
echo ""
echo "Terminal 2 - Start Frontend:"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo "Then open: http://localhost:5173"
echo ""
echo "For more information, see:"
echo "  - README.md (full documentation)"
echo "  - SETUP_GUIDE.md (detailed setup)"
echo "  - QUICK_REFERENCE.md (quick commands)"
echo ""
echo -e "${GREEN}Happy transcribing! 🎸${NC}"
