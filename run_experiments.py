import os
import subprocess
import time
import json
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Deney Parametreleri
PROTOCOLS = ["mqtt", "coap-con", "coap-non", "mqtt-sn", "zenoh", "http", "amqp", "xmpp"]
PAYLOAD_SIZES = [16, 128]
RATES = [1, 10, 100]
BANDWIDTHS = ["50kbit", "100kbit", "250kbit", "1mbit"]
LOSSES = ["0%", "1%", "5%", "10%"]
DELAYS = [0, 20, 100, 500] # ms
DURATION = 10 # Her deneyin süresi (saniye)
RESULTS_DIR = "results"  # Sonuçların kaydedileceği dizin
RESULTS_FILE = "experiment_results.csv"

def run_command(cmd, check=True):
    result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
    if result.stderr:
        print(f"STDERR: {result.stderr}", flush=True)
    return result

def setup_network(bw, loss, delay_ms):
    jitter_ms = int(delay_ms * 0.1)
    delay_str = f"{delay_ms}ms"
    jitter_str = f"{jitter_ms}ms"
    
    if bw == "0":
        run_command("docker exec node1 tc qdisc del dev eth0 root 2>/dev/null || true")
        run_command("docker exec node2 tc qdisc del dev eth0 root 2>/dev/null || true")
    else:
        cmd = f"./setup_network.sh {bw} {delay_str} {jitter_str} {loss}"
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def parse_results(json_file):
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        if not data:
            return 0, 0, 0
            
        latencies = [d['l'] for d in data]
        avg_latency = np.mean(latencies) if latencies else 0
        jitter = np.std(latencies) if latencies else 0
        received_count = len(data)
        
        return received_count, avg_latency, jitter
    except Exception as e:
        return 0, 0, 0

# Thread-safe lock for network configuration
network_lock = threading.Lock()

