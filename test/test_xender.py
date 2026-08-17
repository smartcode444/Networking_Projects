import socket
import os 
import sys
import asyncio

# Get the directory of the current script (utils/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (my_project/)
parent_dir = os.path.dirname(current_dir)
# Add the parent directory to Python's search path
sys.path.append(parent_dir)
# Import from the folder using 'from folder.file import function'
from src.xender import XenderController


def log(message):
    print(message)

def key_pressed() -> str | None:
    """Return the character if a key was pressed, else None."""
    if os.name == 'nt':
        import msvcrt
        if msvcrt.kbhit():
            return msvcrt.getch().decode('utf-8', errors='ignore')
        return None
    else:
        # Unix
        import select, sys
        rlist, _, _ = select.select([sys.stdin], [], [], 0)
        if rlist:
            return sys.stdin.read(1)
        return None


PORT = 8888
IP = "127.0.0.1"

def listening_socket():
    # Create tcp socket, bind it and initiate a connection
    log("\n(LISTEN) Creating TCP socket")
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    log("(LISTEN) TCP socket created")
    log("(LISTEN) Binding TCP socket")
    tcp_socket.bind((IP, PORT))
    log("(LISTEN) TCP socket binded")
    log("(LISTEN) TCP socket listening...")
    tcp_socket.listen(1)
    tcp_client_socket, tcp_client_addr = tcp_socket.accept()
    log("\n(LISTEN) TCP socket connected")
    return tcp_client_socket

def connect_socket():
    # Create tcp socket, bind it and initiate a connection
    log("\n(ACCEPT) Creating TCP socket")
    tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    log("(ACCEPT) TCP socket created")
    log("(ACCEPT) Connecting to Listening socket...")
    tcp_client_socket.connect((IP, PORT))
    log("\n(ACCEPT) TCP socket connected")
    return tcp_client_socket

xender = XenderController("victor")

print("(1) Listening socket \n(2) Accepting socket \n(3) Exit")
while True:
    key = key_pressed()
    if key and key.lower()   == '1':
        xender.model.tcp_client_socket = listening_socket()
        break
    elif key and key.lower() == '2':
        xender.model.tcp_client_socket = connect_socket()
        break
    elif key and key.lower() == '3':
        sys.exit()

try:
    asyncio.run(xender.transfer_loop())
finally:
    if xender.model.tcp_client_socket:
        xender.model.tcp_client_socket.close()
    if xender.model.tcp_socket:
        xender.model.tcp_socket.close()
    if xender.model.udp_socket:
        xender.model.udp_socket.close()

