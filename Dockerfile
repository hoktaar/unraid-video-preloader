FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install build dependencies (needed for some packages on arm64)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app /app/app
COPY templates /app/templates

# Create config directory (volume mount point)
RUN mkdir -p /config

# Expose port
EXPOSE 8000

# Healthcheck für Container-Monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/stats')" || exit 1

# Run command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]