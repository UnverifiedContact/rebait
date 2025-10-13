#!/bin/bash
# Setup script for rebait

echo "🎬 Setting up Rebait - YouTube Transcript Fetcher"
echo "================================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📥 Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Usage examples:"
echo "  python rebait.py 'https://www.youtube.com/watch?v=VIDEO_ID'"
echo "  python rebait.py 'https://www.youtube.com/watch?v=VIDEO_ID' --display"
echo "  python rebait.py 'https://www.youtube.com/watch?v=VIDEO_ID' --languages en es fr"
echo ""
echo "Run demo:"
echo "  python demo.py"
echo ""
echo "Note: Always activate the virtual environment first:"
echo "  source venv/bin/activate"
