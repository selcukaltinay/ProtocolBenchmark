import argparse
import time
import json
import threading
import socket
import asyncio
import logging
import sys
import os
import signal
import random
import string
import struct
from dataclasses import dataclass

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('pika').setLevel(logging.ERROR)
logging.getLogger('slixmpp').setLevel(logging.ERROR)

def generate_payload(size, seq):
    meta = json.dumps({"s": seq, "t": time.time()}).encode('utf-8')
    padding_size = size - len(meta)
    if padding_size < 0: padding_size = 0
    padding = ''.join(random.choices(string.ascii_letters, k=padding_size)).encode('utf-8')
    return meta + padding

def parse_payload(data):
    try:
        if isinstance(data, str): data = data.encode('utf-8')
        decoded = data.decode('utf-8', errors='ignore')
        json_end = decoded.find('}')
        if json_end != -1:
            json_str = decoded[:json_end+1]
            return json.loads(json_str)
    except Exception:
        pass
    return None

class MetricsCollector:
    def __init__(self):
        self.results = []
        self.seen_sequences = set()  # Duplicate detection
        import pandas as pd
        self.pd = pd

    def record(self, timestamp, seq):
        # Duplicate kontrolü - aynı sequence'i tekrar sayma
        if seq in self.seen_sequences:
            return  # Duplicate, kaydetme
        
        self.seen_sequences.add(seq)
        latency = (time.time() - timestamp) * 1000
        self.results.append({'t': timestamp, 's': seq, 'l': latency})

    def save_results(self, filename="results.json"):
        if not self.results: return
        df = self.pd.DataFrame(self.results)
        df.to_json(filename, orient="records")

# --- MQTT Implementation ---
class MQTTTester:
    def __init__(self, host, topic="test/topic"):
        import paho.mqtt.client as mqtt
        from paho.mqtt.enums import CallbackAPIVersion
        self.host = host
        self.topic = topic
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def start_receiver(self, collector):
        def on_message(client, userdata, msg):
            data = parse_payload(msg.payload)
            if data: collector.record(data['t'], data['s'])
        
        self.client.on_message = on_message
        self.client.connect(self.host, 1883, 60)
        self.client.subscribe(self.topic)
        self.client.loop_start()
        while True: time.sleep(1)

    def start_sender(self, size, rate, duration):
        self.client.connect(self.host, 1883, 60)
        self.client.loop_start()
        count = int(rate * duration)
        interval = 1.0 / rate
        for i in range(count):
            start_loop = time.time()
            self.client.publish(self.topic, generate_payload(size, i), qos=0)
            elapsed = time.time() - start_loop
            if interval > elapsed: time.sleep(interval - elapsed)
        time.sleep(2)
        self.client.loop_stop()

# --- CoAP Implementation ---
class CoAPTester:
    def __init__(self, host, mtype="CON"):
        self.host = host
        self.mtype = mtype
        # NON için farklı port kullan
        self.port = 5684 if mtype == "NON" else 5683

    async def run_server(self, collector):
        import aiocoap.resource as resource
        import aiocoap
        class CoAPResource(resource.Resource):
            def __init__(self, collector):
                super().__init__()
                self.collector = collector

            async def render_put(self, request):
                data = parse_payload(request.payload)
                if data: self.collector.record(data['t'], data['s'])
                return aiocoap.Message(code=aiocoap.CHANGED, payload=b"")

        root = resource.Site()
        root.add_resource(['data'], CoAPResource(collector))
        await aiocoap.Context.create_server_context(root, bind=('0.0.0.0', self.port))
        await asyncio.get_running_loop().create_future()

    def start_receiver(self, collector):
        asyncio.run(self.run_server(collector))

    def start_sender(self, size, rate, duration):
        import aiocoap

        async def send():
            context = await aiocoap.Context.create_client_context()
            count = int(rate * duration)
            interval = 1.0 / rate

            for i in range(count):
                start_loop = time.time()
                payload = generate_payload(size, i)

                # Yeni API: transport_tuning kullan
                if self.mtype == "CON":
                    request = aiocoap.Message(code=aiocoap.PUT, payload=payload,
                                            uri=f"coap://{self.host}:{self.port}/data")
                    request.opt.observe = None  # CON için
                else:
                    # NON için transport_tuning ayarla
                    request = aiocoap.Message(code=aiocoap.PUT, payload=payload,
                                            uri=f"coap://{self.host}:{self.port}/data")
                    # NON mesajlar için unreliable transport
                    request.mtype = aiocoap.NON

                try:
                    response = await context.request(request).response
                except Exception as e:
                    print(f"CoAP Error: {e}", flush=True)

                elapsed = time.time() - start_loop
                if interval > elapsed: await asyncio.sleep(interval - elapsed)

        asyncio.run(send())

# --- MQTT-SN Implementation (Simplified UDP) ---
class MQTTSNTester:
    def __init__(self, host, port=1884):
        self.host = host
        self.port = port

    def start_receiver(self, collector):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"MQTT-SN Receiver listening on port {self.port}", flush=True)
        self.sock.bind(('0.0.0.0', self.port))
        while True:
            data, addr = self.sock.recvfrom(4096)
            print(f"DEBUG: Data={data.hex()}", flush=True)
            if len(data) > 7:
                payload = data[7:]
                parsed = parse_payload(payload)
                if parsed: 
                    collector.record(parsed['t'], parsed['s'])

    def start_sender(self, size, rate, duration):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"MQTT-SN Sender starting to {self.host}:{self.port}", flush=True)
        try:
            self.sock.connect((self.host, self.port))
            self.sock.send(b'test')
        except Exception as e:
            print(f"Socket Error: {e}", flush=True)
            return
        
        count = int(rate * duration)
        interval = 1.0 / rate
        
        for i in range(count):
            start_loop = time.time()
            payload = generate_payload(size, i)
            msg_len = len(payload) + 7
            if msg_len < 256:
                header = struct.pack('!BBBHH', msg_len, 0x0C, 0x00, 0x0001, i % 65535)
                self.sock.sendto(header + payload, (self.host, self.port))
            else:
                header = struct.pack('!BHBBHH', 0x01, msg_len, 0x0C, 0x00, 0x0001, i % 65535)
                self.sock.sendto(header + payload, (self.host, self.port))
            
            elapsed = time.time() - start_loop
            if interval > elapsed: time.sleep(interval - elapsed)

