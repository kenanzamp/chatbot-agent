#!/bin/bash
# Run the autonomous agent server

# Navigate to project directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -e .
else
    source venv/bin/activate
fi

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    if [ -f ".env" ]; then
        export $(cat .env | xargs)
    fi
    
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo "⚠️  Warning: ANTHROPIC_API_KEY not set"
        echo "Please set it with: export ANTHROPIC_API_KEY=your-key-here"
        echo "Or create a .env file with: ANTHROPIC_API_KEY=your-key-here"
        echo ""
    fi
fi

echo "🚀 Starting Autonomous Agent..."
echo "Open http://localhost:8000 in your browser"
echo ""

# Run the server
python -m agent.main
