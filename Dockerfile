FROM python:3.11-slim

# Gerekli sistem araçlarını ve sunucuları yükle
# rabbitmq-server: AMQP Broker
# prosody: XMPP Server
# nginx: HTTP Server (Opsiyonel, Python server kullanacağız ama bulunsun)
# build-essential, cmake, git: FastDDS ve diğer derlemeler için
RUN apt-get update && apt-get install -y \
    iproute2 \
    iputils-ping \
    mosquitto \
    mosquitto-clients \
    rabbitmq-server \
    prosody \
    autoconf \
    automake \
    libtool \
    build-essential \
    pkg-config \
    procps \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python kütüphanelerini yükle
RUN pip install --no-cache-dir \
    paho-mqtt \
    aiocoap[all] \
    eclipse-zenoh \
    pandas \
    numpy \
    requests \
    flask \
    pika \
    slixmpp

# Çalışma dizini
WORKDIR /app

# Scriptleri kopyala
COPY traffic_agent.py /app/traffic_agent.py
COPY mosquitto.conf /app/mosquitto.conf
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Varsayılan komut
CMD ["/app/entrypoint.sh"]