def run_protocol_tests(proto):
    """Run all tests for a single protocol"""
    print(f"[{proto}] Starting protocol tests...", flush=True)
    
    # Protokole özel sonuç dosyası
    safe_proto = proto.replace('-', '_')
    proto_file = os.path.join(RESULTS_DIR, f"results_{safe_proto}.csv")
    
    results = []
    if os.path.exists(proto_file):
        try:
            results = pd.read_csv(proto_file).to_dict('records')
        except: pass

    for size in PAYLOAD_SIZES:
        for rate in RATES:
            for bw in BANDWIDTHS:
                for loss in LOSSES:
                    for delay in DELAYS:
                        # Check if done
                        is_done = False
                        for r in results:
                            if (r['Protocol'] == proto and r['Size'] == size and 
                                r['Rate'] == rate and r['Bandwidth'] == bw and 
                                r['Loss'] == loss and r['ConfigDelay_ms'] == delay):
                                # Başarılıysa veya %100 kayıpsa atla
                                if r['DeliveryRatio'] > 0 or loss == "100%":
                                    is_done = True
                                break
                        
                        if is_done:
                            print(f"[{proto}] Skipping (Already done): Size={size}, Rate={rate}, BW={bw}, Loss={loss}, Delay={delay}ms")
                            continue
                            
                        print(f"[{proto}] Running: Size={size}, Rate={rate}, BW={bw}, Loss={loss}, Delay={delay}ms")
                        
                        # 1. Ağı Ayarla (thread-safe)
                        with network_lock:
                            setup_network(bw, loss, delay)
                            time.sleep(1)  # Ağ ayarlarının uygulanması için kısa bekleme
                        
                        # 2. Node1'de Receiver Başlat
                        # Sadece bu protokole ait processı öldür (proto marker kullanarak)
                        run_command(f"docker exec node1 pkill -f 'traffic_agent.py.*--proto {proto}' || true", check=False)
                        time.sleep(1)
                        
                        # Protokole özel script dosyaları (her protokol için farklı isim)
                        receiver_script_file = os.path.join(RESULTS_DIR, f"run_receiver_{safe_proto}.sh")
                        sender_script_file = os.path.join(RESULTS_DIR, f"run_sender_{safe_proto}.sh")
                        
                        receiver_script_content = f"python3 -u traffic_agent.py --mode receiver --proto {proto} > /tmp/agent_{safe_proto}.log 2>&1"
                        with open(receiver_script_file, "w") as f:
                            f.write(receiver_script_content)
                        os.chmod(receiver_script_file, 0o755)
                        
                        # Docker'a script dosyasının tam yolunu ver (volume mount ile /app altında)
                        script_name = f"run_receiver_{safe_proto}.sh"
                        run_command(f"docker exec -d node1 sh /app/{RESULTS_DIR}/{script_name}")
                        time.sleep(5) # Receiver'ın başlaması için bekle                        
                        
                        # 3. Node2'de Sender Başlat
                        sender_script_content = f"python3 -u traffic_agent.py --mode sender --proto {proto} --host node1 --size {size} --rate {rate} --duration {DURATION} > /tmp/sender_{safe_proto}.log 2>&1"
                        with open(sender_script_file, "w") as f:
                            f.write(sender_script_content)
                        os.chmod(sender_script_file, 0o755)
                        
                        script_name = f"run_sender_{safe_proto}.sh"
                        run_command(f"docker exec node2 sh /app/{RESULTS_DIR}/{script_name}", check=False)
                        
                        # 4. Receiver'ı Durdur (sadece bu protokole ait)
                        run_command(f"docker exec node1 pkill -SIGTERM -f 'traffic_agent.py.*--proto {proto}' || true", check=False)
                        time.sleep(2)
                        
                        # 5. Sonuçları Al (protokole özel dosya)
                        temp_results_file = os.path.join(RESULTS_DIR, f"temp_results_{safe_proto}.json")
                        if os.path.exists(temp_results_file): os.remove(temp_results_file)
                        run_command(f"docker cp node1:/app/results.json {temp_results_file}", check=False)
                        
                        # 6. Parse ve Kaydet
                        received_count, avg_latency, jitter = parse_results(temp_results_file)
                        
                        expected_count = rate * DURATION
                        delivery_ratio = (received_count / expected_count) * 100 if expected_count > 0 else 0
                        throughput = (received_count * size * 8) / DURATION
                        
                        result_row = {
                            "Protocol": proto,
                            "Size": size,
                            "Rate": rate,
                            "Bandwidth": bw,
                            "Loss": loss,
                            "ConfigDelay_ms": delay,
                            "Sent": expected_count,
                            "Received": received_count,
                            "DeliveryRatio": delivery_ratio,
                            "LatencyAvg_ms": avg_latency,
                            "Jitter_ms": jitter,
                            "Throughput_bps": throughput
                        }
                        
                        results.append(result_row)
                        print(f"[{proto}] Result: Delivery={delivery_ratio:.2f}%, Latency={avg_latency:.2f}ms")
                        
                        # Thread-safe dosya yazma
                        pd.DataFrame(results).to_csv(proto_file, index=False)
    
    print(f"[{proto}] Tamamlandı. Temizleniyor...")
    return proto

def main():
    print("Deney Başlıyor (Paralel Mod - Protokol Seviyesinde)...")
    
    # Results dizinini oluştur
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f"Sonuçlar '{RESULTS_DIR}/' dizinine kaydedilecek.")
    
    # Konteynırları başlat
    print("Ortam hazırlanıyor...")
    run_command("docker compose down")
    run_command("docker compose up -d --build")
    time.sleep(20) # Servislerin açılması için bekle
    
    # Paralel olarak tüm protokolleri test et
    print(f"Toplam {len(PROTOCOLS)} protokol paralel olarak test ediliyor...")
    
    with ThreadPoolExecutor(max_workers=len(PROTOCOLS)) as executor:
        # Her protokol için bir thread başlat
        future_to_proto = {executor.submit(run_protocol_tests, proto): proto for proto in PROTOCOLS}
        
        # Tamamlananları takip et
        for future in as_completed(future_to_proto):
            proto = future_to_proto[future]
            try:
                result = future.result()
                print(f"✓ [{proto}] Tüm testler tamamlandı!", flush=True)
            except Exception as exc:
                print(f"✗ [{proto}] Hata oluştu: {exc}", flush=True)

    print("Tüm deneyler tamamlandı.")

if __name__ == "__main__":
    main()
