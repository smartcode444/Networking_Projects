import socket
import asyncio
import tkinter as tk
from tkinter import filedialog
import os
from datetime import datetime
import netifaces


root = tk.Tk()
root.withdraw()


def log(msg):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}")

def get_broadcast_address():
#     for interface in netifaces.interfaces():
#         addrs = netifaces.ifaddresses(interface)
#         if netifaces.AF_INET in addrs:
#             for addr in addrs[netifaces.AF_INET]:
#                 ip = addr['addr']
#                 netmask = addr.get('netmask')
#                 broadcast = addr.get('broadcast')
#                 if broadcast and not ip.startswith('127.'):
#                     return broadcast
    return "255.255.255.255"  # fallback

def start_hotspot():
    """Starts hotspot on windows even when offline"""
    pass

def key_pressed() -> bool | str:
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

async def async_key_pressed() -> str | None:
    """Return the character if a key was pressed, else None."""
    if os.name == 'nt':
        import msvcrt
        while True:
            try:
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8', errors='ignore')
                    if key == 'q':
                        return 

                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise

    else:
        while True:
            try:
                # Unix
                import select, sys
                rlist, _, _ = select.select([sys.stdin], [], [], 0)
                if rlist:
                    key =  sys.stdin.read(1)
                    if key == 'q':
                        return 
                    await asyncio.sleep(0.1)
                return None
            except asyncio.CancelledError:
                raise

