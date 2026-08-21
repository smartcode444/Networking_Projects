"""
███████╗███████╗███╗   ██╗███████╗███████╗███████╗
    ██╔╝██╔════╝████╗  ██║██╔══██╗██╔════╝██╔══██╗
   ██╔╝ █████╗  ██╔██╗ ██║██║  ██║█████╗  ██████╔╝
  ██╔╝  ██╔══╝  ██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗
███████╗███████╗██║ ╚████║███████╗███████╗██║  ██║
╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝  ╚═╝
"""
import subprocess
import socket
import asyncio
import tkinter as tk
import os, sys
import netifaces
import logging
# from . import WHconn
# from . import hotspot
import WHconn
import hotspot
# from color import fg, bg
from tkinter import filedialog
from datetime import datetime
import time
import random

root = tk.Tk()
root.withdraw()

SPINNER = ["-", "\\", "|", "/"]
MENU_W  = 52   # box width

adjectives = ["Happy", "Clever", "Brave", "Calm", "Eager", "Fierce", "Gentle", "Jolly", "Kind", "Lively"]
nouns = ["Panda", "Tiger", "Eagle", "River", "Comet", "Shadow", "Falcon", "Summit", "Ocean", "Breeze"]

# Force UTF-8 on Windows so box-drawing chars render in modern terminals
if os.name == 'nt':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[logging.FileHandler("zender.log"), logging.StreamHandler(sys.stdout)]
# )
# logger = logging.getLogger("Zender")

# logger.info("This is a info message")
# logger.debug("This is a debug message")
# logger.warning("This is a warning message")
# logger.error("This is a error message")

