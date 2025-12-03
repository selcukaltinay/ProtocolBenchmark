#!/bin/bash

# Servisleri Başlat (Protokole göre)
if [[ "$PROTOCOL" == mqtt* ]]; then
    echo "Starting Mosquitto..."
    /usr/sbin/mosquitto -c /etc/mosquitto/mosquitto.conf -d
elif [[ "$PROTOCOL" == amqp* ]]; then
    echo "Starting RabbitMQ..."
    rabbitmq-server -detached
    sleep 10
    rabbitmqctl add_user test test 2>/dev/null
    rabbitmqctl set_user_tags test administrator 2>/dev/null
    rabbitmqctl set_permissions -p / test ".*" ".*" ".*" 2>/dev/null
elif [[ "$PROTOCOL" == xmpp* ]]; then
    echo "Starting Prosody..."
    prosodyctl start
    sleep 5
    prosodyctl register subscriber lpwan.local password 2>/dev/null
    prosodyctl register producer lpwan.local password 2>/dev/null
fi

# Sonsuz döngü (Container'ı ayakta tutmak için)
tail -f /dev/null
