#!/usr/bin/env bash

# Install Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt update && apt install -y ./google-chrome-stable_current_amd64.deb

# Install ChromeDriver
CHROME_VERSION=$(google-chrome-stable --version | awk '{print $3}' | cut -d '.' -f 1)
wget https://chromedriver.storage.googleapis.com/$CHROME_VERSION.0.0/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
chmod +x chromedriver
mv chromedriver /usr/local/bin/

# Install Python dependencies
pip install -r requirements.txt

# Run your script
python api/Data_Script/working.py 