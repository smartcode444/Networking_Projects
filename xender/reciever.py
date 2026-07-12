import socket
import asyncio 
import os

selected_device = ""
devices = {}
# Create a signal to notify the background task when to stop
stop_signal = asyncio.Event()

UDP_PORT = 5005
TCP_PORT = 8888
CLEAR_COMMAND = "cls" if os.name == "nt" else clear

def clear_console():
    """Clears the terminal screen."""
    os.system(CLEAR_COMMAND)

# Read a single character
def get_single_char():
    """Read a single character"""
    if os.name == "nt":
        import msvcrt
        return msvcrt.getch().decode('utf-8')
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

async def check_input():
    # Run blocking input a seperate thread to keep the loop free
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, "Stop scanning (y/n)?")

def recieve_file(connection, filename):
    try:
        # Open anew blank file to save the incoming data 
        with open(filename, "wb") as file:
            while True:
                # Read the incoming data in 4KB chunks
                chunk = connection.recv(4096)

                if not chunk:
                    connection.close() # No more data means the file is finished 
                    break 

                file.write(chunk)
            print(f"File {filename} recieved and saved successfully!")

    except KeyboardInterrupt:
        raise KeyboardInterrupt
            
    finally:
        print(f"Exiting recieve()")
        return


def send_file(server, filename):
    try:
        with open(filename, "rb") as file:
            while True:
                chunk = file.read(4096)

                if not chunk:
                    server.close()
                    break

                server.sendall(chunk)
            print(f"File: {filename} sent successfully!")

    except KeyboardInterrupt:
        raise KeyboardInterrupt

    finally:
        print(f"Exiting send()")
        return

def shutdown_server(server):
    server.close()
    print("TCP Server closed")

async def scan_devices(server):
    data, address = server.recvfrom(1024)
    # Recieve client_name and boradcast message "XENDER_DISCOVERY_REQUEST"
    client_username = data[0]
    client_msg      = data[1]
  a  # I have not decode the message
    if client_msg == "XENDER_DISCOVERY_REQUEST" and client_username not in devices:
        message = b"I_SEE_U"
        # Send a I see you message so the the device can know if it should initiate its tcp server
        server.sendto(message, (address[0], UDP_PORT))
    print(f"[UDP] Ignored duplicate request from {client_username}")

async def scanning_loop(server):
    """This run continously in tthe background"""
    while not stop_signal.is_set():
        client_name, address = await scan_devices(server)
        devices[client_name] = address

        # Clear screen and update display
        clear_console()
        print("Available devices: ")
        for username, addr in devices.items():
            print(f"{username} [addr: {addr}]")
        print("Stop scanning (y/n)?")

async def input_loop():
    typed_text = "" 
    while True:
        # Oflload the blocking function to a seperate thread
        char = await asyncio.to_thread(get_single_char)
        if char in ('\r', '\n'):
            break
        elif char in ('\x08', '\x7f'):
            if len(typed_text) > 0:
                typed_text = typed_text[:-1]
                print('\b \b', end='', flush=True)
        else:
            typed_text += char
            print(char, end='', flush=True)


