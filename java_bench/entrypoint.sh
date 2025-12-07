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
    mkdir -p /var/run/prosody
    chown prosody:prosody /var/run/prosody

    # Start Prosody properly using prosodyctl
    prosodyctl start

    # Wait for Prosody to be fully ready
    echo "Waiting for Prosody to start..."
    for i in {1..10}; do
        if prosodyctl status 2>&1 | grep -q "is running"; then
            echo "Prosody started successfully"
            break
        fi
        sleep 1
    done

    # Register users
    prosodyctl register subscriber lpwan.local password 2>/dev/null || echo "Subscriber already registered"
    prosodyctl register producer lpwan.local password 2>/dev/null || echo "Producer already registered"

    # Verify users
    echo "XMPP users registered. Checking status..."
    prosodyctl status
fi

# Sonsuz döngü (Container'ı ayakta tutmak için)
tail -f /dev/null
