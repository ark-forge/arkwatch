FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for msmtp (email sending)
RUN apt-get update && apt-get install -y --no-install-recommends \
    msmtp \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY run_api.py run_worker.py ./
COPY config/.env.example config/.env.example

# Create data and logs directories
RUN mkdir -p data logs

EXPOSE 8080

# Default: run the API server
CMD ["python", "run_api.py"]
