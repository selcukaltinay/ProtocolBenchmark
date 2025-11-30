#!/bin/bash

echo "=============================================="
echo "Bant Genişliği ve Bağlantı Testi (iperf3)"
echo "=============================================="

# Node1 üzerinde iperf3 sunucusunu arka planda başlat (eğer çalışmıyorsa)
if ! docker exec node1 pgrep -x "iperf3" > /dev/null; then
    echo "Node1 üzerinde iperf3 sunucusu başlatılıyor..."
    docker exec -d node1 iperf3 -s
else
    echo "Node1 üzerinde iperf3 sunucusu zaten çalışıyor."
fi

# Node2'den Node1'e test başlat
echo "Node2 -> Node1 testi başlatılıyor..."
echo "----------------------------------------------"
docker exec node2 iperf3 -c node1

echo "----------------------------------------------"
echo "Test tamamlandı."
