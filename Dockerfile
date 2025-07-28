FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Create non-root user for security (do this early)
RUN adduser --disabled-password --gecos '' --shell /bin/bash miko

# Copy application code
COPY . .

# Create all necessary directories and set proper permissions
RUN mkdir -p static/uploads \
    && mkdir -p logs \
    # && chown -R miko:miko /app \
    # && chmod -R 755 /app \
    # && chmod -R 777 static/uploads \
    # && chmod -R 777 logs

# Switch to non-root user AFTER setting permissions
USER miko

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
# Production mode (no --reload)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]