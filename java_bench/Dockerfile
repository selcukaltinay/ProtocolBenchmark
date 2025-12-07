FROM eclipse-temurin:11-jre
WORKDIR /app

# Copy pre-built JAR instead of building inside Docker
COPY target/protocol-benchmark-1.0-SNAPSHOT.jar /app/bench.jar

# Install networking tools
RUN apt-get update && apt-get install -y \
    iproute2 iputils-ping net-tools \
    mosquitto mosquitto-clients \
    rabbitmq-server \
    prosody \
    && rm -rf /var/lib/apt/lists/*

COPY config/mosquitto.conf /etc/mosquitto/mosquitto.conf
COPY config/prosody.cfg.lua /etc/prosody/prosody.cfg.lua
RUN chown root:prosody /etc/prosody/prosody.cfg.lua && chmod 640 /etc/prosody/prosody.cfg.lua

# Entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
