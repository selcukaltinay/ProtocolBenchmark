#!/bin/bash

# Kullanım: ./setup_network.sh [Bant Genişliği] [Gecikme] [Jitter] [Paket Kaybı]
# Örnek: ./setup_network.sh 100kbit 100ms 20ms 5%

BW=${1:-100kbit}
DELAY=${2:-100ms}
JITTER=${3:-20ms}
LOSS=${4:-5%}

echo "=============================================="
echo "Ağ Simülasyonu Ayarlanıyor..."
echo "Bant Genişliği : $BW"
echo "Gecikme        : $DELAY"
echo "Jitter         : +/- $JITTER"
echo "Paket Kaybı    : $LOSS"
echo "=============================================="

echo "[node1] Trafik kontrol kuralları uygulanıyor..."

# Önce eski kuralları temizle
docker exec node1 tc qdisc del dev eth0 root 2>/dev/null || true
docker exec node2 tc qdisc del dev eth0 root 2>/dev/null || true

# Yeni kuralları ekle (netem ile gecikme/kayıp + tbf ile bant genişliği)
docker exec node1 tc qdisc add dev eth0 root netem delay $DELAY $JITTER loss $LOSS rate $BW
docker exec node2 tc qdisc add dev eth0 root netem delay $DELAY $JITTER loss $LOSS rate $BW

echo "[node1] Başarılı."
echo "[node2] Başarılı."
echo "=============================================="
echo "Ayarlar tamamlandı."
echo "Kontrol etmek için: docker exec node1 tc qdisc show dev eth0"