async def send():
    clear_console()

    # Create a UDP socket
    udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Listen on all local network interfaces 5005
    udp_server.bind(('', UDP_PORT))
    print("Listening for nearby devices...")

    scan_task = asyncio.create_task(scanning_loop(udp_server))

    # Main loop waits for user input while scanning happens concurrently
    while True:
        choice = await input_loop()
        choice = choice.strip.lower()
        if choice in devices:
            selected_device = choice
            print(f"You have selected device: {selected_device}")
        
            # stop_signal.set()
            udp_server.close()
            break

    await scan_task

    if selected_device:
        selected_device_addr = devices[selected_device][0]
        # Create TCP Socket
        tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the port 8888 and start listening for connections
        print(f"Connecting to {selected_device}: {selected_device_addr}:{TCP_PORT}")
        tcp_server.settimeout(1.0) # Prevent accept()/recv() from blocking Ctrl + C indefinitely

        is_conn = False
        try:
            print(f"Waiting for the {selected_device} to connect back...")
            while True:
                try: 
                    # Accept the incoming connection from the sender
                    tcp_server.connect((selected_device_addr, TCP_PORT))
                    print(f"Connected to {selected_device}: {selected_device_addr}:{TCP_PORT}")
                    is_conn = True

                    # Send "mp4" file
                    filename = "recieved.mp4"
                    print(f"Sending filename to {selected_device}: {selected_device_addr}:{TCP_PORT}")
                    send_file(tcp_server, filename)
                    break

                except socket.timeout:
                    # Timeout hit without a connection ; loop loop continues and checks 
                    # for Ctrl + C
                    continue

        except KeyboardInterrupt:
            print("\n[*] Keyboard interrupt detected, Shutting down!")

        finally:
            if is_conn:    
                shutdown_server(tcp_server)

async def recieve():
    # Create TCP Socket
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the port 8888 and start listening for connections
    tcp_server.bind(('', TCP_PORT))
    tcp_server.listen(1)
    tcp_server.settimeout(1.0) # Prevent accept()/recv() from blocking Ctrl + C indefinitely
    print("TCP Server is ready and waiting...")


    # Create a UDP socket
    udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Enable the socket to send broadcast messages
    udp_server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # Shout to the whole network on a specific port 5005
    message = b"SENDER_DISCOVERY_REQUEST" # Change to sen
    
    while True:
        udp_server.sendto(message, ('255.255.255.255', UDP_PORT))
        print("Broadcast message sent")

        data, address = udp_server.recvfrom(1024)
        if data.decode('utf-8').strip == "I_SEE_U":
            choice = input(f"Aceept connection from {address[0]}:{address[1]}(y/n)?")
            if choice.strip().lower() == "y":
                udp_server.close()
                break

    is_conn = False
    try:
        print("Waiting for the sender to connect back...")
        while True:
            try:
                    
                # Accept the incoming connection from the sender
                connection, sender_addr = tcp_server.accept()
                is_conn = True
                print(f"Connected to sender: {sender_addr[0]}:{sender_addr[1]}")

                # Send "mp4" file
                send_file(connection, "recieved.mp4")
                break

            except socket.timeout:
                # Timeout hit without a connection ; loop loop continues and checks 
                # for Ctrl + C
                continue

    except KeyboardInterrupt:
        print("\n[*] Keyboard interrupt detected, Shutting down!")

    finally:
        if is_conn:    
            shutdown_server(connection)


# Will soon replace main

def main():
    # Create TCP Socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the port 8888 and start listening for connections
    server.bind(('', TCP_PORT))
    server.listen(1)
    server.settimeout(1.0) # Prevent accept()/recv() from blocking Ctrl + C indefinitely
    print("TCP Server is ready and waiting...")


    # Create a UDP socket
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Enable the socket to send broadcast messages
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # Shout to the whole network on a specific port 5005
    message = b"XENDER_DISCOVERY_REQUEST"
    client.sendto(message, ('255.255.255.255', UDP_PORT))
    print("Broadcast message sent")

    client.close()

    is_conn = False
    try:
        print("Waiting for the sender to connect back...")
        while True:
            try:
                    
                # Accept the incoming connection from the sender
                connection, sender_addr = server.accept()
                is_conn = True
                print(f"Connected to sender: {sender_addr[0]}:{sender_addr[1]}")

                # Send "mp4" file
                send_file(connection, "recieved.mp4")
                break

            except socket.timeout:
                # Timeout hit without a connection ; loop loop continues and checks 
                # for Ctrl + C
                continue

    except KeyboardInterrupt:
        print("\n[*] Keyboard interrupt detected, Shutting down!")

    finally:
        if is_conn:    
            shutdown_server(connection)

if __name__ == "__main__":
    main()
