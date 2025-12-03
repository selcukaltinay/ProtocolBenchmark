# XMPP Server Setup

## Overview
XMPP (Extensible Messaging and Presence Protocol) has been added to the benchmark framework using Ejabberd server.

## Architecture
```
Producer (node2) → XMPP Server (xmpp-server:5222) → Subscriber (node1)
```

## Setup Steps

### 1. Start the XMPP Server
```bash
docker-compose -f docker-compose-java.yml up -d xmpp-server
```

Wait for the server to start (about 10-15 seconds).

### 2. Register Users
```bash
./register_xmpp_users.sh
```

This will register:
- `producer@lpwan.local` (password: password)
- `subscriber@lpwan.local` (password: password)

### 3. Run Tests

Start subscriber (node1):
```bash
docker-compose -f docker-compose-java.yml run --rm node1 \
  java -jar /app/bench.jar subscriber xmpp xmpp-server
```

Start producer (node2):
```bash
docker-compose -f docker-compose-java.yml run --rm node2 \
  java -jar /app/bench.jar producer xmpp xmpp-server 100 10 30
```

Parameters:
- Protocol: `xmpp`
- Host: `xmpp-server` (always use this in Docker network)
- Size: Message size in bytes (e.g., 100)
- Rate: Messages per second (e.g., 10)
- Duration: Test duration in seconds (e.g., 30)

## Time Measurement

XMPP uses the same latency measurement as other protocols:

1. **Producer**: Embeds timestamp in payload at send time
2. **XMPP Server**: Routes message from producer to subscriber
3. **Subscriber**: Receives message and calculates latency = (receive_time - send_time)

This measures **end-to-end latency** including:
- Producer → Server network delay
- Server processing time
- Server → Subscriber network delay

## Configuration Files

- [docker-compose-java.yml](docker-compose-java.yml) - XMPP server service definition
- [xmpp_config/ejabberd.yml](xmpp_config/ejabberd.yml) - Ejabberd server configuration
- [register_xmpp_users.sh](register_xmpp_users.sh) - User registration script

## Server Management

Check server status:
```bash
docker exec xmpp-server ejabberdctl status
```

List registered users:
```bash
docker exec xmpp-server ejabberdctl registered_users lpwan.local
```

View server logs:
```bash
docker logs xmpp-server
```

Access web admin (optional):
```bash
http://localhost:5280/admin
```

## Protocol Comparison

| Protocol | Type | Server Required |
|----------|------|----------------|
| MQTT | Pub/Sub | Yes (Broker) |
| AMQP | Pub/Sub | Yes (Broker) |
| XMPP | Chat/Messaging | Yes (Server) |
| CoAP | Request/Response | No (Peer-to-peer) |
| Zenoh | Pub/Sub | No (can be P2P) |
| HTTP | Request/Response | Yes (Server) |

## Troubleshooting

If connection fails:
1. Check server is running: `docker ps | grep xmpp-server`
2. Check users are registered: `./register_xmpp_users.sh`
3. Check server logs: `docker logs xmpp-server`
4. Ensure containers are on same network: `docker network inspect lpwan_lpwan_net`
