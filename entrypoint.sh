#!/bin/bash
# Servisleri başlat
# Mosquitto'yu özel konfigürasyonla başlat (Dış bağlantılara izin ver)
mosquitto -d -c /app/mosquitto.conf
# AMQP (RabbitMQ)
service rabbitmq-server start
sleep 5
rabbitmqctl add_user test test 2>/dev/null || true
rabbitmqctl set_user_tags test administrator 2>/dev/null || true
rabbitmqctl set_permissions -p / test ".*" ".*" ".*" 2>/dev/null || true

# XMPP (Prosody) start - Ensure pidfile directory exists
mkdir -p /var/run/prosody
chown prosody:prosody /var/run/prosody

# Start Prosody in foreground mode first to ensure proper initialization
prosodyctl start

# XMPP Kullanıcılarını Kaydet (Servis başladıktan sonra) - FIX: Use lpwan.local domain!
sleep 3
prosodyctl register producer lpwan.local password 2>/dev/null || echo "Producer already registered"
prosodyctl register subscriber lpwan.local password 2>/dev/null || echo "Subscriber already registered"

# Konteynırı açık tut
tail -f /dev/null
