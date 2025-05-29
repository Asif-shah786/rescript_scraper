#!/usr/bin/env bash
# exit on error
set -o errexit

# Set up directories
INSTALL_DIR="/opt/render/project/src/.local"
mkdir -p $INSTALL_DIR/bin
mkdir -p $INSTALL_DIR/chrome

# Download and install Chrome
echo "Downloading Chrome..."
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O chrome.deb
dpkg-deb -x chrome.deb $INSTALL_DIR/chrome
rm chrome.deb

# Download and install ChromeDriver
echo "Downloading ChromeDriver..."
CHROME_VERSION=$($INSTALL_DIR/chrome/opt/google/chrome/chrome --version | cut -d ' ' -f 3 | cut -d '.' -f 1)
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" -O chromedriver.zip
unzip -q chromedriver.zip -d $INSTALL_DIR/bin
rm chromedriver.zip
chmod +x $INSTALL_DIR/bin/chromedriver

# Create a script to verify installation
cat > $INSTALL_DIR/verify.sh << 'EOF'
#!/bin/bash
echo "Verifying Chrome installation..."
$CHROME_BIN --version
echo "Verifying ChromeDriver installation..."
$CHROMEDRIVER_PATH --version
echo "Checking DISPLAY..."
echo $DISPLAY
EOF
chmod +x $INSTALL_DIR/verify.sh

# Install Python dependencies
pip install -r requirements.txt 