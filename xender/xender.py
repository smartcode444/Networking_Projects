import socket
import tkinter as tk
from tkinter import filedialog
import os
from datetime import datetime
# import ifaddr
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


def key_pressed() -> bool | str:
    """Reeturn the character if a key was pressed, else None."""
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


class mySocket:
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
        self.udp_socket.settimeout(4.0)
        self.udp_socket.bind(('', self.UDP_PORT))
        log("[SOCKET] UDP socket created and running")

    def broadcast(self) -> bool:
        """Broadcast to sockets on the network"""
        self.selected_mode = "broadcast"
        log("[BROADCAST] Creating Binding TCP socket...")
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
        self.tcp_socket.bind(('', self.TCP_PORT))
        self.tcp_socket.listen(1)
        self.tcp_socket.settimeout(1.0) 
        log("[BROADCAST] Binding TCP socket up and ready")
        
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
                "[BROADCAST] Shutting down Binding TCP socket\n" \
                "[BROADCAST] Broadcasting operation terminated!")
            self.tcp_socket.close()
            return False

        try:  
            log("[BROADCAST] Binding TCP socket ...")
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
                "[BROADCAST] Shutting down Binding TCP socket\n" \
                "[BROADCAST] Broadcasting operation terminated!")
            self.tcp_socket.close()
            return False
        
        except Exception as e:
            print("\n")
            log(f"[BROADCAST] An error occured {e} in broadcast()\n" \
                "[BROADCAST] Shutting down Binding TCP socket\n" \
                "[BROADCAST] Broadcasting operation terminated!")
            self.tcp_socket.close()
            return False
        

    def scan(self) -> dict:
        """Scan for devices on the network"""
        self.selected_mode = "scan"

        self.tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_client_socket.settimeout(1.0)

        print("Scanning for devices... (press 'q' to stop)")

        devices = {}

        # Scan for sockets for 20 secs
        # self.udp_socket.bind(('', self.UDP_PORT))
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
                        print(f"Devices: {devices}")
                except socket.timeout:
                    continue

        except KeyboardInterrupt:
            print("\n[*] Keyboard interrupt detected, Scanning operation terminated!")

        except Exception as e:
            print(f"An error occured {e} in scan(), Scanning operation terminated!")
            
        return devices

    def connect(self, devices: dict) -> bool:
        print("\nAvailabe devices: ")
        for index, (name, address) in enumerate(devices.items(), start=1):
            print(f"[{index}] Device [{name}]")
        while True:
            try:
                sel_num    = int(input("Which device would you like to connect to? "))
                if sel_num < 1 or sel_num > len(devices):
                    continue
                sel_device = list(devices.keys())[sel_num - 1]
                break

            except ValueError:
                continue

        print(f"Connecting to {sel_device}")

        while True:
            try:
                self.tcp_client_socket.connect((devices[sel_device][0], self.TCP_PORT))
                print(f"Succesfully connected to {sel_device}")
                return True

            except socket.timeout:
                # print("20s has elapsed")
                # return False
                continue

            except Exception as e:
                print(f"An error occured in {e} connect()")
                return False

    # @classmethod
    def transfer_files(self):
        """Transfer files"""
        while True:
            print("[1]Send files \n[2]Recieve files \n[3]Go back to Main Menu")
            choice = input(": ")
            if choice   == "1":
                self._try_send()
            elif choice == "2":
                self._try_recieve()
            elif choice == "3":
                break
            else:
                print("Invalid input")

    # @classmethod
    def _send_end(self):
        """Send END command"""
        # Send a command byte: 0x02 means END
        self.tcp_client_socket.send(b'\x02')

    # @classmethod
    def _try_send(self):
        """Send files"""
        file_paths = filedialog.askopenfiles(
            title="Xender -> Select files",
        )
        if not file_paths:
            return
        for file_obj in file_paths:
            name = os.path.basename(file_obj.name)
            path = file_obj.name
            try:
                self._send_file(name, path)
            except KeyboardInterrupt:
                print(f"[*] Keyboard Interrupt detected, Transfer of {name} is terminated")
                continue
            except Exception as e:
                print(f"Error sending {name}:")
        self._send_end()

    # @classmethod
    def _send_file(self, name: str , path):
        """Send file"""
        # Send command: 0x01 = file transfer
        self.tcp_client_socket.send(b'\x01')
        
        # Send filename length (4 bytes, big‑endian) and filename
        name_bytes = name.encode('utf-8')
        self.tcp_client_socket.send(len(name_bytes).to_bytes(4, 'big') + name_bytes)
        
        file_size = os.path.getsize(path)
        self.tcp_client_socket.send(file_size.to_bytes(4, 'big'))

        # Send file data

        print(f"Sending {name}...")
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
            print("\n[*] Keyboard interrupt detected, File transfer is terminated!")            
            raise KeyboardInterrupt
        
        except Exception:
            raise Exception

    # @classmethod
    def _try_recieve(self, ):
        """Recieve files"""
        # self.tcp_client_socket = tcp_client_socket
        self.tcp_client_socket.settimeout(5.0)
 
        while True:
            try:
                cmd = self.tcp_client_socket.recv(1)
                print(cmd)
                if not cmd:
                    print("Connection closed by sender")
                    break
                if cmd == b'\x02': # END Command                            # Add socket timeout retry logic
                    print("Transfer complete.")
                    break
                elif cmd == b'\x01': # File transfer
                    self._recieve_file()
                else:
                    print(f"Unknown command: {cmd}")
                    break

            except Exception as e:
                print(f"Error: {e}")
                break

    # @classmethod
    def _recieve_file(self):
        """Recieve files"""
        try:
            length_data = self.tcp_client_socket.recv(4)
            if len(length_data) < 4:
                raise RuntimeError("Failed to read filename length")
            name_len = int.from_bytes(length_data, 'big')

            # Read filename 
            name_bytes = b''
            while len(name_bytes) < name_len:
                chunk = self.tcp_client_socket.recv(name_len - len(name_bytes))
                if not chunk:
                    raise RuntimeError("Connection lost while reading filename")
                name_bytes += chunk
            filename = name_bytes.decode('utf-8')

            # Read file size 
            size_data = self.tcp_client_socket.recv(4)
            if len(size_data) < 4:
                raise RuntimeError("Failed to read file size")
            file_size = int.from_bytes(size_data, 'big')

        except socket.timeout:
            raise RuntimeError("Timeout waiting for data.")

        # Recieve file
        print(f"Recieving {filename} ({file_size/(1024*1024):.2f} MB)....") # -> Remember to approximate the file size
        with open(filename, "wb") as file:
            recieved = 0
            while recieved < file_size:
                try:
                    chunk = self.tcp_client_socket.recv(min(4096, file_size-recieved))
                except socket.timeout:
                    raise RuntimeError("Timeout waiting for data.")
                if not chunk:
                    break
                file.write(chunk)
                recieved += len(chunk)
        print(f"File {filename} recieved")



