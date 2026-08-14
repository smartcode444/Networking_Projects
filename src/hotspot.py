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

