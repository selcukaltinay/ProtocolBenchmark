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
import subprocess
from dataclasses import dataclass

# Protokol Kütüphaneleri
import paho.mqtt.client as mqtt
import aiocoap
import aiocoap.resource as resource
import zenoh
import requests
from flask import Flask, request
import pika
import slixmpp

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
        self.received_packets = []
        self.lock = threading.Lock()

    def record(self, send_time, seq):
        recv_time = time.time()
        with self.lock:
            self.received_packets.append({
                "seq": seq,
                "send_time": send_time,
                "recv_time": recv_time,
                "latency": recv_time - send_time
            })

    def save_results(self, filename="results.json"):
        with self.lock:
            with open(filename, 'w') as f:
                json.dump(self.received_packets, f)

# --- MQTT Implementation ---
class MQTTTester:
    def __init__(self, host, topic="test/topic"):
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
class CoAPResource(resource.Resource):
    def __init__(self, collector):
        super().__init__()
        self.collector = collector

    async def render_put(self, request):
        data = parse_payload(request.payload)
        if data: self.collector.record(data['t'], data['s'])
        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"")

class CoAPTester:
    def __init__(self, host):
        self.host = host

    def start_receiver(self, collector):
        root = resource.Site()
        root.add_resource(['data'], CoAPResource(collector))
        asyncio.get_event_loop().create_task(aiocoap.Context.create_server_context(root))
        asyncio.get_event_loop().run_forever()

    def start_sender(self, size, rate, duration):
        async def send_loop():
            context = await aiocoap.Context.create_client_context()
            count = int(rate * duration)
            interval = 1.0 / rate
            for i in range(count):
                start_loop = time.time()
                payload = generate_payload(size, i)
                request = aiocoap.Message(code=aiocoap.PUT, payload=payload, uri=f"coap://{self.host}/data")
                asyncio.create_task(context.request(request).response)
                elapsed = time.time() - start_loop
                if interval > elapsed: await asyncio.sleep(interval - elapsed)
            await asyncio.sleep(2)
        asyncio.get_event_loop().run_until_complete(send_loop())

# --- Zenoh Implementation ---
class ZenohTester:
    def __init__(self, key="demo/example"):
        self.key = key
        self.config = zenoh.Config()

    def start_receiver(self, collector):
        session = zenoh.open(self.config)
        def listener(sample):
            data = parse_payload(sample.payload.to_bytes())
            if data: collector.record(data['t'], data['s'])
        sub = session.declare_subscriber(self.key, listener)
        while True: time.sleep(1)

    def start_sender(self, size, rate, duration):
        session = zenoh.open(self.config)
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
        self.host = host
        self.app = Flask(__name__)

    def start_receiver(self, collector):
        @self.app.route('/data', methods=['POST'])
        def receive():
            data = parse_payload(request.data)
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
                requests.post(url, data=generate_payload(size, i))
            except: pass
            elapsed = time.time() - start_loop
            if interval > elapsed: time.sleep(interval - elapsed)

# --- AMQP (RabbitMQ) Implementation ---
class AMQPTester:
    def __init__(self, host):
        self.host = host
        self.queue = 'test_queue'

    def start_receiver(self, collector):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        channel = connection.channel()
        channel.queue_declare(queue=self.queue)

        def callback(ch, method, properties, body):
            data = parse_payload(body)
            if data: collector.record(data['t'], data['s'])

        channel.basic_consume(queue=self.queue, on_message_callback=callback, auto_ack=True)
        channel.start_consuming()

    def start_sender(self, size, rate, duration):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        channel = connection.channel()
        channel.queue_declare(queue=self.queue)
        
        count = int(rate * duration)
        interval = 1.0 / rate
        for i in range(count):
            start_loop = time.time()
            channel.basic_publish(exchange='', routing_key=self.queue, body=generate_payload(size, i))
            elapsed = time.time() - start_loop
            if interval > elapsed: time.sleep(interval - elapsed)
        time.sleep(2)
        connection.close()

# --- XMPP Implementation ---
class XMPPClient(slixmpp.ClientXMPP):
    def __init__(self, jid, password, collector=None, target=None):
        super().__init__(jid, password)
        self.collector = collector
        self.target = target
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)

    def start(self, event):
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            if self.collector:
                data = parse_payload(msg['body'].encode('utf-8'))
                if data: self.collector.record(data['t'], data['s'])

class XMPPTester:
    def __init__(self, host):
        self.host = host
        self.domain = "localhost" 

    def start_receiver(self, collector):
        xmpp = XMPPClient(f"user1@{self.domain}", "password", collector=collector)
        xmpp.connect((self.host, 5222))
        xmpp.process(forever=True)

    def start_sender(self, size, rate, duration):
        xmpp = XMPPClient(f"user2@{self.domain}", "password", target=f"user1@{self.domain}")
        xmpp.connect((self.host, 5222))
        xmpp.process(block=False)
        time.sleep(2)
        
        count = int(rate * duration)
        interval = 1.0 / rate
        for i in range(count):
            start_loop = time.time()
            payload = generate_payload(size, i).decode('utf-8')
            xmpp.send_message(mto=f"user1@{self.domain}", mbody=payload, mtype='chat')
            elapsed = time.time() - start_loop
            if interval > elapsed: time.sleep(interval - elapsed)
        time.sleep(2)
        xmpp.disconnect()

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

    global collector
    collector = MetricsCollector()

    def handle_exit(signum, frame):
        if args.mode == "receiver":
            collector.save_results()
        sys.exit(0)
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    # Service Startup handled by entrypoint.sh

    tester = None
    if args.proto == "mqtt": tester = MQTTTester(args.host)
    elif args.proto == "coap": tester = CoAPTester(args.host)
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
