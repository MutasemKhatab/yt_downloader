#!/bin/bash
# Deploy script for YouTube Downloader - Termux Server
# This script sets up the Flask server environment in Termux

echo "==== Setting up YouTube Downloader Server for Termux ===="

# Update package lists
echo "Updating package lists..."
pkg update -y

# Install required packages
echo "Installing required packages..."
pkg install -y python ffmpeg

# Install pip if not already installed
if ! command -v pip &> /dev/null; then
    echo "Installing pip..."
    pkg install -y python-pip
fi

# Create a virtual environment (optional but recommended)
echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    pip install virtualenv
    python -m virtualenv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install required Python packages
echo "Installing Python dependencies..."
pip install flask flask-socketio yt-dlp eventlet

# Check if FFmpeg is installed
echo "Checking FFmpeg installation..."
if ! command -v ffmpeg &> /dev/null; then
    echo "WARNING: FFmpeg not found! Please install FFmpeg manually."
    echo "You can install it with: pkg install ffmpeg"
else
    echo "FFmpeg is installed correctly."
fi

# Verify Python dependencies
echo "Verifying Python dependencies..."
pip list | grep -E 'flask|socketio|yt-dlp|eventlet'

echo "==== Server Setup Complete ===="
echo ""
echo "To run the server:"
echo "1. Make sure you're in the project directory"
echo "2. If not in virtual environment, run: source venv/bin/activate"
echo "3. Run: python app.py"
echo ""
echo "The server will be available at http://127.0.0.1:5000"
echo "To make it available to other devices on your network, find your IP address"
echo "with the 'ifconfig' command and update the URL in the Flutter app."
echo ""
echo "Press any key to start the server now, or Ctrl+C to exit"
read -n 1 -s

# Run the server
python app.py
