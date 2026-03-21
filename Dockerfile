# Multi-stage build for Mirai
FROM node:22-slim AS dashboard-builder

WORKDIR /build/dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm install
COPY dashboard/ .
RUN npm run build

# Main image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl gnupg build-essential \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/Mirai

# Copy Python source
COPY cortex/ cortex/
COPY subconscious/ subconscious/
COPY install.sh .

# Copy pre-built dashboard
COPY --from=dashboard-builder /build/dashboard/dist/ dashboard/dist/

# Install Python dependencies
RUN pip install --no-cache-dir \
    playwright chromadb requests flask flask-cors flask-sock \
    openai python-dotenv mem0ai crawl4ai \
    e2b-code-interpreter crewai websocket-client

RUN playwright install --with-deps chromium

# Create non-root user
RUN useradd -m -s /bin/bash mirai_user
RUN chown -R mirai_user:mirai_user /app/Mirai
USER mirai_user

# Expose: Flask+Dashboard (5000), Cortex API (8100)
EXPOSE 5000 8100

# Default: start Flask (serves BI API + dashboard + WebSocket)
ENV FLASK_APP=subconscious/swarm/__init__.py:create_app
CMD ["python", "-m", "flask", "run", "--host", "0.0.0.0", "--port", "5000", "--with-threads"]