class NetworkManager:
    def __init__(self, username: str):
        self.UDP_PORT          = 7007
        self.TCP_PORT          = 5005
        self.CTRL_PORT         = 5006
        self.BROADCAST_ADDR             = get_broadcast_address()

        self.DISCOVERY_MESSAGE = "XENDER_DISCOVERY_REQUEST"
        self.RESPONSE_MESSAGE  = "I_SEE_U"

        self.name              = username

        self.tcp_socket        = None
        self.tcp_client_socket = None
        self.ctrl_socket       = None # accepted from broadcaster side
        self.ctrl_conn         = None # connected from scanner side
        self._cancel_flag      = asyncio.Event()

        self.selected_mode     = None

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        self.udp_socket.bind(('', self.UDP_PORT))
        self.udp_socket.settimeout(1.0)

    def init_bd_socks(self):
        """Intialize sockets for broadcasting."""
        self.selected_mode = "broadcast"

        self.ctrl_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.ctrl_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
        self.ctrl_server.bind(('', self.CTRL_PORT))
        self.ctrl_server.listen(1)

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
        self.tcp_socket.bind(('', self.TCP_PORT))
        self.tcp_socket.listen(1)


    def broadcast(self, message) -> str:
        """Broadcast message on network."""
        try:
            self.udp_socket.sendto(message, (self.BROADCAST_ADDR , self.UDP_PORT))
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


    def bd_connect(self):
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
        """Intialize sockets for scanning."""
        self.selected_mode = "scan"
        self.tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        

    def scan(self, msg, devices) -> tuple:
        """Scan for devices on the network."""
        try:
            data, address      = self.udp_socket.recvfrom(1024)
            username_len       = data[0]
            client_name        = data[1:1+username_len].decode('utf-8')
            client_msg         = data[1+username_len:].decode('utf-8')

            # Debug
            # print(f"Address: {address}") 
            # print(f"Recieved data: {data}, client_name: {client_name}, client_msg: {client_msg}")
            # print(f"Found {len(devices)} devices")

            if client_msg == "XENDER_DISCOVERY_REQUEST" and client_name not in devices:
                self.udp_socket.sendto(msg, (address))                
                return client_name, address

        except socket.timeout:
            raise socket.timeout

        except Exception as e:
            self.tcp_client_socket.close()
            raise e
            

    def sc_connect(self, device_addr):
        try:
            self.tcp_client_socket.settimeout(1.0)
            self.tcp_client_socket.connect((device_addr, self.TCP_PORT))

            self.ctrl_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ctrl_conn.connect((device_addr, self.CTRL_PORT))

        except socket.timeout:
            raise socket.timeout

        except Exception as e:
            raise e

    def send_cancel_signal(self):
        """Send a CANCEL byte to the other side via the control socket."""
        ctrl = self.ctrl_socket or self.ctrl_conn
        try:
            ctrl.send(b'\x03')
        except OSError:
            pass

    async def watch_for_cancel(self):
        """Runs concurrently during transfer
        Blocks until the other side sends 0x03, then sets _cancel_flag."""
        loop = asyncio.get_event_loop()
        ctrl = self.ctrl_socket or self.ctrl_conn
        ctrl.setblocking(False)
        try:
            while True:
                data = await loop.sock_recv(ctrl , 1)
                if data == b'\x03':
                    self._cancel_flag.set()
                    return
        except (OSError, asyncio.CancelledError):
            raise

    def recv_bytes(self, no_bytes):
        """Recieve bytes."""
        return self.tcp_client_socket.recv(no_bytes)

    def send_bytes(self, bytes):
        """Send bytes."""
        return self.tcp_client_socket.sendall(bytes)
    
    def _send_end(self):
        """Send END command."""
        # Send a command byte: 0x02 means END
        try:
            self.tcp_client_socket.send(b'\x02')
        except OSError:
            pass

    async def _send_file(self, name, path, on_progress=None):
        """Send a single file over the data socket. 
        Notifies reciever on cancellation."""
        loop = asyncio.get_event_loop()
        self.tcp_client_socket.setblocking(False)
        self._cancel_flag.clear()

        try:
            filesize = os.path.getsize(path)
            namebytes = name.encode('utf-8')

            # ── Header
            # [0x01][4B name_len][name][8B file_size]
            # 8 bytes for file_size supports files up to 16 exabytes
            header = (b'\x01' 
                       + len(namebytes).to_bytes(4, 'big') 
                       + namebytes
                       + filesize.to_bytes(8, 'big'))
            await loop.sock_sendall(self.tcp_client_socket, header)

            start = time.perf_counter()
            with open(path, "rb") as f:
                sent = 0
                while sent < filesize:
                    if self._cancel_flag.is_set(): # Check between chunks
                        return f"\n[!] Transfer of '{name}' stopped"
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    await loop.sock_sendall(self.tcp_client_socket, chunk)
                    sent += len(chunk)
                    if on_progress:              
                        on_progress(sent, filesize, start)
                    

            return f"\n[OK] Sent '{name}' sent successfully"

        except asyncio.CancelledError:
            self.send_cancel_signal()
            raise

        except OSError as e:
            raise RuntimeError(f"\n[!] Error while sending '{name}'")

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
    
    async def _recieve_file(self, dest_folder, on_progress=None):
        """Receive files over the data socket. 
        Shuts down socket on cancellation so sender unblocks."""
        loop = asyncio.get_event_loop()
        self.tcp_client_socket.setblocking(False)

        async def recv_exact(n: int) -> bytes:
            """Await exactly n bytes"""
            buf = b''
            while len(buf) < n:
                chunk = await loop.sock_recv(self.tcp_client_socket, n - len(buf))
                if not chunk:
                    raise ConnectionError("[!] Connection closed by sender")
                buf += chunk
            return buf

        try:
            while True:
                cmd = await  loop.sock_recv(self.tcp_client_socket, 1)

                if not cmd:
                    return "\n[!] Connection closed by Sender"

                if cmd   == b'\x03':   # CANCEL - sender stopped
                    return "\n[!] Transfer cancelled by sender"
                
                elif cmd == b'\x02':   # END - allf siles done
                    return "\n[OK] Transfer complete."
                
                elif cmd == b'\x01':   # File incoming
                    name_len = int.from_bytes(await recv_exact(4), 'big')
                    filename = (await recv_exact(name_len)).decode('utf-8')
                    filesize = int.from_bytes(await recv_exact(8), 'big')

                    # Recieve file
                    print(f"Receiving {filename} ({filesize/(1024*1024):.2f} MB)....") 

                    start    = time.perf_counter()
                    filepath = os.path.join(dest_folder, filename)
                    with open(filepath, "wb") as f:
                        received = 0
                        while received < filesize:
                            chunk = await loop.sock_recv(
                                self.tcp_client_socket,
                                min(65536, filesize - received)
                            )
                            if not chunk:
                                raise ConnectionError("\n[!] Connection lost mid-transfer")
                            f.write(chunk)
                            received += len(chunk)
                            if on_progress:
                                on_progress(received, filesize, start)

                    return f"\n[Ok] File {filename} recieved"

                else:
                    return f"\n[!] Unknown command: {cmd!r}"

        except asyncio.CancelledError:
            self.send_cancel_signal()
            raise

        except ConnectionError as e:
            return f"Socket error: {e}"

        finally:
            try:
                self.tcp_client_socket.setblocking(True)
            except OSError:
                pass
        
            

