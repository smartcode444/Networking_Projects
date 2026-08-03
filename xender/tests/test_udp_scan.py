import socket
from datetime import datetime
import time

def log(msg):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}")

UDP_PORT = 8888
recv_data = None

log("[SCAN] Creating UDP socket")
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
log("[SCAN] UDP socket Created")
udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
udp_socket.settimeout(10.0)
log("[SCAN] Binding UDP socket")
udp_socket.bind(('', UDP_PORT))
log("[SCAN] UDP socket binded")

log("[SCAN] Scanning for packets...\n")
while True:
    try:
        recv_data, addr = udp_socket.recvfrom(1024)
        print(f"[SCAN] Recieved raw data: {recv_data} from {addr[0]}:{addr[1]}")
        recv_data = recv_data.decode()
        print(f"[SCAN] Recieved data: {recv_data.decode('utf-8')} from {addr[0]}:{addr[1]}")
        break
    except socket.timeout:
        break

log("[SCAN] End of Scanning")
if not recv_data:
    log("[SCAN] No packet was found")

udp_socket.close()



