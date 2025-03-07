FROM ubuntu:20.04  

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    postgresql-client \
    unzip \
    curl && \
    rm -rf /var/lib/apt/lists/*

RUN curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && \
    chmod +x mc && \
    mv mc /usr/local/bin/

RUN curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip && \
    apt-get install -y unzip && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws && \
    ln -s /usr/local/bin/aws /usr/bin/aws


RUN echo "export AWS_PAGER=''" >> /etc/profile       

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /app

ENTRYPOINT ["python3"]
CMD ["review.py"]
