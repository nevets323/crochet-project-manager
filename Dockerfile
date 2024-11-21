FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN set -eux; \
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        gcc \
        gnupg \
        ca-certificates \
    ; \
    rm -rf /var/lib/apt/lists/*; \
    mkdir -p /etc/apt/keyrings; \
    apt-get clean

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create upload directory
RUN mkdir -p static/uploads

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose port
EXPOSE 5000

# Create startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Run the application
CMD ["/app/start.sh"]