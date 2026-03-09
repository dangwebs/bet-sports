FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (e.g., for compiled Python packages if needed)
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential git && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-worker.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements-worker.txt

# Copy source code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV RUN_ENV=docker

# Run the worker script
CMD ["python", "src/worker.py"]
