import subprocess
import random
import string
import sys
import ctypes

def is_admin():
    """Return True if the script is running with Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_netsh(command):
    """Execute a netsh command and return the output as a string."""
    try:
        result = subprocess.run(
            ["netsh"] + command.split(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True
        )
        return result.stdout + result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Error executing netsh command: {e}")
        print(e.output)
        sys.exit(1)

def get_driver_info():
    """Check if the Wi-Fi driver supports Hosted Network."""
    output = run_netsh("wlan show drivers")
    for line in output.splitlines():
        if "Hosted network supported" in line:
            if "Yes" in line:
                return True
            else:
                return False
    return False

def get_hosted_network_status():
    """Return the current status: 'started', 'not started', or 'unknown'."""
    output = run_netsh("wlan show hostednetwork")
    for line in output.splitlines():
        if "Status" in line and ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                status = parts[1].strip().lower()
                return status
    return "unknown"

def get_current_hosted_settings():
    """Return (ssid, key) if a Hosted Network is already configured, else (None, None)."""
    output = run_netsh("wlan show hostednetwork")
    ssid = None
    key = None
    for line in output.splitlines():
        if "SSID" in line and ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                ssid = parts[1].strip()
        if "Key" in line and ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                key = parts[1].strip()
    return ssid, key

def get_connected_clients():
    """Return the number of connected clients (stations)."""
    output = run_netsh("wlan show hostednetwork")
    for line in output.splitlines():
        if "Number of clients" in line and ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return "0"

def generate_random_ssid():
    """Generate a random SSID (e.g., 'Hotspot_1234')."""
    digits = ''.join(random.choices(string.digits, k=4))
    return f"Hotspot_{digits}"

def generate_random_key(length=12):
    """Generate a random alphanumeric key of given length (at least 8)."""
    if length < 8:
        length = 8
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def set_hosted_network(ssid, key):
    """Configure the Hosted Network with the given SSID and key."""
    run_netsh(f"wlan set hostednetwork mode=allow ssid={ssid} key={key}")

def start_hosted_network():
    """Start the Hosted Network."""
    output = run_netsh("wlan start hostednetwork")
    if "started" in output.lower():
        return True
    else:
        print("Failed to start hosted network:")
        print(output)
        return False

def main():
    if not is_admin():
        print("ERROR: This script must be run as Administrator.")
        print("Please right-click the script and select 'Run as administrator'.")
        sys.exit(1)

    # Check driver support
    if not get_driver_info():
        print("ERROR: Your Wi-Fi adapter does not support Hosted Network.")
        print("Please check your driver or use a different adapter.")
        sys.exit(1)

    # Check if the hotspot is already ACTIVE
    status = get_hosted_network_status()
    ssid, key = get_current_hosted_settings()

    if status == "started":
        clients = get_connected_clients()
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
        ssid = generate_random_ssid()
        key = generate_random_key()
        print("No existing Hosted Network found. Creating new one...")
        set_hosted_network(ssid, key)
        print(f"  SSID     : {ssid}")
        print(f"  Password : {key}")

    # Start the Hosted Network
    if start_hosted_network():
        print("\nHotspot started successfully.")
        print("You can now connect other devices using the above SSID and password.")
        print("(Internet access will not be available unless you enable ICS manually.)")
    else:
        print("\nHotspot could not be started. Check if another hotspot is already running.")
        sys.exit(1)

if __name__ == "__main__":
    main()