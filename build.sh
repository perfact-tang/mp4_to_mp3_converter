#!/bin/bash

# Build script for MP4 to MP3 Converter macOS application
# This script creates a distributable .app bundle and .dmg installer

set -e

echo "🚀 Starting MP4 to MP3 Converter build process..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist MP4toMP3Converter.app MP4toMP3Converter.dmg

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Check if FFmpeg is available
echo "🔍 Checking FFmpeg availability..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg not found in PATH. Attempting to install via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo "❌ FFmpeg not found and Homebrew not available. Please install FFmpeg manually."
        exit 1
    fi
fi

# Create icons directory if it doesn't exist
mkdir -p icons

# Create a simple icon if it doesn't exist
if [ ! -f "icons/app.icns" ]; then
    echo "🎨 Creating application icon..."
    # Create a simple PNG icon and convert to ICNS
    python3 -c "
import os
from PIL import Image, ImageDraw, ImageFont

# Create icon
size = 512
img = Image.new('RGBA', (size, size), (0, 122, 255, 255))
draw = ImageDraw.Draw(img)

# Draw a simple play button icon
margin = size // 4
center = size // 2

# Draw triangle (play button)
points = [
    (margin, margin),
    (size - margin, center),
    (margin, size - margin)
]
draw.polygon(points, fill=(255, 255, 255, 255))

# Save as PNG
img.save('icons/icon_512x512.png')

# Create different sizes
sizes = [16, 32, 64, 128, 256, 512]
for s in sizes:
    resized = img.resize((s, s), Image.Resampling.LANCZOS)
    resized.save(f'icons/icon_{s}x{s}.png')

print('Icon created successfully')
"
    
    # Convert PNG to ICNS (if available)
    if command -v png2icns &> /dev/null; then
        png2icns icons/app.icns icons/icon_*.png
    else
        echo "⚠️  png2icns not available. Using PNG icon instead."
        cp icons/icon_512x512.png icons/app.png
    fi
fi

# Build the application
echo "🔨 Building application with PyInstaller..."
python -m PyInstaller mp4_to_mp3_converter.spec --clean

# Check if build was successful
if [ ! -d "dist/MP4toMP3Converter.app" ]; then
    echo "❌ Build failed!"
    exit 1
fi

# Copy FFmpeg binary to the app bundle
echo "📁 Copying FFmpeg to app bundle..."
FFMPEG_PATH=$(which ffmpeg)
if [ -f "$FFMPEG_PATH" ]; then
    cp "$FFMPEG_PATH" "dist/MP4toMP3Converter.app/Contents/MacOS/ffmpeg"
    chmod +x "dist/MP4toMP3Converter.app/Contents/MacOS/ffmpeg"
    echo "✅ FFmpeg copied to app bundle"
else
    echo "⚠️  FFmpeg binary not found, app may not work correctly"
fi

# Code signing (optional - requires Apple Developer account)
if [ -n "$CODESIGN_IDENTITY" ]; then
    echo "🔐 Code signing application..."
    codesign --deep --force --verify --verbose \
        --sign "$CODESIGN_IDENTITY" \
        "dist/MP4toMP3Converter.app"
    echo "✅ Code signing completed"
else
    echo "ℹ️  Code signing skipped (set CODESIGN_IDENTITY environment variable to enable)"
fi

# Create DMG installer
echo "💿 Creating DMG installer..."
hdiutil create -volname "MP4 to MP3 Converter" \
    -srcfolder dist/MP4toMP3Converter.app \
    -ov -format UDZO \
    -fs HFS+ \
    -size 100m \
    "MP4toMP3Converter.dmg"

echo "✅ Build completed successfully!"
echo ""
echo "📦 Artifacts created:"
echo "  - Application: dist/MP4toMP3Converter.app"
echo "  - Installer: MP4toMP3Converter.dmg"
echo ""
echo "🎉 You can now distribute the application!"

# Optional: Verify the app bundle
echo "🔍 Verifying app bundle..."
if codesign -dv --verbose=4 "dist/MP4toMP3Converter.app" 2>/dev/null; then
    echo "✅ App bundle verification passed"
else
    echo "⚠️  App bundle verification failed (expected for unsigned apps)"
fi