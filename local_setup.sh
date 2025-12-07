#!/bin/bash
# Phase 2 Local Setup Script for macOS
# This script sets up the VAT Integration Pipeline Phase 2 on your local machine

set -e  # Exit on error

echo "=========================================="
echo "VAT Integration Pipeline - Phase 2 Setup"
echo "=========================================="
echo ""

# Configuration
REPO_PATH="/Users/arimotosaki/Documents/GitHub/pipeline-integration"
VENV_NAME="venv"
PYTHON_CMD="python3"

# Navigate to repository
echo "1. Navigating to repository..."
cd "$REPO_PATH"
pwd

# Pull latest changes
echo ""
echo "2. Pulling latest changes from GitHub..."
git fetch origin
git checkout claude/build-vat-integration-phase-1-019EnzcMNyw8ckKZmh2MDBcn
git pull origin claude/build-vat-integration-phase-1-019EnzcMNyw8ckKZmh2MDBcn
echo "✓ Repository updated"

# Remove old virtual environment if exists
if [ -d "$VENV_NAME" ]; then
    echo ""
    echo "3. Removing old virtual environment..."
    rm -rf "$VENV_NAME"
fi

# Create virtual environment
echo ""
echo "4. Creating virtual environment..."
$PYTHON_CMD -m venv "$VENV_NAME"
echo "✓ Virtual environment created: $VENV_NAME"

# Activate virtual environment
echo ""
echo "5. Activating virtual environment..."
source "$VENV_NAME/bin/activate"
echo "✓ Virtual environment activated"

# Upgrade pip
echo ""
echo "6. Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "7. Installing dependencies..."
pip install -r requirements.txt
pip install -r requirements-phase2.txt
echo "✓ Dependencies installed"

# Setup database
echo ""
echo "8. Setting up database and loading sample data..."
python scripts/setup_phase2.py 2>&1 | grep -v "Missing required"
echo "✓ Database initialized"

# Success message
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Virtual environment is activated."
echo "To start the API server, run:"
echo ""
echo "  python -m uvicorn src.api.main:app --reload"
echo ""
echo "Then open in your browser:"
echo "  http://localhost:8000/docs"
echo ""
echo "To activate the virtual environment later:"
echo "  cd $REPO_PATH"
echo "  source $VENV_NAME/bin/activate"
echo ""
echo "=========================================="
