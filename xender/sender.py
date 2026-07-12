import socket

# Create a UDP socket
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Listen on all local network interfaces 5005
server.bind(('', 5005))
print("Listening for nearby devices...")

# Wait to hear a shout
data, address = server.recvfrom(1024)
print(f"Recieved message: {data} from IP: {address[0]}:{address[1]}")

server.close()

# Create
client = socket