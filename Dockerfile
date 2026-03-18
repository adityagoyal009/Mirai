# Use a lightweight Python base image
FROM python:3.10-slim

# Install system dependencies needed for Playwright (Browser hands)
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

# Set up the working directory inside the sandbox
WORKDIR /app/Mirai

# Copy the Mirai codebase into the sandbox
COPY . /app/Mirai/

# Install Python dependencies
# Core: Playwright, ChromaDB, requests, Flask
# New: mem0ai (hybrid memory), openbb (financial data), crawl4ai (fast extraction),
#      e2b-code-interpreter (sandbox), crewai (multi-agent)
RUN pip install --no-cache-dir \
    playwright \
    chromadb \
    requests \
    flask \
    flask-cors \
    openai \
    python-dotenv \
    mem0ai \
    openbb \
    crawl4ai \
    e2b-code-interpreter \
    crewai

RUN playwright install --with-deps chromium

# Create a non-root user so Mirai cannot destroy the container's core OS
RUN useradd -m -s /bin/bash mirai_user
RUN chown -R mirai_user:mirai_user /app/Mirai
USER mirai_user

# Expose ports: Cortex API (8100), MiroFish (5000), SearXNG (8888 if co-deployed)
EXPOSE 8100 5000

# The default command starts the Mirai Cortex
CMD ["python", "cortex/mirai_cortex.py"]
