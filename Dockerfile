# Use a lightweight Python base image
FROM python:3.10-slim

# Install system dependencies needed for Playwright (Browser hands) and Node.js (OpenClaw)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    build-essential \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (needed for OpenClaw Gateway)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Set up the working directory inside the sandbox
WORKDIR /app/Mirai

# Copy the Mirai codebase into the sandbox
COPY . /app/Mirai/

# Install Python dependencies (Playwright, ChromaDB, requests, etc.)
RUN pip install --no-cache-dir playwright chromadb requests crewai
RUN playwright install --with-deps chromium

# We install OpenClaw globally inside the container
RUN npm install -g @openclaw/cli || echo "Will link local openclaw instead"

# Create a non-root user so Mirai cannot destroy the container's core OS
RUN useradd -m -s /bin/bash mirai_user
RUN chown -R mirai_user:mirai_user /app/Mirai
USER mirai_user

# The default command starts the Mirai Cortex
CMD ["python", "cortex/mirai_cortex.py"]
