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

# Create non-root user early
RUN adduser --disabled-password --gecos '' --shell /bin/bash user

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Create logs directory with proper permissions BEFORE copying code
RUN mkdir -p logs \
    && touch logs/gov-auth-api.log \
    && chown -R user:user logs \
    && chmod 777 logs \
    && chmod 777 logs/gov-auth-api.log

# Copy application code and set ownership
COPY --chown=user:user . .

# Remove logs folder that might have been copied and recreate with correct permissions
RUN rm -rf logs \
    && mkdir -p logs \
    && mkdir -p static/uploads/evaluasi/{surat-tugas,surat-pemberitahuan,meetings/{entry,konfirmasi,exit},matriks,laporan-hasil,kuisioner,format-kuisioner} \
    && chown -R user:user /app \
    && chmod -R 755 /app \
    && chmod 777 logs 
    
RUN echo "DEBUG: Checking logs permissions:" \
    && ls -la logs \
    && whoami \
    && id

# Switch to non-root user
USER user

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "run.py"]