def main():
    print("Welcome to smartcode version of [Xender]")
    client_username = input("Enter username: ")

    mysocket = mySocket(client_username)

    print(f"Welcome {client_username}")
    
    try: 
        while True:
            print("\n[1]Scan \n[2]Broadcast \n[3]Exit")
            choice  = input(": ")
            if choice == "1":
                devices = mysocket.scan()
                if devices:
                    is_conn = mysocket.connect(devices)
                    if is_conn:
                        mysocket.transfer_files()
                else:
                    print("No device was found on the network")
                    continue

            elif choice == "2":
                is_conn = mysocket.broadcast()
                if is_conn:
                    mysocket.transfer_files()
                
            elif choice == "3":
                print("Thank you for using xender!")
                if mysocket.selected_mode is None:
                    mysocket.udp_socket.close()
                    break
                if  mysocket.selected_mode  == "scan":
                    mysocket.tcp_client_socket.close()
                elif mysocket.selected_mode == "broadcast":
                    mysocket.tcp_socket.close()
                    if hasattr(mysocket, "tcp_client_socket"):
                        mysocket.tcp_client_socket.close()
                # mysocket.udp_socket.close()

                mysocket.selected_mode = None
                break

            else:
                print("Invalid input, Try again")

    except KeyboardInterrupt:
        print("Thank you for using xender!")

if __name__ == "__main__":
    main()