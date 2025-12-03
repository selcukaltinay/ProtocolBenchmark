FROM maven:3.9-eclipse-temurin-11 AS build
WORKDIR /app
COPY pom.xml .
COPY settings.xml .
COPY src ./src
RUN mvn clean package -DskipTests -s settings.xml

FROM eclipse-temurin:11-jre
WORKDIR /app
COPY --from=build /app/target/protocol-benchmark-1.0-SNAPSHOT.jar /app/bench.jar

# Install networking tools
RUN apt-get update && apt-get install -y \
    iproute2 iputils-ping net-tools \
    mosquitto mosquitto-clients \
    rabbitmq-server \
    prosody \
    && rm -rf /var/lib/apt/lists/*

COPY config/mosquitto.conf /etc/mosquitto/mosquitto.conf

# Entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
