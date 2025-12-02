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

# XMPP (Prosody) start
service prosody start

# XMPP Kullanıcılarını Kaydet (Servis başladıktan sonra)
sleep 2
prosodyctl register user1 localhost password
prosodyctl register user2 localhost password

# Konteynırı açık tut
tail -f /dev/null
