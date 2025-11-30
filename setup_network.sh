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

apply_tc() {
    CONTAINER=$1
    INTERFACE="eth0"

    echo "[$CONTAINER] Trafik kontrol kuralları uygulanıyor..."

    # Eski kuralları temizle
    docker exec $CONTAINER tc qdisc del dev $INTERFACE root 2>/dev/null

    # Yeni kuralları ekle (Netem)
    # rate: bant genişliği sınırlama
    # delay: gecikme ve jitter
    # loss: paket kaybı yüzdesi
    
    # Gecikme 0ms ise delay parametresini ekleme
    if [[ "$DELAY" == "0ms" ]]; then
        CMD="tc qdisc add dev $INTERFACE root netem loss $LOSS rate $BW"
    else
        CMD="tc qdisc add dev $INTERFACE root netem delay $DELAY $JITTER distribution normal loss $LOSS rate $BW"
    fi
    
    docker exec $CONTAINER $CMD

    if [ $? -eq 0 ]; then
        echo "[$CONTAINER] Başarılı."
    else
        echo "[$CONTAINER] HATA: Kurallar uygulanamadı."
    fi
}

# Her iki konteynır için de kuralları uygula (Giden trafik simülasyonu)
# İki tarafın da giden trafiğini kısıtladığımızda, toplam iletişim simüle edilmiş olur.
apply_tc node1
apply_tc node2

echo "=============================================="
echo "Ayarlar tamamlandı."
echo "Kontrol etmek için: docker exec node1 tc qdisc show dev eth0"