# --- Zenoh Implementation ---
class ZenohTester:
    def __init__(self, key="demo/example"):
        import zenoh
        self.zenoh = zenoh
        self.key = key
        self.config = zenoh.Config()

    def start_receiver(self, collector):
        session = self.zenoh.open(self.config)
        def listener(sample):
            data = parse_payload(sample.payload.to_bytes())
            if data: collector.record(data['t'], data['s'])
        sub = session.declare_subscriber(self.key, listener)
        while True: time.sleep(1)

    def start_sender(self, size, rate, duration):
        session = self.zenoh.open(self.config)
        pub = session.declare_publisher(self.key)
        count = int(rate * duration)
        interval = 1.0 / rate
        for i in range(count):
            start_loop = time.time()
            pub.put(generate_payload(size, i))
            elapsed = time.time() - start_loop
            if interval > elapsed: time.sleep(interval - elapsed)
        time.sleep(2)
        session.close()

# --- HTTP Implementation ---
class HTTPTester:
    def __init__(self, host):
        from flask import Flask, request
        import requests
        self.host = host
        self.app = Flask(__name__)
        self.requests = requests
        self.request = request

    def start_receiver(self, collector):
        @self.app.route('/data', methods=['POST'])
        def receive():
            data = parse_payload(self.request.data)
            if data: collector.record(data['t'], data['s'])
            return "OK"
        self.app.run(host='0.0.0.0', port=8000)

    def start_sender(self, size, rate, duration):
        url = f"http://{self.host}:8000/data"
        count = int(rate * duration)
        interval = 1.0 / rate
        for i in range(count):
            start_loop = time.time()
            try:
                self.requests.post(url, data=generate_payload(size, i), timeout=5)
            except: pass
            elapsed = time.time() - start_loop
            if interval > elapsed: time.sleep(interval - elapsed)

# --- AMQP (RabbitMQ) Implementation ---
class AMQPTester:
    def __init__(self, host):
        import pika
        self.pika = pika
        self.host = host
        self.credentials = pika.PlainCredentials('test', 'test')
        self.params = pika.ConnectionParameters(host=self.host, credentials=self.credentials)

    def start_receiver(self, collector):
        connection = self.pika.BlockingConnection(self.params)
        channel = connection.channel()
        channel.queue_declare(queue='test_queue')

        def callback(ch, method, properties, body):
            data = parse_payload(body)
            if data: collector.record(data['t'], data['s'])

        channel.basic_consume(queue='test_queue', on_message_callback=callback, auto_ack=True)
        channel.start_consuming()

    def start_sender(self, size, rate, duration):
        connection = self.pika.BlockingConnection(self.params)
        channel = connection.channel()
        channel.queue_declare(queue='test_queue')

        count = int(rate * duration)
        interval = 1.0 / rate
        
        for i in range(count):
            start_loop = time.time()
            channel.basic_publish(exchange='', routing_key='test_queue', body=generate_payload(size, i))
            elapsed = time.time() - start_loop
            if interval > elapsed: time.sleep(interval - elapsed)
        
        connection.close()

# --- XMPP Implementation ---
class XMPPTester:
    def __init__(self, host):
        self.host = host
        print("XMPP is currently disabled due to library issues.", flush=True)

    def start_receiver(self, collector):
        print("XMPP Receiver disabled", flush=True)
        while True: time.sleep(1)

    def start_sender(self, size, rate, duration):
        print("XMPP Sender disabled", flush=True)
        time.sleep(duration)

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["sender", "receiver"], required=True)
    parser.add_argument("--proto", required=True)
    parser.add_argument("--host", default="node1")
    parser.add_argument("--size", type=int, default=128)
    parser.add_argument("--rate", type=float, default=1.0)
    parser.add_argument("--duration", type=int, default=10)
    
    args = parser.parse_args()
    print(f"Starting script with args: {args}", flush=True)

    global collector
    collector = MetricsCollector()
    import atexit
    atexit.register(collector.save_results)

    # Signal Handling
    def handle_exit(signum, frame):
        print(f"Received signal {signum}, saving results...", flush=True)
        sys.exit(0)
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    tester = None
    if args.proto == "mqtt": tester = MQTTTester(args.host)
    elif args.proto == "coap-con": tester = CoAPTester(args.host, mtype="CON")
    elif args.proto == "coap-non": tester = CoAPTester(args.host, mtype="NON")
    elif args.proto == "mqtt-sn": tester = MQTTSNTester(args.host)
    elif args.proto == "zenoh": tester = ZenohTester()
    elif args.proto == "http": tester = HTTPTester(args.host)
    elif args.proto == "amqp": tester = AMQPTester(args.host)
    elif args.proto == "xmpp": tester = XMPPTester(args.host)
    
    if tester:
        if args.mode == "receiver":
            tester.start_receiver(collector)
        else:
            tester.start_sender(args.size, args.rate, args.duration)
    else:
        print(f"Unknown protocol: {args.proto}")
