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

# Copy application code
COPY . .

# Create directories and set proper permissions
RUN mkdir -p static/uploads \
    && mkdir -p logs

# CREATE USER AND GROUP (ini yang hilang!)
RUN groupadd -r -g 1000 appgroup \
    && useradd -r -u 1000 -g appgroup -m -d /home/appuser -s /bin/bash appuser

# IMPORTANT: Set ownership BEFORE setting permissions
RUN chown -R appuser:appgroup /app

# Then set permissions
RUN chmod -R 755 /app \
    && chmod -R 777 /app/static \
    && chmod -R 777 /app/logs

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

RUN whoami \
    && ls -la /app \
    && touch /app/test_write_permission \
    && rm /app/test_write_permission

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]