class ConsoleView:
    @staticmethod
    def _box(title, rows):
        # cls()
        w      = MENU_W
        border = "+" + "-" * (w - 2) + "+"
        mid    = "+" + "-" * (w - 2) + "+"
        print(border)
        print("|" + title.center(w - 2) + "|")
        print(mid)
        for row in rows:
            print("|  " + row.ljust(w - 4) + "|")
        print(border)

    # Menu
    @staticmethod
    def show_main_menu():
        ConsoleView._box(
            "ZENDER",
            [
                "[1]  Transfer Files",
                "[2]  Check Wi-Fi Hotspot Status",
                "[3]  Activate Device Hotspot",
                "[4]  Exit",
            ],
        )

    @staticmethod
    def show_menu():
        ConsoleView._box(
            "Connect to a Device",
            [
                "[1]  Scan  -- find other devices",
                "[2]  Broadcast  -- let others find you",
                "[3]  Back to Main Menu",
            ],
        )
        while True:
            key = key_pressed()
            if key:
                return key

    @staticmethod
    def show_transfer_menu():
        ConsoleView._box(
            "File Transfer",
            [
                "[1]  Send files",
                "[2]  Receive files",
                "[3]  Back",
            ],
        )


    @staticmethod
    def show_devices(devices):
        if not devices:
            print("\n  [!]  No devices found.\n")
            return
        rows = [f"[{i}]  {name}  ({addr[0]})"
                for i, (name, addr) in enumerate(devices.items(), 1)]
        rows.append("'q'  Go back")
        ConsoleView._box("Devices Found", rows)

    # Messages
    @staticmethod
    def show_message(msg):
        """Normal message — always on its own line."""
        print(f"  {msg}")

    @staticmethod
    def show_inline(msg):
        """Overwrite the current line (spinner / progress bar)."""
        print(f"\r  {msg:<{MENU_W}}", end="", flush=True)

    @staticmethod
    def end_inline():
        """Call after a spinner/progress sequence to move to next line."""
        print()

    @staticmethod
    def show_progress(received, total, label, start_time):
        """In-place ASCII progress bar."""
        if total <= 0:
            return
        pct     = received / total * 100
        elapsed = time.perf_counter() - start_time
        speed   = (received / elapsed / (1024 * 1024)) if elapsed > 0.05 else 0.0
        bar_w   = 24
        filled  = int(bar_w * received / total)
        bar     = "#" * filled + "-" * (bar_w - filled)
        short   = label[:13]
        ConsoleView.show_inline(
            f"[{bar}] {pct:5.1f}%  {speed:5.1f} MB/s  {short}"
        )

    @staticmethod
    def ask_yes_no(prompt):
        print(f"\n  {prompt}")
        print("  [1] Yes    [2] No\n")
        while True:
            key = key_pressed()
            if key in ("1", "2"):
                return key

    @staticmethod
    def get_selection(max_num):
        while True:
            key = key_pressed()
            if key == "q":
                return "q"
            try:
                sel = int(key) if key else None
                if sel and 1 <= sel <= max_num:
                    return sel
            except ValueError:
                continue

    @staticmethod
    def get_input():
        return key_pressed()

