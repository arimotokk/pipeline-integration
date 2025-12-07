#!/bin/bash
# Simple server startup script for macOS

cd /Users/arimotosaki/Documents/GitHub/pipeline-integration

# Activate virtual environment
source venv/bin/activate

echo "Starting VAT Integration Pipeline server..."
echo "Access the dashboard at: http://localhost:8000/ui/dashboard"
echo "Press CTRL+C to stop the server"
echo ""

# Start server
python -m uvicorn src.api.main:app --reload
