#!/bin/bash
# Start the VAT Integration Pipeline API Server
# Run this after completing local_setup.sh

set -e

REPO_PATH="/Users/arimotosaki/Documents/GitHub/pipeline-integration"
VENV_NAME="venv"

echo "Starting VAT Integration Pipeline API..."
echo ""

# Navigate to repository
cd "$REPO_PATH"

# Check if virtual environment exists
if [ ! -d "$VENV_NAME" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run local_setup.sh first:"
    echo "  bash local_setup.sh"
    exit 1
fi

# Activate virtual environment
source "$VENV_NAME/bin/activate"

# Start the API server
echo "🚀 Starting API server on http://localhost:8000"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo "Press Ctrl+C to stop the server"
echo ""

python -m uvicorn src.api.main:app --reload