class XenderController():
    def __init__(self, username):
        self.username = username
        self.model = NetworkManager(username)
        self.view = ConsoleView()
        self.running = True

    async def run(self):
        while self.running:
            choice = self.view.show_menu()
            if choice == '1':
                cls()
                self.model.init_scan_socks()
                devices = {}
                msg    = b"I_SEE_U" + self.username.encode('utf-8')
                spin_i = 0

                self.view.show_message("Scanning for devices... press 'q' to stop\n")

                msg = b"I_SEE_U" + self.username.encode('utf-8')
                while True:
                    self.view.show_inline(
                        f"{SPINNER[spin_i % len(SPINNER)]}  Scanning... {len(devices)} found"
                    )
                    spin_i += 1  

                    # Check key (non-blocking)
                    user_key = self.view.get_input()
                    if user_key == 'q':
                        self.view.end_inline()        # move off spinner line
                        self.view.show_message("[!]  Scanning stopped.")
                        break

                    try:
                        if data := self.model.scan(msg, devices):
                            name, addr = data
                            devices[name] = addr
                            # Don't show_message here — breaks the spinner line
                    except socket.timeout:
                        continue
                    except Exception as e:
                        self.view.end_inline()
                        self.view.show_message(f"[!]  Error scanning: {e}")
                        break

                self.view.end_inline()
                self.view.show_devices(devices)

                if devices:
                    idx = self.view.get_selection(len(devices))
                    if idx == 'q':
                        continue
                    selected_name = list(devices.keys())[idx-1]
                    self.view.show_message(f"Connecting to {selected_name}... (press 'q' to stop)")
                    while True:
                        user_key = self.view.get_input()
                        if user_key == 'q':
                            self.view.show_message("\n[!] User refused connection")
                            break
                        try:
                            self.model.sc_connect(devices[selected_name][0])
                            self.view.show_message(f"[OK] Succesfully connected to {selected_name}")
                            await self.transfer_loop()
                            break
                        except socket.timeout:
                            continue
                        except Exception as e:
                            self.view.show_message(f"[!] Error connecting to {selected_name}: {e}.")
                            break


            elif choice and choice == '2':
                cls()
                # self.view.show_message("\nBroadcasting to network... (press q to stop)")
                self.model.init_bd_socks()
                username_bytes = self.username.encode('utf-8')
                message = bytes([len(username_bytes)]) + username_bytes + b"XENDER_DISCOVERY_REQUEST"
                spin_i = 0

                while True:
                    self.view.show_inline(
                        f"{SPINNER[spin_i % len(SPINNER)]}  Broadcasting... (press q to stop)"
                    )
                    spin_i += 1  
                    user_key = self.view.get_input()
                    if user_key == 'q':
                        self.view.show_message("\nBroadcasting stopped by user")
                        break
                    try:
                        if conn := self.model.broadcast(message):
                            choice = self.view.ask_yes_no(f"\nAccept connection from '{conn}'")
                            if   choice == "1":
                                break
                            elif choice == "2":
                                self.view.show_message("[!] User refused connection.")
                                self.view.show_message("\nBroadcasting to network... (press q to go back to previous menu)")
                        else:
                            continue
                    except socket.timeout:
                        continue

                # Connect to device
                if choice == "1":
                    self.view.show_message(f"Connecting to {conn}... (press 'q' to stop)")
                    while True:
                        user_key = self.view.get_input()
                        if user_key == "q":
                            self.view.show_message("\n[!] Connection stopped by user")
                            break
                        try:
                            self.model.bd_connect()
                            await self.transfer_loop()
                            break
                        except socket.timeout:
                            continue
                        except Exception as e:
                            self.view.show_message(f"[!] Error connecting to {conn}: {e}.")
                            break
                    

            elif choice and choice == '3':
                # self.view.show_message("Goodbye!")
                break


    async def try_send(self):
            """Send files"""
            cancelled = False
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

            for file_obj in file_paths:
                name = os.path.basename(file_obj.name)
                path = file_obj.name
                filesize = os.path.getsize(file_obj.name)
                self.view.show_message(f"[>>] Sending '{name}' ({filesize / (1024*1024):.1f} MB) (press 'q' to stop)")

                try:
                    send_file = asyncio.create_task(
                       self.model._send_file(
                            name, path,
                            on_progress=lambda s, t, st: self.view.show_progress(s, t, name, st)
                        )
                    )
                    pressed_key = asyncio.create_task(async_key_pressed())
                    watch_cancel = asyncio.create_task(self.model.watch_for_cancel())

                    done, pending = await asyncio.wait(
                        {send_file, pressed_key, watch_cancel}, 
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
                        self.view.end_inline()      # move off progress bar line
                        self.view.show_message(send_file.result())
                        
                    elif pressed_key in done:
                        self.view.show_message("[!] Sending stopped by user.")
                        cancelled = True
                        break

                    elif watch_cancel in done:
                        self.view.show_message("[!] Transfer cancelled by reciever.")
                        break

                except Exception as e:
                    self.view.show_message(f"[!] Error sending {name}: {e}")

            if not cancelled:
                self.model._send_end()

    async def try_recieve(self):
        """Recieve files"""
        self.model.clear_receive_buffer()

        # Prompt user for destination folder
        dest_folder = filedialog.askdirectory(title="Select destination folder")
        if dest_folder:
            self.view.show_message(f"[OK] Destination folder {dest_folder}")
        else:
            self.view.show_message(f"[!] Invalid Destination folder")

        
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
                self.view.show_message(f"\n[>>]Recieving file {files_recieved}/{no_files_to_recieve}... (press 'q' to stop)")
                recv_file = asyncio.create_task(
                    self.model._recieve_file(
                        dest_folder,
                        on_progress=lambda s, t, st: self.view.show_progress(s, t, "receiving", st)
                    )
                )
                pressed_key = asyncio.create_task(async_key_pressed())
                watch_cancel = asyncio.create_task(self.model.watch_for_cancel())

                done, pending = await asyncio.wait(
                    {recv_file, pressed_key, watch_cancel}, 
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass

                if recv_file in done:
                    self.view.end_inline()                  # move off progress bar line
                    self.view.show_message(recv_file.result())
                    
                elif pressed_key in done:
                    self.model.send_cancel_signal()
                    self.view.show_message("[!] Recieving stopped by user.")

                elif watch_cancel in done:
                    self.view.show_message("[!]  Transfer cancelled by sender.")
                    break

            except Exception as e:
                print(f"Error: {e}")
                self.view.show_message(f"[!] Error: {e}")

    async def transfer_loop(self):
        """Transfer files"""
        while True:
            cls()
            self.view.show_message("\nTransfer FILES \n[1] Send files \n[2] Recieve files \n[3] Back to main")
            sel = self.view.get_selection(3)
            if   sel == 1:
                await self.try_send()    
            elif sel == 2:
                await self.try_recieve()
            elif sel == 3:break



def on_hotspot():
    """Activate hotspot"""
    # Check if is_admin
    if not hotspot.is_admin():
        print("[!] ERROR: This script must be run as Administrator to activate Hotspot.")
        print("Please right-click the script and select 'Run as administrator'.")
        return

    # Check driver support
    if not hotspot.get_driver_info():
        print("[!] ERROR: Your Wi-Fi adapter does not support Hosted Network.")
        print("Please check your driver or use a different adapter.")
        return

    status    = hotspot.get_hosted_network_status()
    ssid, key = hotspot.get_current_hosted_settings()

    if status == "started":
        clients = hotspot.get_connected_clients()
        print("\n" + "="*50)
        print("[OK] HOTSPOT IS ALREADY ACTIVE")
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
            print("\n[OK] Hotspot started successfully.")
            print("You can now connect other devices using the above SSID and password.")
            print("(Internet access will not be available unless you enable ICS manually.)")
        else:
            print("\nHotspot could not be started. Check if another hotspot is already running.")
            return


def check_wifi_hotspot():
    """Check Wifi-Hotspot Status"""
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
        print("\n[OK] Your device is acting as a Wi-Fi hotspot.")
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
        print(f"  [OK] You are connected to Wi-Fi network: {client_ssid}")
        print("   (But This does not appear to be a hotspot from a Supported device.)")
    else:
        print("   Wi-Fi is either off or not connected to any network.")

    # Additional details for debugging
    if hosted_started and client_count == 0:
        print(f"   Hotspot SSID   : {hosted_ssid}")
        print(f"   Password       : {hosted_password}")
    # if client_state == "connected":
    #     print(f"   You are Connected to   : {client_ssid} (type: {client_network_type})")


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

                    await asyncio.sleep(0.05)
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
                    await asyncio.sleep(0.05)
                except asyncio.CancelledError:
                    raise

    except KeyboardInterrupt:
            return None

def generate_username():
    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    number = random.randint(10, 99)
    
    # Combine the words and number into a single username
    return f"{adj}{noun}{number}"

def log(msg):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}")

def cls():
    """Clear screen"""
    if os.name == 'nt':
        subprocess.run('cls', shell=True)
    else:
        subprocess.run(['clear'])
    print("███████╗███████╗███╗   ██╗███████╗███████╗███████╗")
    print("    ██╔╝██╔════╝████╗  ██║██╔══██║██╔════╝██╔══██║")
    print("   ██╔╝ █████╗  ██╔██╗ ██║██║  ██║█████╗  ██████╔╝")
    print("  ██╔╝  ██╔══╝  ██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗")
    print("███████╗███████╗██║ ╚████║███████║███████╗██║  ██║")
    print("╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝  ╚═╝")
    print(f"Welcome {USERNAME}!")

if __name__ == "__main__":
    USERNAME = generate_username()
    cls()
    
    xender = XenderController(USERNAME)

    check_wifi_hotspot()
    
    ConsoleView.show_main_menu()
    while True:
        key = key_pressed()
        if   key == "1":
            cls()
            xender.running = True
            try:
                asyncio.run(xender.run())
            except KeyboardInterrupt:
                break
            ConsoleView.show_main_menu()

        elif key == "2":
            cls()
            check_wifi_hotspot()
            ConsoleView.show_main_menu()

        elif key  == "3": 
            cls()
            on_hotspot()
            ConsoleView.show_main_menu()

        elif key  == "4": 
            xender.running = False
            xender.model.udp_socket.close()
            if xender.model.tcp_client_socket:
                xender.model.tcp_client_socket.close()
            if xender.model.ctrl_socket:
                xender.model.ctrl_socket.close()
            if xender.model.ctrl_conn:
                xender.model.ctrl_conn.close()
            break

    print("Thank you for using zender!")            
    sys.exit()

