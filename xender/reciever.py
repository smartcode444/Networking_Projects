import socket
import asyncio 
import os

# selected_device = ""
devices = {}
# Create a signal to notify the background task when to stop
stop_signal = asyncio.Event()

# Constants
UDP_PORT = 5005
TCP_PORT = 8888
CLEAR_COMMAND = "cls" if os.name == "nt" else "clear"

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
        import tty, termios, sys
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
                    # connection.close() # No more data means the file is finished 
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
                    # server.close()
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
    loop = asyncio._get_running_loop()
    data, address = await loop.run_in_executor(None, server.recvfrom, 1024)
    # Recieve client_name and boradcast message "XENDER_DISCOVERY_REQUEST"
    username_len       = data[0]
    client_username    = data[1:1+username_len].decode('utf-8')
    client_msg         = data[1+username_len:].decode('utf-8')
  
    if client_msg == "XENDER_DISCOVERY_REQUEST" and client_username not in devices:
        # Send a I see you message so the the device can know if it should initiate its tcp server
        server.sendto(b"I_SEE_U", (address[0], UDP_PORT))
        return client_username, address
    return None, None
    # print(f"[UDP] Ignored duplicate request from {client_username}")

async def scanning_loop(server):
    """This run continously in the background"""
    global devices
    while not stop_signal.is_set():
        # Use asyncio.wait_for with a timeout to allow checking the signal
        try:
            client_name, address = await asyncio.wait_for(scan_devices(server), timeout=1.0)

            if client_name == None or address == None:
                continue

            devices[client_name] = address

            # Clear screen and update display
            clear_console()

            # Parse and process data
            print("Available devices: ")
            for username, addr in devices.items():
                print(f"{username} [addr: {addr}]")
            print("Stop scanning (y/n)?")

        except asyncio.TimeoutError:
            continue

        except OSError: # Socket closed
            break

async def input_loop():
    typed_text = "" 
    while True:
        # Oflload the blocking function to a seperate thread
        char = await asyncio.to_thread(get_single_char)
        if char in ('\r', '\n'):
            return typed_text
        elif char in ('\x08', '\x7f'):
            if len(typed_text) > 0:
                typed_text = typed_text[:-1]
                print('\b \b', end='', flush=True)
        else:
            typed_text += char
            print(char, end='', flush=True)


async def send(CLIENT_USERNAME):
    clear_console()
    selected_device = None

    # Create a UDP socket
    udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # Listen on all local network interfaces 5005
    udp_server.bind(('', UDP_PORT))
    udp_server.setblocking(False)
    print("Listening for nearby devices...")

    scan_task = asyncio.create_task(scanning_loop(udp_server))

    # Main loop waits for user input while scanning happens concurrently
    while True:
        choice = await input_loop()
        choice = choice.strip().lower()
        if choice in devices:
            selected_device = choice
            print(f"You have selected device: {selected_device}")
        
            stop_signal.set()
            udp_server.close()
            break
        else:
            continue

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
                tcp_server.close()

async def recieve(CLIENT_USERNAME):
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
    udp_server.settimeout(1.0)
    udp_server.setblocking(False)
    loop = asyncio.get_running_loop()

    # Shout to the whole network on a specific port 5005
    username_bytes = CLIENT_USERNAME.encode('utf-8')
    message = bytes([len(username_bytes)]) + username_bytes + b"XENDER_DISCOVERY_REQUEST"
    
    try: 
        while True:
            try:
                print("Broadcasting...")
                udp_server.sendto(message, ('255.255.255.255', UDP_PORT))
                # print("Broadcast message sent")

                data, address = await loop.sock_recvfrom(udp_server, 1024) 
                if data.decode('utf-8').strip() == "I_SEE_U":
                    choice = input(f"Accept connection from {address[0]}:{address[1]}(y/n)?")
                    if choice.strip().lower() == "y":
                        udp_server.close()
                        break
                    
            except socket.timeout:
                continue

    except KeyboardInterrupt:
        print("\n[*] Keyboard interrupt detected, Shutting down!")
        udp_server.close()
        return

    is_conn = False
    try:  
        print("Waiting for the sender to connect back...")
        while True:
            try:
                connection, sender_addr = tcp_server.accept()
                connection.settimeout(1.0)
                is_conn = True
                print(f"Connected to sender: {sender_addr[0]}:{sender_addr[1]}")

                # Send "mp4" file
                recieve_file(connection, "recieved.mp4")
                break

            except socket.timeout:
                # Timeout hit without a connection ; loop loop continues and checks 
                # for Ctrl + C
                continue

    except KeyboardInterrupt:
        print("\n[*] Keyboard interrupt detected, Shutting down!")

    finally:
        if is_conn:    
            # shutdown_server(connection)
            tcp_server.close()


# Will soon replace main
async def main():
    # global CLIENT_USERNAME
    print("Welcome to smartcode version of [Xender]")
    CLIENT_USERNAME = input("Enter username: ")
    print(f"Welcome {CLIENT_USERNAME}")
    print("[1]Send \n[2]Recieve \n[3]Close")
    while True:
        choice  = input(": ")
        if choice == "1":
            await send(CLIENT_USERNAME)
            break
        elif choice == "2":
            await recieve(CLIENT_USERNAME)
            break
        elif choice == "3":
            print("Thank you for using smart_xender!")
            break
        else:
            print("Invalid input, Try again")

if __name__ == "__main__":
    asyncio.run(main())
