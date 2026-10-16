FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (build tools and poppler/graphics libraries if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure storage directories exist
RUN mkdir -p storage/uploads storage/exports

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["python", "run.py"]
