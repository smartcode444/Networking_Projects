import socket
import asyncio

async def broadcast_msg(server):
    message = b"SENDER_DISCOVERY_REQUEST"
    while True:
        choice = input("Stop scanning (y/n)?")
        if choice in ["y", "Y"]:
            break
        # Shout to the whole network on a specific port 5005
        server.sendto(message, ('255.255.255.255', 5005))
        # Wait to hear a shout
        data, address = server.recvfrom(1024)
        print(f"Recieved message: {data} from IP: {address[0]}:{address[1]}")
        username = data
        devices[username] = address[0]

devices = {}

async def main():    
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Enable the socket to send broadcast messages
    server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    broadcast_task = asyncio.create_task(broadcast_msg())

    await broadcast_task

    while True:
        print(devices)
        await asyncio.sleep(2)

    server.close()

