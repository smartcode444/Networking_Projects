"""
███████╗███████╗███╗   ██╗███████╗███████╗███████╗
    ██╔╝██╔════╝████╗  ██║██╔══██╗██╔════╝██╔══██╗
   ██╔╝ █████╗  ██╔██╗ ██║██║  ██║█████╗  ██████╔╝
  ██╔╝  ██╔══╝  ██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗
███████╗███████╗██║ ╚████║███████╗███████╗██║  ██║
╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝  ╚═╝
"""

import socket
import asyncio
import tkinter as tk
import os, sys
import netifaces
import logging
from . import WHconn
from . import hotspot
# from color import fg, bg
from tkinter import filedialog
from datetime import datetime


root = tk.Tk()
root.withdraw()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("zender.log"), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Zender")

# logger.info("This is a info message")
# logger.debug("This is a debug message")
# logger.warning("This is a warning message")
# logger.error("This is a error message")

def log(msg):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}")

def get_broadcast_address():
    for interface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                ip = addr['addr']
                netmask = addr.get('netmask')
                broadcast = addr.get('broadcast')
                if broadcast and not ip.startswith('127.'):
                    return broadcast
    return "255.255.255.255"  # fallback


def key_pressed() -> bool | str:
    """Return the character if a key was pressed, else None."""
    try:
        if os.name == 'nt':
            import msvcrt
            if msvcrt.kbhit():
                return msvcrt.getch().decode('utf-8', errors='ignore')
            return None
        else:
            # Unix
            import select
            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                return sys.stdin.read(1)
            return None
        
    except KeyboardInterrupt:
        return None

async def async_key_pressed() -> str | None:
    """Return the character if a key was pressed, else None."""
    try:
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

    except KeyboardInterrupt:
            return None

