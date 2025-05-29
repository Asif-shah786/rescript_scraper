FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libdrm2 \
    fonts-liberation \
    libgbm1 \
    xvfb \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Verify Chrome installation
RUN google-chrome --version

# Install ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | awk '{ print $3 }' | cut -d '.' -f 1) && \
    echo "Chrome version: $CHROME_VERSION" && \
    DRIVER_VERSION=$(curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION) && \
    echo "ChromeDriver version: $DRIVER_VERSION" && \
    wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$DRIVER_VERSION/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver.zip

# Verify ChromeDriver installation
RUN chromedriver --version

# Set display port to avoid crash
ENV DISPLAY=:99

# Set up working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a script to verify the installation
RUN echo '#!/bin/bash\n\
    echo "Chrome version:"\n\
    google-chrome --version\n\
    echo "ChromeDriver version:"\n\
    chromedriver --version\n\
    echo "Chrome binary location:"\n\
    which google-chrome\n\
    echo "ChromeDriver location:"\n\
    which chromedriver\n\
    echo "Listing /usr/local/bin:"\n\
    ls -la /usr/local/bin\n\
    ' > /app/verify.sh && chmod +x /app/verify.sh

# Start Xvfb and run the application
CMD Xvfb :99 -screen 0 1024x768x16 & ./verify.sh && python api/main.py 