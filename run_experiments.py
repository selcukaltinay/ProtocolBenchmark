import os
import time
import subprocess
import argparse
import json
import shutil
from concurrent.futures import ThreadPoolExecutor

# Test Edilecek Protokoller
PROTOCOLS = {
    "mqtt-qos0": {"args": ["producer", "mqtt", "node1", "{size}", "{rate}", "{duration}", "0"], "sub_args": ["subscriber", "mqtt", "node1", "0"]},
    "mqtt-qos1": {"args": ["producer", "mqtt", "node1", "{size}", "{rate}", "{duration}", "1"], "sub_args": ["subscriber", "mqtt", "node1", "1"]},
    "mqtt-qos2": {"args": ["producer", "mqtt", "node1", "{size}", "{rate}", "{duration}", "2"], "sub_args": ["subscriber", "mqtt", "node1", "2"]},
    "amqp-qos0": {"args": ["producer", "amqp", "node1", "{size}", "{rate}", "{duration}", "0"], "sub_args": ["subscriber", "amqp", "node1", "0"]},
    "amqp-qos1": {"args": ["producer", "amqp", "node1", "{size}", "{rate}", "{duration}", "1"], "sub_args": ["subscriber", "amqp", "node1", "1"]},
    "coap-con": {"args": ["producer", "coap", "node1", "{size}", "{rate}", "{duration}", "con"], "sub_args": ["subscriber", "coap", "node1"]},
    "coap-non": {"args": ["producer", "coap", "node1", "{size}", "{rate}", "{duration}", "non"], "sub_args": ["subscriber", "coap", "node1"]},
    "http": {"args": ["producer", "http", "node1", "{size}", "{rate}", "{duration}"], "sub_args": ["subscriber", "http", "node1"]},
    "xmpp-qos0": {"args": ["producer", "xmpp", "node1", "{size}", "{rate}", "{duration}", "0"], "sub_args": ["subscriber", "xmpp", "node1", "0"]},
    "xmpp-qos1": {"args": ["producer", "xmpp", "node1", "{size}", "{rate}", "{duration}", "1"], "sub_args": ["subscriber", "xmpp", "node1", "1"]},
    "xmpp-qos2": {"args": ["producer", "xmpp", "node1", "{size}", "{rate}", "{duration}", "2"], "sub_args": ["subscriber", "xmpp", "node1", "2"]},
    "zenoh-best-effort": {"args": ["producer", "zenoh", "node1", "{size}", "{rate}", "{duration}", "best-effort"], "sub_args": ["subscriber", "zenoh", "node1"]},
    "zenoh-reliable": {"args": ["producer", "zenoh", "node1", "{size}", "{rate}", "{duration}", "reliable"], "sub_args": ["subscriber", "zenoh", "node1"]}
}

PAYLOAD_SIZES = [16, 128]
RATES = [1, 10, 100]
BANDWIDTHS = ["50kbit", "100kbit", "250kbit", "1mbit"]
LOSS_RATES = ["0%", "1%", "5%", "10%"]
DELAYS = ["0ms", "20ms", "100ms", "500ms"]
DURATION = 10

