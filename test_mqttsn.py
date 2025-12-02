import socket
import sys
import time

if sys.argv[1] == 'receiver':
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', 1884))
    print("Listening", flush=True)
    while True:
        data, addr = s.recvfrom(1024)
        print(f"Got {data} from {addr}", flush=True)
else:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(b'test', ('node1', 1884))
    print("Sent", flush=True)
