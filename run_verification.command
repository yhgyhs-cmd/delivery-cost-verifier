#!/bin/bash

# Navigate to the script's directory
cd "$(dirname "$0")"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found!"
    echo "Please ensure '.venv' exists in this folder."
    read -p "Press Enter to exit..."
    exit 1
fi

# Run the verification script
echo "Running cost verification..."
python3 verify_cost.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Verification Completed Successfully!"
else
    echo ""
    echo "❌ Verification Failed with an error."
fi

# Keep the window open
echo ""
read -p "Press Enter to close..."
