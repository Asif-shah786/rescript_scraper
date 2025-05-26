#!/usr/bin/env bash
set -e  # Exit on error
set -x  # Print commands as they are executed

echo "Starting Chrome and ChromeDriver installation..."

# Install required dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y \
    wget \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    xvfb \
    libxi6 \
    libxtst6 \
    libxss1 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1

# Install Chrome
echo "Installing Chrome..."
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb

# Print Chrome version
echo "Chrome version:"
google-chrome-stable --version

# Install ChromeDriver
echo "Installing ChromeDriver..."
CHROME_VERSION=$(google-chrome-stable --version | awk '{print $3}' | cut -d '.' -f 1)
echo "Chrome major version: $CHROME_VERSION"

# Download and install ChromeDriver
wget "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION" -O - > CHROME_DRIVER_VERSION
CHROME_DRIVER_VERSION=$(cat CHROME_DRIVER_VERSION)
echo "ChromeDriver version: $CHROME_DRIVER_VERSION"

wget "https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip
chmod +x chromedriver
mv chromedriver /usr/local/bin/
rm chromedriver_linux64.zip CHROME_DRIVER_VERSION

# Set up permissions
echo "Setting up permissions..."
chmod 755 /usr/local/bin/chromedriver
chown root:root /usr/local/bin/chromedriver

# Verify ChromeDriver installation
echo "Verifying ChromeDriver installation..."
chromedriver --version

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Print environment information
echo "Environment information:"
which google-chrome-stable
which chromedriver
ls -l /usr/local/bin/chromedriver

# Set up display for headless mode
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x16 &

# Run your script
echo "Starting the application..."
python api/Data_Script/working.py 