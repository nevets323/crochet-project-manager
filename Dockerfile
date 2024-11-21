FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --fix-missing && \
    apt-get install -y \
    gcc \
    wget \
    gnupg && \
    # Add Debian repository keys
    wget --no-check-certificate https://packages.debian.org/bookworm/amd64/debian-archive-keyring/download -O /usr/share/keyrings/debian-archive-keyring.gpg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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