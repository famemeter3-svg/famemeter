#!/bin/bash

# DynamoDB Local UI Tool - Run Script
# Simple script to set up and run the local UI viewer

set -e

echo ""
echo "=========================================="
echo "DynamoDB Data Viewer - Startup"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Check if venv exists, if not create it
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

echo ""
echo "📦 Activating virtual environment..."
source venv/bin/activate

echo ""
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

echo ""
echo "🔍 Checking AWS configuration..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "⚠️  Warning: AWS credentials not configured"
    echo "   Run: aws configure"
    echo "   or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
fi

echo ""
echo "✓ Check complete!"
echo ""
echo "=========================================="
echo "Starting server..."
echo "=========================================="
echo ""
echo "🌐 Open your browser: http://localhost:5000"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Run the Flask app
python3 app.py
