#!/bin/bash

# Deploy to DietPi Script
# Quick deployment of changed files to DietPi server

DIETPI_HOST="dietpi@192.168.31.58"
DIETPI_PATH="/home/dietpi/New/summary/"

echo "🚀 Deploying to DietPi..."

# Check if DietPi is reachable
if ! ping -c 1 192.168.31.58 > /dev/null 2>&1; then
    echo "❌ Cannot reach DietPi at 192.168.31.58"
    echo "   Make sure DietPi is on and connected to the network"
    exit 1
fi

echo "📁 Copying files to DietPi..."

# Copy main application files
echo "   → app.py"
scp app.py ${DIETPI_HOST}:${DIETPI_PATH}

echo "   → static/index.html"
scp static/index.html ${DIETPI_HOST}:${DIETPI_PATH}static/

echo "   → requirements.txt (if exists)"
if [ -f "requirements.txt" ]; then
    scp requirements.txt ${DIETPI_HOST}:${DIETPI_PATH}
fi

echo "✅ Files deployed successfully!"
echo ""
echo "🔄 To restart the server on DietPi, run:"
echo "   ssh ${DIETPI_HOST}"
echo "   cd ${DIETPI_PATH}"
echo "   pkill -f 'python3 app.py'  # Stop current server"
echo "   source venv/bin/activate"
echo "   python3 app.py  # Start updated server"
echo ""
echo "🌐 Server will be available at: http://192.168.31.58:9000" 