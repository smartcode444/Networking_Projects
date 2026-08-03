import socket
from datetime import datetime
import time

def log(msg):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}")

UDP_PORT = 8888
message = b"Message"

log("[BROADCAST] Creating UDP socket")
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
log("[BROADCAST] UDP socket created")
udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
udp_socket.settimeout(4.0)
log("[BROADCAST] Binding UDP socket")
udp_socket.bind(('', UDP_PORT))
log("[BROADCAST] UDP socket binded")

log("[BROADCAST] Broadcasting message...\n")
tries = 1
while tries <= 10:
    udp_socket.sendto(message, ("255.255.255.255", UDP_PORT))
    log("[BROADCAST] Message is broadcasted [" + str(tries) + "]")
    tries += 1
    time.sleep(1)

udp_socket.close()






