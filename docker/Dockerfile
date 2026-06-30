# ORION System - Production Dockerfile
# Multi-stage build for optimized production deployment

# Stage 1: Build stage
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production stage
FROM python:3.12-slim AS production

# Security: non-root user
RUN groupadd -r orion && useradd -r -g orion -d /app orion

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/orion/.local

# Copy application code
COPY --chown=orion:orion . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R orion:orion /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/orion/.local/bin:$PATH \
    ORION_ENV=production \
    ORION_LOG_LEVEL=INFO

# Switch to non-root user
USER orion

# Expose ports
EXPOSE 8000 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command
CMD ["python", "-m", "orion.server"]