class NetworkManager:
    def __init__(self, username: str):
        self.UDP_PORT          = 7007
        self.TCP_PORT          = 5005
        self.CTRL_PORT         = 500
        # self.MY_IP             = "255.255.255.255"

        self.DISCOVERY_MESSAGE = "XENDER_DISCOVERY_REQUEST"
        self.RESPONSE_MESSAGE  = "I_SEE_U"

        self.name              = username

        self.tcp_socket        = None
        self.tcp_client_socket = None
        self.ctrl_socket       = None # accepted from broadcaster side
        self.ctrl_conn         = None # connected from scanner side

        self.selected_mode     = None

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        self.udp_socket.bind(('', self.UDP_PORT))
        self.udp_socket.settimeout(1.0)

    def init_bd_socks(self) -> bool:
        """Intialize sockets for broadcasting"""
        self.selected_mode = "broadcast"

        self.ctrl_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.ctrl_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
        self.ctrl_server.bind(('', self.CTRL_PORT))
        self.ctrl_server.listen(1)

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
        self.tcp_socket.bind(('', self.TCP_PORT))
        self.tcp_socket.listen(1)


    def broadcast(self, message):
        try:
            self.udp_socket.sendto(message, (get_broadcast_address(), self.UDP_PORT))
            data, addr = self.udp_socket.recvfrom(1024)
            if not data.startswith(message):
                data = data.decode('utf-8').strip()    
                if data[:7] == "I_SEE_U":
                    self.udp_socket.settimeout(20.0)
                    device_name = data[7:]
                    return device_name

        except socket.timeout:
            raise socket.timeout

        # except Exception:            


    def bd_connect(self, ):
        self.tcp_socket.settimeout(1.0)   
        try:
            self.tcp_client_socket, addr = self.tcp_socket.accept()
            self.tcp_socket.close()

        except socket.timeout:
            raise socket.timeout 
    
        except Exception as e:
            self.tcp_socket.close()
            raise e

        try:
            self.ctrl_socket, _ = self.ctrl_server.accept()
            self.ctrl_server.close()

        except socket.timeout:
            raise socket.timeout 
            
        except Exception as e:
            self.tcp_socket.close()
            raise e

    def init_scan_socks(self):
        """Intialize sockets for scanning"""
        self.tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        

    def scan(self) -> dict:
        """Scan for devices on the network"""
        self.selected_mode = "scan"

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

    def recv_bytes(self, no_bytes):
        return self.tcp_client_socket.recv(no_bytes)

    def send_bytes(self, bytes):
        return self.tcp_client_socket.sendall(bytes)
    
    def _send_end(self):
        """Send END command"""
        # Send a command byte: 0x02 means END
        try:
            self.tcp_client_socket.send(b'\x02')
        except OSError:
            pass

    async def _send_file(self, name, path):
        """Send a single file. Notifies reciever on cancellation"""
        loop = asyncio.get_event_loop()
        self.tcp_client_socket.setblocking(False)

        try:
            filesize = os.path.getsize(path)
            namebytes = name.encode('utf-8')

            header = (b'\x01' 
                       + len(namebytes).to_bytes(4, 'big') 
                       + namebytes
                       + filesize.to_bytes(4, 'big'))
            await loop.sock_sendall(self.tcp_client_socket, header)

            with open(path, "rb") as f:
                sent = 0
                while sent < filesize:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    await loop.sock_sendall(self.tcp_client_socket, chunk)
                    sent += len(chunk)

            return f"Sent '{name}' sent successfully"

        except asyncio.CancelledError:
            try:
                self.tcp_client_socket.setblocking(True)
                self.tcp_client_socket.send(b'\x03')
            except OSError:
                pass 
            raise

        except OSError as e:
            raise RuntimeError(f"Connection lost - reciever may have cancelled")

        finally:
            try:
                self.tcp_client_socket.setblocking(True)
            except OSError:
                pass


    def clear_receive_buffer(self):
        """Reads and discards all pending data currently in the socket buffer."""
        self.tcp_client_socket.setblocking(False)
        try:
            while True:
                data = self.recv_bytes(4096)
                if not data:
                    break
        except BlockingIOError:
            pass
        finally:
            self.tcp_client_socket.setblocking(True)
    
    async def _recieve_file(self, dest_folder):
        """Receive files. Shuts down socket on cancellation so sender unblocks."""
        loop = asyncio.get_event_loop()
        self.tcp_client_socket.setblocking(False)

        async def recv_exact(n: int) -> bytes:
            """Await exactly n bytes"""
            buf = b''
            while len(buf) < n:
                chunk = await loop.sock_recv(self.tcp_client_socket, n - len(buf))
                if not chunk:
                    raise ConnectionError("Connection closed by sender")
                buf += chunk
            return buf

        try:
            while True:
                cmd = await  loop.sock_recv(self.tcp_client_socket, 1)

                if not cmd:
                    return "Connection closed by Sender"

                if cmd   == b'\x03':   # CANCEL - sender stopped
                    return "Transfer cancelled by sender"
                
                elif cmd   == b'\x02':   # END - allf siles done
                    return "Transfer complete."
                
                elif cmd == b'\x01':   # File incoming
                    name_len = int.from_bytes(await recv_exact(4), 'big')
                    filename = (await recv_exact(name_len)).decode('utf-8')
                    filesize = int.from_bytes(await recv_exact(4), 'big')

                    # Recieve file
                    print(f"Receiving {filename} ({filesize/(1024*1024):.2f} MB)....") 

                    filepath = os.path.join(dest_folder, filename)
                    with open(filepath, "wb") as f:
                        received = 0
                        while received < filesize:
                            chunk = await loop.sock_recv(
                                self.tcp_client_socket,
                                min(65536, filesize - received)
                            )
                            if not chunk:
                                raise ConnectionError("Connection lost mid-transfer")
                            f.write(chunk)
                            received += len(chunk)

                    return f"File {filename} recieved"

                else:
                    return f"Unknown command: {cmd!r}"

        except asyncio.CancelledError:
            try:
                self.tcp_client_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            raise

        except ConnectionError as e:
            return str(e)

        finally:
            try:
                self.tcp_client_socket.setblocking(True)
            except OSError:
                pass
        
            

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

    @staticmethod
    def get_input():
        return key_pressed()

