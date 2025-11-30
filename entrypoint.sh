#!/bin/bash
# Servisleri başlat
# Mosquitto'yu özel konfigürasyonla başlat (Dış bağlantılara izin ver)
mosquitto -d -c /app/mosquitto.conf
service rabbitmq-server start
service prosody start

# XMPP Kullanıcılarını Kaydet (Servis başladıktan sonra)
sleep 2
prosodyctl register user1 localhost password
prosodyctl register user2 localhost password

# Konteynırı açık tut
tail -f /dev/null