def run_command(command, check=True):
    try:
        result = subprocess.run(command, shell=True, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing: {command}\n{e.stderr}")
        if check: raise
        return None

def setup_network_for_container(container_name, bw, loss, delay):
    try:
        run_command(f"docker exec {container_name} tc qdisc del dev eth0 root", check=False)
        cmd = f"docker exec {container_name} tc qdisc add dev eth0 root handle 1: netem delay {delay} loss {loss}"
        run_command(cmd)
        cmd = f"docker exec {container_name} tc qdisc add dev eth0 parent 1: handle 2: tbf rate {bw} burst 32kbit latency 400ms"
        run_command(cmd)
    except Exception as e:
        print(f"Network setup failed for {container_name}: {e}")

def worker(proto_name):
    safe_proto = proto_name.replace("-", "_")
    project_name = f"bench_{safe_proto}"
    
    print(f"[{proto_name}] Building and Starting Environment...")
    
    compose_cmd = f"PROTOCOL={proto_name} docker compose -p {project_name} -f docker-compose-java.yml"
    run_command(f"{compose_cmd} down -v", check=False)
    run_command(f"{compose_cmd} up -d --build")
    
    # Bekle ki servisler başlasın
    wait_time = 30 if "amqp" in proto_name else 10
    print(f"[{proto_name}] Waiting {wait_time}s for services to initialize...")
    time.sleep(wait_time)
    
    for size in PAYLOAD_SIZES:
        for rate in RATES:
            for bw in BANDWIDTHS:
                for loss in LOSS_RATES:
                    for delay in DELAYS:
                        if rate == 100 and bw == "50kbit": continue
                        
                        node1_name = f"{project_name}-node1-1"
                        node2_name = f"{project_name}-node2-1"
                        
                        # Network Setup
                        setup_network_for_container(node1_name, bw, loss, delay)
                        setup_network_for_container(node2_name, bw, loss, delay)
                        
                        # Prepare args
                        config = PROTOCOLS[proto_name]
                        prod_args = [arg.format(size=size, rate=rate, duration=DURATION) for arg in config["args"]]
                        sub_args = config["sub_args"]
                        
                        prod_cmd = "java -jar /app/bench.jar " + " ".join(prod_args)
                        sub_cmd = "java -jar /app/bench.jar " + " ".join(sub_args)
                        
                        # Start Subscriber
                        run_command(f"docker exec {node1_name} pkill -f 'java -jar'", check=False)
                        # Run subscriber in /tmp/{proto} to isolate results
                        run_command(f"docker exec {node1_name} mkdir -p /tmp/{safe_proto}")
                        
                        full_sub_cmd = f"cd /tmp/{safe_proto} && {sub_cmd}"
                        run_command(f"docker exec -d {node1_name} sh -c '{full_sub_cmd}'")
                        time.sleep(2)
                        
                        # Start Producer
                        prod_output = run_command(f"docker exec {node2_name} {prod_cmd}", check=False)
                        
                        actual_sent = int(rate * DURATION)
                        if prod_output:
                            for line in prod_output.splitlines():
                                if "BENCHMARK_SENT_COUNT:" in line:
                                    try:
                                        actual_sent = int(line.split(":")[1].strip())
                                    except:
                                        pass
                        
                        # Stop Subscriber
                        run_command(f"docker exec {node1_name} pkill -SIGTERM -f 'java -jar'", check=False)
                        time.sleep(1)
                        
                        # Collect Results
                        param_str = f"s{size}_r{rate}_bw{bw}_l{loss}_d{delay}"
                        temp_csv = f"results/temp_{safe_proto}_{param_str}.csv"
                        
                        try:
                            run_command(f"docker cp {node1_name}:/tmp/{safe_proto}/results.csv {temp_csv}", check=False)
                            
                            import pandas as pd
                            if os.path.exists(temp_csv) and os.path.getsize(temp_csv) > 0:
                                df = pd.read_csv(temp_csv)
                                expected_count = actual_sent
                                received_count = len(df)
                                delivery_ratio = (received_count / expected_count) * 100.0 if expected_count > 0 else 0
                                avg_latency = df['latency'].mean() if received_count > 0 else 0
                                throughput = (received_count * size * 8) / DURATION
                                jitter = df['latency'].std() if received_count > 1 else 0
                                
                                result_row = {
                                    "Protocol": proto_name,
                                    "Size": size,
                                    "Rate": rate,
                                    "Bandwidth": bw,
                                    "Loss": loss,
                                    "Delay": delay,
                                    "ConfigDelay_ms": int(delay.replace('ms', '')),
                                    "DeliveryRatio": delivery_ratio,
                                    "LatencyAvg_ms": avg_latency,
                                    "Jitter_ms": jitter,
                                    "Throughput_bps": throughput,
                                    "Timestamp": time.time()
                                }
                                
                                summary_file = f"results/results_{safe_proto}.csv"
                                summary_df = pd.DataFrame([result_row])
                                
                                if not os.path.exists(summary_file):
                                    summary_df.to_csv(summary_file, index=False)
                                else:
                                    summary_df.to_csv(summary_file, mode='a', header=False, index=False)
                                
                                os.remove(temp_csv)
                        except Exception as e:
                            print(f"[{proto_name}] Error processing: {e}")

if __name__ == "__main__":
    if not os.path.exists("results"):
        os.makedirs("results")
        
    with open("docker-compose-java.yml", "w") as f:
        f.write("""
services:
  node1:
    build: 
      context: ./java_bench
      dockerfile: Dockerfile
    cap_add:
      - NET_ADMIN
    environment:
      - PROTOCOL=${PROTOCOL}
    networks:
      - lpwan_net
    command: /app/entrypoint.sh

  node2:
    build:
      context: ./java_bench
      dockerfile: Dockerfile
    cap_add:
      - NET_ADMIN
    depends_on:
      - node1
    environment:
      - PROTOCOL=${PROTOCOL}
    networks:
      - lpwan_net
    command: /app/entrypoint.sh

networks:
  lpwan_net:
    driver: bridge
""")

    with ThreadPoolExecutor(max_workers=16) as executor:
        executor.map(worker, PROTOCOLS.keys())