class XenderController():
    def __init__(self, username):
        self.model = NetworkManager(username)
        self.view = ConsoleView()
        self.running = True

    async def run(self):
        while self.running:
            choice = self.view.show_menu()
            if choice == '1':
                self.view.show_message("\nScanning for devices... (press 'q' to stop)")
                devices = self.model.scan()
                self.view.show_devices(devices)
                if devices:
                    idx = self.view.get_selection(len(devices))
                    selected_name = list(devices.keys())[idx-1]
                    if self.model.connect(devices[selected_name][0], selected_name):
                        self.view.show_message(f"Connected to {selected_name}")
                        await self.transfer_loop()
                else:
                    self.view.show_message("No devices found.")
            elif choice and choice == '2':
                self.view.show_message("\nBroadcasting to network... (press q to go back to previous menu)")
                self.model.init_bd_socks()
                username_bytes = self.name.encode('utf-8')
                message = bytes([len(username_bytes)]) + username_bytes + b"XENDER_DISCOVERY_REQUEST"
                while True:
                    input = self.view.get_input()
                    if input == "q":
                        break
                    try:
                        if conn := self.model.broadcast(message):
                            choice == self.view.ask_yes_no(f"\nAccept connection from '{conn}' \n[1] Yes \n[2] No")
                            if   choice == "1":
                                self.view.show_message(f"Connecting to {conn}...")
                                break
                            elif choice == "2":
                                self.view.show_message("User refused connection.")
                                self.view.show_message("\nBroadcasting to network... (press q to go back to previous menu)")
                        else:
                            continue
                    except socket.timeout:
                        continue

                # Connect to device
                while True:
                    input = self.view.get_input()
                    if input == "q":
                        break
                    try:
                        self.model.bd_connect()
                        break
                    except socket.timeout:
                        continue
                    except Exception as e:
                        self.view.show_message(f"Error connecting to {conn}.")
                        break
                    
                await self.transfer_loop()

            elif choice and choice == '3':
                self.view.show_message("Goodbye!")
                self.running = False
                self.model.udp_socket.close()
                if self.model.tcp_client_socket:
                    self.model.tcp_client_socket.close()
                if self.model.ctrl_socket:
                    self.model.ctrl_socket.close()
                if self.model.conn:
                    self.model.conn.close()
                break

    async def try_send(self):
            """Send files"""
            file_paths = filedialog.askopenfiles(
                title="Xender -> Select files",
            )
            if not file_paths:
                self.view.show_message("No files selected.")
                return

            # Cannot send more than 99 files
            no_files = len(file_paths)
            if   1 <= no_files < 9:
                no_files_bytes = ("0"+str(no_files)).encode('utf-8')
            elif 10 <= no_files <= 99:
                no_files_bytes = str(no_files).encode('utf-8')
            else:
                self.view.show_message("Too many files selected (max 99).")
                return
            self.model.send_bytes(no_files_bytes)

            cancelled = False
            for file_obj in file_paths:
                name = os.path.basename(file_obj.name)
                path = file_obj.name
                try:
                    self.view.show_message(f"Sending {name}... (press 'q' to stop)")
                    send_file = asyncio.create_task(self.model._send_file(name, path))
                    pressed_key = asyncio.create_task(async_key_pressed())
                    done, pending = await asyncio.wait(
                        {send_file, pressed_key}, 
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, Exception):
                            pass
    
                    if send_file in done:
                        result = send_file.result()
                        self.view.show_message(f"{result}")
                        cancelled = True
                        
                    elif key_pressed in done:
                        self.view.show_message("Sending stopped by user.")
                        cancelled = True

                except Exception as e:
                    self.view.show_message(f"Error sending {name}: {e}")

            if not cancelled:
                self.model._send_end()

    async def try_recieve(self):
        """Recieve files"""
        self.model.clear_receive_buffer()

        # Prompt user for destination folder
        dest_folder = filedialog.askdirectory(title="Select destination folder")
        if dest_folder:
            self.view.show_message(f"Destination folder {dest_folder}")
        else:
            self.view.show_message(f"Invalid Destination folder")

        
        # Recieve the number of files to recieve
        try:
            bytes = self.model.recv_bytes(2)
        except ValueError:
            return 
        
        no_files_to_recieve = int(bytes.decode('utf-8'))
        files_recieved = 0
        while files_recieved < no_files_to_recieve:
            files_recieved += 1 
            try:
                self.view.show_message(f"\nRecieving file {files_recieved}/{no_files_to_recieve}... (press 'q' to stop)")
                recv_file = asyncio.create_task(self.model._recieve_file(dest_folder))
                pressed_key = asyncio.create_task(async_key_pressed())

                done, pending = await asyncio.wait(
                    {recv_file, pressed_key}, 
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass

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
                await self.try_send()    
            elif sel == 2:
                await self.try_recieve()
            elif sel == 3:break

def on_hotspot():
        # Check if is_admin
        if not hotspot.is_admin():
            print("ERROR: This script must be run as Administrator to manage Hotspot connection.")
            print("Please right-click the script and select 'Run as administrator'.")
            return

        # Check driver support
        if not hotspot.get_driver_info():
            print("ERROR: Your Wi-Fi adapter does not support Hosted Network.")
            print("Please check your driver or use a different adapter.")
            return

        status    = hotspot.get_hosted_network_status()
        ssid, key = hotspot.get_current_hosted_settings()

        if status == "started":
            clients = hotspot.get_connected_clients()
            print("\n" + "="*50)
            print("HOTSPOT IS ALREADY ACTIVE")
            print("="*50)
            print(f"  SSID            : {ssid if ssid else 'Unknown'}")
            print(f"  Password        : {key if key else 'Unknown'}")
            print(f"  Connected devices: {clients}")
            print("="*50)
            print("No changes were made to your system.")
            return  # Exit gracefully without touching anything

        # If not started, display current status and proceed
        print(f"Hotspot status: {status.capitalize()}. Setting up and starting...")

        # Get or create configuration
        if ssid and key:
            print(f"Using existing configuration:")
            print(f"  SSID     : {ssid}")
            print(f"  Password : {key}")
        else:
            ssid = hotspot.generate_random_ssid()
            key = hotspot.generate_random_key()
            print("No existing Hosted Network found. Creating new one...")
            hotspot.set_hosted_network(ssid, key)
            print(f"  SSID     : {ssid}")
            print(f"  Password : {key}")

            # Start the Hosted Network
            if hotspot.start_hosted_network():
                print("\nHotspot started successfully.")
                print("You can now connect other devices using the above SSID and password.")
                print("(Internet access will not be available unless you enable ICS manually.)")
            else:
                print("\nHotspot could not be started. Check if another hotspot is already running.")
                return

def check_wifi_hotspot():
    print("\nChecking Wifi-Hotspot Status...")

    # Check if this device is hosting a hotspot 
    hosted_started, hosted_ssid, hosted_password, client_count = WHconn.get_hosted_network_status()

    # Check if this device is connected as a client
    client_info = WHconn.get_client_wifi_info()
    client_state = client_info.get("state") if client_info else None
    client_ssid = client_info.get("ssid") if client_info else None
    client_network_type = client_info.get("network_type") if client_info else None

    # Determine status 
    # Case 1: Device is the hotspot and has at least one client connected
    if hosted_started and client_count > 0:
        print("\n Your device is acting as a Wi-Fi hotspot.")
        print(f"   Hotspot SSID   : {hosted_ssid if hosted_ssid else 'Unknown'}")
        print(f"   Password       : {hosted_password if hosted_password else 'Unknown'}")
        print(f"   Connected devices: {client_count}")
        print("   (Other devices are connected to your hotspot.)")
        return

    # Case 2: Device is connected as a client to another hotspot
    if client_state == "connected" and client_ssid:
        if WHconn.is_hotspot_network(client_ssid, client_network_type):
            device_name = WHconn.guess_device_name(client_ssid)
            print("\n Your device is connected to another device's hotspot.")
            print(f"   Network name   : {client_ssid}")
            print(f"   Device         : {device_name}")
            print(f"   Network type   : {client_network_type if client_network_type else 'Unknown'}")
            return

    # Case 3: Neither – not part of any hotspot scenario
    # print("\n   Your device is NOT in a hotspot connection") # scenario.
    if hosted_started and client_count == 0:
        print("   (Your hotspot is on, but no other devices are connected.)")
    elif hosted_started and client_count > 0:
        # already handled above, but just in case
        pass
    elif client_state == "connected":
        print(f"   You are connected to Wi-Fi network: {client_ssid}")
        print("   (But This does not appear to be a hotspot from a Supported device.)")
    else:
        print("   Wi-Fi is either off or not connected to any network.")

    # Additional details for debugging
    if hosted_started and client_count == 0:
        print(f"   Hotspot SSID   : {hosted_ssid}")
        print(f"   Password       : {hosted_password}")
    # if client_state == "connected":
    #     print(f"   You are Connected to   : {client_ssid} (type: {client_network_type})")

def cls():
    """Clear screen"""
    print("\033[2J\033[H", end="")      
    print("███████╗███████╗███╗   ██╗███████╗███████╗███████╗")
    print("    ██╔╝██╔════╝████╗  ██║██╔══██║██╔════╝██╔══██║")
    print("   ██╔╝ █████╗  ██╔██╗ ██║██║  ██║█████╗  ██████╔╝")
    print("  ██╔╝  ██╔══╝  ██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗")
    print("███████╗███████╗██║ ╚████║███████║███████╗██║  ██║")
    print("╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝  ╚═╝")

if __name__ == "__main__":
    cls()
    print("The best File-Transfer tool")
    USERNAME = input("Enter username: ")
    cls()
    print(f"Welcome {USERNAME}!")
    xender = XenderController(USERNAME)

    check_wifi_hotspot()
    
    print("\n[1] Activate Device Hotspot  \n[2] Check Wifi-Hotspot Status \n[3] Skip to Transfer FILES \n[4] Exit")
    while True:
        key = key_pressed()
        if   key == "1":
            cls()
            on_hotspot()
            print("\n[1] Activate Device Hotspot  \n[2] Check Wifi-Hotspot Status \n[3] Skip to Transfer FILES \n[4] Exit")
        elif key == "2":
            cls()
            check_wifi_hotspot()
            print("\n[1] Activate Device Hotspot  \n[2] Check Wifi-Hotspot Status \n[3] Skip to Transfer FILES \n[4] Exit")
        elif key  == "3": break
        elif key  == "4": sys.exit()

    asyncio.run(xender.run())



    # print(f"{fg.GREEN}███████╗███████╗███╗   ██╗███████╗███████╗███████╗{fg.RESET}")
    # print(f"{fg.GREEN}    ██╔╝██╔════╝████╗  ██║██╔══██╗██╔════╝██╔══██╗{fg.RESET}")
    # print(f"{fg.GREEN}   ██╔╝ █████╗  ██╔██╗ ██║██║  ██║█████╗  ██████╔╝{fg.RESET}")
    # print(f"{fg.GREEN}  ██╔╝  ██╔══╝  ██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗{fg.RESET}")
    # print(f"{fg.GREEN}███████╗███████╗██║ ╚████║███████╗███████╗██║  ██║{fg.RESET}")
    # print(f"{fg.GREEN}╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝  ╚═╝{fg.RESET}")