class NetworkManager:
    def __init__(self, username: str):
        self.UDP_PORT          = 7007
        self.TCP_PORT          = 5005
        # self.MY_IP             = "255.255.255.255"

        self.DISCOVERY_MESSAGE = "XENDER_DISCOVERY_REQUEST"
        self.RESPONSE_MESSAGE  = "I_SEE_U"

        self.name              = username

        self.tcp_socket        = None
        self.tcp_client_socket = None

        self.selected_mode     = None

        log("[SOCKET] Creating UDP socket...")
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        self.udp_socket.bind(('', self.UDP_PORT))
        log("[SOCKET] UDP socket created and running")

    def broadcast(self) -> bool:
        """Broadcast to sockets on the network"""
        self.selected_mode = "broadcast"
        log("[BROADCAST] Creating Listening TCP socket...")
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
        self.tcp_socket.bind(('', self.TCP_PORT))
        self.tcp_socket.listen(1)
        self.tcp_socket.settimeout(1.0) 
        log("[BROADCAST] Listening TCP socket up and ready")

        self.udp_socket.settimeout(1.0)
        try: 
            username_bytes = self.name.encode('utf-8')
            message = bytes([len(username_bytes)]) + username_bytes + b"XENDER_DISCOVERY_REQUEST"
            while True:
                try:
                    log("[BROADCAST] UDP socket broadcasting discovery message...")
                    self.udp_socket.sendto(message, (get_broadcast_address(), self.UDP_PORT))

                    log("[BROADCAST] UDP socket waiting for response...")
                    data, addr = self.udp_socket.recvfrom(1024)
                
                    if data.startswith(message):
                        continue

                    data = data.decode('utf-8').strip()
                    log("[BROADCAST] UDP socket recieved response: " + str(data) + " from " + str(addr[0]) + ":" + str(addr[1]))

                    if data[:7] == "I_SEE_U":
                        device_name = data[7:]
                        print(f"\nAccept connection from '{device_name}' \n[1] Yes \n[2] No")
                        key = key_pressed()
                        if key == "1":
                            print(f"Accepting connection from '{device_name}'...")
                            break
                        
                except socket.timeout:
                    continue

        except KeyboardInterrupt:
            print("\n")
            log("[BROADCAST] Keyboard Interrupt detected\n" \
                "[BROADCAST] Shutting down Listening TCP socket\n" \
                "[BROADCAST] Broadcasting operation terminated!")
            self.tcp_socket.close()
            return False

        try:  
            log("[BROADCAST] Listening TCP socket ...")
            while True:
                try:
                    self.tcp_client_socket, tcp_client_addr = self.tcp_socket.accept()
                    print(f"\nConnection from '{device_name}' accepted ")
                    self.tcp_socket.close()
                    return True

                except socket.timeout:
                    continue

        except KeyboardInterrupt:
            print("\n")
            log("[BROADCAST] Keyboard interrupt detected\n" \
                "[BROADCAST] Shutting down Listening TCP socket\n" \
                "[BROADCAST] Broadcasting operation terminated!")
            self.tcp_socket.close()
            return False
        
        except Exception as e:
            print("\n")
            log(f"[BROADCAST] An error occured {e} in broadcast()\n" \
                "[BROADCAST] Shutting down Listening TCP socket\n" \
                "[BROADCAST] Broadcasting operation terminated!")
            self.tcp_socket.close()
            return False
        

    def scan(self) -> dict:
        """Scan for devices on the network"""
        self.selected_mode = "scan"
        self.udp_socket.settimeout(1.0)
        log("[SCAN] Creating connecting TCP socket")
        self.tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        devices = {}

        try:
            while True:
                key = key_pressed()
                if key and key.lower() == 'q':
                    print("\nScanning stopped by user")
                    break
                
                try:
                    data, address      = self.udp_socket.recvfrom(1024)
                    username_len       = data[0]
                    client_name        = data[1:1+username_len].decode('utf-8')
                    client_msg         = data[1+username_len:].decode('utf-8')

                    # Debug
                    print(f"Address: {address}") 
                    print(f"Recieved data: {data}, client_name: {client_name}, client_msg: {client_msg}")
                    print(f"Found {len(devices)} devices")

                    msg = b"I_SEE_U" + self.name.encode('utf-8')
                    if client_msg == "XENDER_DISCOVERY_REQUEST" and client_name not in devices:
                        self.udp_socket.sendto(msg, (address))
                        devices[client_name] = address
                        print(f"Found {len(devices)} (press 'q' to stop scanning)")

                except socket.timeout:
                    continue

        except KeyboardInterrupt:
            print("\n[*] Keyboard interrupt detected, Scanning operation terminated!")

        except Exception as e:
            print(f"An error occured {e} in scan(), Scanning operation terminated!")
            
        return devices

    def connect(self, device_addr, device_name) -> bool:
        
        print(f"Connecting to {device_name}")

        while True:
            try:
                self.tcp_client_socket.settimeout(1.0)
                self.tcp_client_socket.connect((device_addr, self.TCP_PORT))
                print(f"Succesfully connected to {device_name}")
                return True

            except socket.timeout:
                # print("20s has elapsed")
                continue

            except Exception as e:
                print(f"An error occured in {e} connect()")
                return False

    # @classmethod
    def _send_end(self):
        """Send END command"""
        # Send a command byte: 0x02 means END
        self.tcp_client_socket.send(b'\x02')
    

    def _send_file(self, name, path):
        """Send file"""
        # Send command: 0x01 = file transfer
        self.tcp_client_socket.send(b'\x01')
        
        # Send filename length (4 bytes, big‑endian) and filename
        name_bytes = name.encode('utf-8')
        self.tcp_client_socket.send(len(name_bytes).to_bytes(4, 'big') + name_bytes)

        # Send file name         
        file_size = os.path.getsize(path)
        self.tcp_client_socket.send(file_size.to_bytes(4, 'big'))

        # Send file data
        # print(f"Sending {name}...")
        try:
            with open(path, "rb") as file:
                sent = 0
                while sent < file_size:
                    chunk = file.read(4096)
                    if not chunk:
                        break
                    self.tcp_client_socket.sendall(chunk)
                    sent += len(chunk)
                print(f"File: {name} sent successfully!")

        except KeyboardInterrupt:
            raise KeyboardInterrupt
        
        except Exception:
            raise Exception

    def recv_bytes(self, no_bytes):
        return self.tcp_client_socket.recv(no_bytes)

    def send_bytes(self, bytes):
        return self.tcp_client_socket.send(bytes)
    
    async def _recieve_file(self, dest_folder):
        """Recieve files"""
        try:
            while True:
                cmd = self.recv_bytes(1)
                if not cmd:
                    return "Connection closed by Sender"
                # if cmd   == b'\x02':   # END Command          # Add socket timeout retry logic
                #     return "Transfer complete."
                elif cmd == b'\x01':   # File transfer
                    length_data = self.recv_bytes(4)
                    if len(length_data) < 4:
                        raise RuntimeError("Failed to read filename length")
                    name_len = int.from_bytes(length_data, 'big')

                    # Read filename 
                    name_bytes = b''
                    while len(name_bytes) < name_len:
                        chunk = self.recv_bytes(name_len - len(name_bytes))
                        if not chunk:
                            raise RuntimeError("Connection lost while reading filename")
                        name_bytes += chunk
                    filename = name_bytes.decode('utf-8')

                    # Read file size 
                    size_data = self.recv_bytes(4)
                    if len(size_data) < 4:
                        raise RuntimeError("Failed to read file size")
                    file_size = int.from_bytes(size_data, 'big')

                    # Recieve file
                    print(f"Recieving {filename} ({file_size/(1024*1024):.2f} MB)....") 
                    with open(dest_folder + '/' +  filename, "wb") as file:
                        recieved = 0
                        while recieved < file_size:
                            chunk = self.recv_bytes(min(4096, file_size-recieved))
                            if not chunk:
                                break
                            file.write(chunk)
                            recieved += len(chunk)
                    return f"File {filename} recieved"
                else:
                    return f"Unknown command: {cmd}"

        except asyncio.CancelledError:
            return f"Recieving {filename} was cancelled by user"
            raise
        
            

