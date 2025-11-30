import os
import subprocess
import time
import json
import pandas as pd
import numpy as np

# Deney Parametreleri
PROTOCOLS = ["mqtt", "coap", "zenoh", "http", "amqp", "xmpp"]
PAYLOAD_SIZES = [16, 128, 1024]
RATES = [1, 10, 100]
BANDWIDTHS = ["50kbit", "100kbit", "250kbit", "1mbit", "0"] # 0 = unlimited
LOSSES = ["0%", "1%", "5%", "10%"]
DELAYS = [0, 20, 100, 500] # ms

DURATION = 10 # Her deneyin süresi (saniye)

RESULTS_FILE = "experiment_results.csv"

def run_command(cmd, check=True):
    subprocess.run(cmd, shell=True, check=check, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def setup_network(bw, loss, delay_ms):
    # Jitter = Gecikmenin %10'u
    jitter_ms = int(delay_ms * 0.1)
    
    delay_str = f"{delay_ms}ms"
    jitter_str = f"{jitter_ms}ms"
    
    if bw == "0":
        # Sınırsız: Kuralları temizle
        run_command("docker exec node1 tc qdisc del dev eth0 root 2>/dev/null || true")
        run_command("docker exec node2 tc qdisc del dev eth0 root 2>/dev/null || true")
    else:
        cmd = f"./setup_network.sh {bw} {delay_str} {jitter_str} {loss}"
        subprocess.run(cmd, shell=True)

def parse_results(container_path):
    # Konteynırdan sonuç dosyasını al
    local_path = "temp_results.json"
    try:
        run_command(f"docker cp node1:{container_path} {local_path}")
        
        with open(local_path, 'r') as f:
            data = json.load(f)
            
        if not data:
            return 0, 0, 0, 0
            
        df = pd.DataFrame(data)
        
        total_received = len(df)
        avg_latency = df['latency'].mean() * 1000 # ms
        jitter = df['latency'].std() * 1000 # ms
        
        return total_received, avg_latency, jitter
    except Exception as e:
        print(f"Error parsing results: {e}")
        return 0, 0, 0

def main():
    results = []
    
    print("Deney Başlıyor...")
    total_combinations = len(PROTOCOLS) * len(PAYLOAD_SIZES) * len(RATES) * len(BANDWIDTHS) * len(LOSSES) * len(DELAYS)
    print(f"Toplam Kombinasyon: {total_combinations}")
    
    # Konteynırları yeniden başlat (temiz başlangıç)
    print("Ortam hazırlanıyor...")
    run_command("docker compose down")
    run_command("docker compose up -d --build")
    time.sleep(5) # Servislerin açılması için bekle

    for proto in PROTOCOLS:
        for size in PAYLOAD_SIZES:
            for rate in RATES:
                for bw in BANDWIDTHS:
                    for loss in LOSSES:
                        for delay in DELAYS:
                            print(f"Running: Proto={proto}, Size={size}, Rate={rate}, BW={bw}, Loss={loss}, Delay={delay}ms")
                            
                            # 1. Ağı Ayarla
                            setup_network(bw, loss, delay)
                            
                            # 2. Node1'de Receiver Başlat (Arka planda)
                            # Önce eski processleri temizle (basitçe kill)
                            run_command("docker exec node1 pkill -f traffic_agent.py || true", check=False)
                            
                            # Receiver'ı başlat
                            # nohup ve & ile arka plana atıyoruz
                            receiver_cmd = f"docker exec -d node1 python3 traffic_agent.py --mode receiver --proto {proto}"
                            run_command(receiver_cmd)
                            time.sleep(2) # Receiver'ın hazır olması için bekle
                            
                            # 3. Node2'de Sender Başlat (Bloklayan işlem)
                            sender_cmd = f"docker exec node2 python3 traffic_agent.py --mode sender --proto {proto} --host node1 --size {size} --rate {rate} --duration {DURATION}"
                            try:
                                subprocess.run(sender_cmd, shell=True, check=True)
                            except subprocess.CalledProcessError:
                                print("Sender failed!")
                            
                            # 4. Receiver'ı Durdur ve Verileri Al
                            run_command("docker exec node1 pkill -SIGINT -f traffic_agent.py", check=False)
                            time.sleep(1) # Dosyayı yazması için bekle
                            
                            # 5. Sonuçları Analiz Et
                            # Sonuç dosyası node1 içinde /app/results.json (workdir /app olduğu için)
                            recv_count, latency, jitter = parse_results("/app/results.json")
                            
                            expected_count = rate * DURATION
                            delivery_ratio = (recv_count / expected_count) * 100 if expected_count > 0 else 0
                            throughput = (recv_count * size * 8) / DURATION # bps (Goodput)
                            
                            result_row = {
                                "Protocol": proto,
                                "Size": size,
                                "Rate": rate,
                                "Bandwidth": bw,
                                "Loss": loss,
                                "ConfigDelay_ms": delay,
                                "Sent": expected_count,
                                "Received": recv_count,
                                "DeliveryRatio": delivery_ratio,
                                "LatencyAvg_ms": latency,
                                "Jitter_ms": jitter,
                                "Throughput_bps": throughput
                            }
                            results.append(result_row)
                            print(f"Result: Delivery={delivery_ratio:.2f}%, Latency={latency:.2f}ms")
                            
                            # Her adımda CSV'yi güncelle (crash olursa veri kaybolmasın)
                            pd.DataFrame(results).to_csv(RESULTS_FILE, index=False)

    print("Tüm deneyler tamamlandı.")
    print(f"Sonuçlar {RESULTS_FILE} dosyasına kaydedildi.")

if __name__ == "__main__":
    main()
