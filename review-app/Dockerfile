FROM ubuntu:20.04  

# Install system dependencies, including PostgreSQL client
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    postgresql-client \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Install MinIO Client (mc)
RUN curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && \
    chmod +x mc && \
    mv mc /usr/local/bin/

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY . /app

# Set entrypoint and default command
ENTRYPOINT ["python3"]
CMD ["review.py"]
