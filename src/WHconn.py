import subprocess
import re

def run_netsh(command):
    """Execute a netsh command and return its output as a string."""
    try:
        result = subprocess.run(
            ["netsh"] + command.split(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""

def get_hosted_network_status():
    """
    Check if the local Hosted Network (Windows Mobile Hotspot) is active.
    Returns: (is_started, ssid, password, client_count)
    """
    output = run_netsh("wlan show hostednetwork")
    if not output:
        return False, None, None, 0

    started = False
    ssid = None
    password = None
    client_count = 0

    for line in output.splitlines():
        if "Status" in line and ":" in line:
            status = line.split(":", 1)[1].strip().lower()
            started = (status == "started")
        if "SSID" in line and ":" in line and "BSSID" not in line:
            ssid = line.split(":", 1)[1].strip()
        if "Key" in line and ":" in line:
            password = line.split(":", 1)[1].strip()
        if "Number of clients" in line and ":" in line:
            try:
                client_count = int(line.split(":", 1)[1].strip())
            except ValueError:
                client_count = 0

    return started, ssid, password, client_count

def get_client_wifi_info():
    """
    Get info about the current Wi‑Fi connection (client mode).
    Returns: dict with state, ssid, network_type, bssid
    """
    output = run_netsh("wlan show interfaces")
    if not output or "There is no wireless interface" in output:
        return None

    info = {
        "state": None,
        "ssid": None,
        "network_type": None,
        "bssid": None
    }

    patterns = {
        "state": re.compile(r"State\s*:\s*(.+)", re.IGNORECASE),
        "ssid": re.compile(r"SSID\s*:\s*(.+)", re.IGNORECASE),
        "network_type": re.compile(r"Network type\s*:\s*(.+)", re.IGNORECASE),
        "bssid": re.compile(r"BSSID\s*:\s*(.+)", re.IGNORECASE)
    }

    for line in output.splitlines():
        for key, pattern in patterns.items():
            match = pattern.search(line)
            if match:
                info[key] = match.group(1).strip()

    # Normalize state
    if info["state"]:
        info["state"] = info["state"].lower()

    return info

def is_hotspot_network(ssid, network_type):
    """Heuristic to detect if a network is a mobile hotspot."""
    if not ssid:
        return False

    hotspot_keywords = [
        "iPhone", "Android", "Galaxy", "Pixel", "OnePlus",
        "hotspot", "MiFi", "AP", "Access Point", "Mobile Hotspot"
    ]
    ssid_lower = ssid.lower()
    for kw in hotspot_keywords:
        if kw.lower() in ssid_lower:
            return True

    if network_type and ("mobile hotspot" in network_type.lower() or "ad-hoc" in network_type.lower()):
        return True

    return False

def guess_device_name(ssid):
    """Try to extract a device name from a hotspot SSID."""
    if "iPhone" in ssid:
        return "iPhone (Apple)"
    if "Android" in ssid:
        return "Android device"
    if "Galaxy" in ssid:
        return "Samsung Galaxy"
    if "Pixel" in ssid:
        return "Google Pixel"
    if "OnePlus" in ssid:
        return "OnePlus"
    if "MiFi" in ssid:
        return "MiFi hotspot"
    return "Unknown hotspot device"

def main():
    print("=" * 60)
    print("  Wi‑Fi Hotspot Status Checker")
    print("=" * 60)

    # ---------- 1. Check if this device is hosting a hotspot ----------
    hosted_started, hosted_ssid, hosted_password, client_count = get_hosted_network_status()

    # ---------- 2. Check if this device is connected as a client ----------
    client_info = get_client_wifi_info()
    client_state = client_info.get("state") if client_info else None
    client_ssid = client_info.get("ssid") if client_info else None
    client_network_type = client_info.get("network_type") if client_info else None

    # ---------- Determine status ----------
    # Case 1: Device is the hotspot and has at least one client connected
    if hosted_started and client_count > 0:
        print("\n✅ Your device is acting as a Wi‑Fi hotspot.")
        print(f"   Hotspot SSID   : {hosted_ssid if hosted_ssid else 'Unknown'}")
        print(f"   Password       : {hosted_password if hosted_password else 'Unknown'}")
        print(f"   Connected devices: {client_count}")
        print("   (Other devices are connected to your hotspot.)")
        return

    # Case 2: Device is connected as a client to another hotspot
    if client_state == "connected" and client_ssid:
        if is_hotspot_network(client_ssid, client_network_type):
            device_name = guess_device_name(client_ssid)
            print("\n✅ Your device is connected to another device's hotspot.")
            print(f"   Network name   : {client_ssid}")
            print(f"   Device         : {device_name}")
            print(f"   Network type   : {client_network_type if client_network_type else 'Unknown'}")
            return

    # Case 3: Neither – not part of any hotspot scenario
    print("\n❌ Your device is NOT in a hotspot connection scenario.")
    if hosted_started and client_count == 0:
        print("   (Your hotspot is on, but no other devices are connected.)")
    elif hosted_started and client_count > 0:
        # already handled above, but just in case
        pass
    elif client_state == "connected":
        print(f"   You are connected to Wi‑Fi network: {client_ssid}")
        print("   (This does not appear to be a mobile hotspot.)")
    else:
        print("   Wi‑Fi is either off or not connected to any network.")

    # Additional details for debugging
    if hosted_started and client_count == 0:
        print(f"   Hotspot SSID   : {hosted_ssid}")
        print(f"   Password       : {hosted_password}")
    if client_state == "connected":
        print(f"   Connected to   : {client_ssid} (type: {client_network_type})")

if __name__ == "__main__":
    main()