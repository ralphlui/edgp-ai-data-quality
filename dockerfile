# Use official Python image
FROM python:3.13.5-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy project files
COPY requirements.txt .
COPY . .

# Install system dependencies (build tools + lib for numpy/pandas/etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# No port needed since this is an SQS consumer
# EXPOSE removed

# Run the service
CMD ["python", "-m", "app.main"]
