FROM ubuntu:20.04  

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    postgresql-client \
    curl && \
    rm -rf /var/lib/apt/lists/*

RUN curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && \
    chmod +x mc && \
    mv mc /usr/local/bin/

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /app

ENTRYPOINT ["python3"]
CMD ["review.py"]