class ConsoleView:
    @staticmethod
    def show_menu():
        print("\n[1] Scan \n[2] Broadcast \n[3] Exit")
        while True:
            key = key_pressed()
            if key:
                return key

    @staticmethod
    def show_devices(devices):
        if not devices:
            print("No devices found.")
            return
        for idx, (name, addr) in enumerate(devices.items(), 1):
            print(f"[{idx}] {name} - {addr[0]}:{addr[1]}")

    @staticmethod
    def get_selection(max_num):
        while True:
            try:
                key = key_pressed()
                if key:
                    sel = int(key)
                    if 1 <= sel <= max_num:
                        return sel
            except ValueError:
                continue

    @staticmethod
    def ask_yes_no(prompt):
        print(f"{prompt} \n[1] Yes \n[2] No")
        while True:
            key = key_pressed()
            if key:
                return key

    @staticmethod
    def show_message(msg):
        print(msg)

class XenderController():
    def __init__(self, username):
        self.model = NetworkManager(username)
        self.view = ConsoleView()
        self.running = True

    async def run(self):
        while self.running:
            choice = self.view.show_menu()
            print(choice)
            if choice == '1':
                self.view.show_message("\nScanning for devices... (press 'q' to stop)")
                devices = self.model.scan()
                self.view.show_devices(devices)
                if devices:
                    idx = self.view.get_selection(len(devices))
                    selected_name = list(devices.keys())[idx-1]
                    if self.model.connect(devices[selected_name][0], selected_name):
                        self.view.show_message(f"Connected to {selected_name}")
                        self.transfer_loop()
                else:
                    self.view.show_message("No devices found.")
            elif choice and choice == '2':
                if self.model.broadcast():
                    self.view.show_message("Connected to a device.")
                    self.transfer_loop()
            elif choice and choice == '3':
                self.view.show_message("Goodbye!")
                self.running = False
                self.model.udp_socket.close()

                # if hasattr(self.model, "tcp_client_socket"):
                #     self.model.tcp_client_socket.close()
                if self.model.tcp_client_socket:
                    self.model.tcp_client_socket.close()
                break

    def try_send(self):
            """Send files"""
            file_paths = filedialog.askopenfiles(
                title="Xender -> Select files",
            )
            if not file_paths:
                self.view.show_message("No files selected.")
                return

            # Cannot send more than 99 files
            no_files = str(len(file_paths)).encode('utf-8')
            self.model.send_bytes(no_files)
            
            for file_obj in file_paths:
                name = os.path.basename(file_obj.name)
                path = file_obj.name
                try:
                    self.view.show_message(f"Sending {name}...")
                    self.model._send_file(name, path)
                except KeyboardInterrupt:
                    self.view.show_message(f"[*] Keyboard Interrupt detected, Transfer of {name} is terminated")
                    continue
                except Exception as e:
                    self.view.show_message(f"Error sending {name}: {e}")
            # self.model._send_end()

    async def try_recieve(self):
        """Recieve files"""
        # Prompt user for destination folder
        dest_folder = filedialog.askdirectory(title="Select destination folder")
        if dest_folder:
            self.view.show_message(f"Destination folder {dest_folder}")
        else:
            self.view.show_message(f"Invalid Destination folder")
        # Recieve the number of files to recieve
        bytes = self.model.recv_bytes(2)
        no_files_to_recieve = int(bytes.decode('utf-8'))
        files_recieved = 0
        while files_recieved < no_files_to_recieve:
            files_recieved += 1 
            try:
                self.view.show_message(f"\nRecieving file {files_recieved}/{no_files_to_recieve}... (press 'q' to stop)")
                recv_file = asyncio.create_task(self.model._recieve_file(dest_folder))
                pressed_key = asyncio.create_task(async_key_pressed())
                # self.view.show_message(self._recieve_file(dest_folder))

                done, pending = await asyncio.wait(
                    {recv_file, pressed_key}, 
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()

                if recv_file in done:
                    result = recv_file.result()
                    self.view.show_message(f"{result}")
                    
                elif key_pressed in done:
                    self.view.show_message("Recieving stopped by user.")

            except Exception as e:
                self.view.show_message(f"Error: {e}")

            

    async def transfer_loop(self):
        """Transfer files"""
        while True:
            self.view.show_message("\n[1] Send files \n[2] Recieve files \n[3] Back to main")
            sel = self.view.get_selection(3)
            if   sel == 1:
                self.try_send()
            elif sel == 2:
                await self.try_recieve()
            elif sel == 3:
                break


if __name__ == "__main__":
    print("Welcome smartcode!")
    xender = XenderController("smartcode")
    asyncio.run(xender.run())