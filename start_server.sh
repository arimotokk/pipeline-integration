#!/bin/bash
# Simple server startup script for macOS

cd /Users/arimotosaki/Documents/GitHub/pipeline-integration

# Activate virtual environment
source venv/bin/activate

# Kill any existing process on port 8000
echo "Checking for existing server on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✓ Killed existing server" || echo "✓ Port 8000 is available"

echo ""
echo "Starting VAT Integration Pipeline server..."
echo "Access the dashboard at: http://localhost:8000/ui/dashboard"
echo "Press CTRL+C to stop the server"
echo ""

# Start server
python -m uvicorn src.api.main:app --reload
