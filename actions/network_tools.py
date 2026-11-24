"""
AEGIS Network Tools & Device Management
Network discovery, ARP-based device mapping, hostname resolution, and Wake-on-LAN (WOL) magic packet dispatch.
"""

import os
import re
import socket
import struct
import subprocess
import concurrent.futures
from typing import List, Dict, Any, Optional, Tuple

# Curated lookup table of common Organizationally Unique Identifiers (OUI)
OUI_VENDORS = {
    # Apple
    "00:03:93": "Apple", "00:05:02": "Apple", "00:0a:95": "Apple", "00:10:fa": "Apple",
    "00:14:51": "Apple", "00:16:cb": "Apple", "00:17:f2": "Apple", "00:19:e3": "Apple",
    "00:1b:63": "Apple", "00:1c:b3": "Apple", "00:1d:4f": "Apple", "00:1e:52": "Apple",
    "00:1f:5b": "Apple", "00:1f:f3": "Apple", "00:21:e9": "Apple", "00:22:41": "Apple",
    "00:23:12": "Apple", "00:23:32": "Apple", "00:23:6c": "Apple", "00:23:df": "Apple",
    "00:24:36": "Apple", "00:25:00": "Apple", "00:25:4b": "Apple", "00:25:bc": "Apple",
    "00:26:08": "Apple", "00:26:4a": "Apple", "00:26:b0": "Apple", "00:26:bb": "Apple",
    "3c:07:54": "Apple", "3c:15:c2": "Apple", "3c:22:fb": "Apple", "70:ef:00": "Apple",
    "88:66:5a": "Apple", "a4:83:e7": "Apple", "ac:de:48": "Apple", "bc:d1:d3": "Apple",
    "d4:61:9d": "Apple", "dc:a9:04": "Apple", "e0:ac:cb": "Apple", "f0:18:98": "Apple",
    "f4:5c:89": "Apple", "f8:ff:c2": "Apple",

    # Cisco
    "00:00:0c": "Cisco", "00:01:42": "Cisco", "00:01:43": "Cisco", "00:01:63": "Cisco",
    "00:01:64": "Cisco", "00:01:96": "Cisco", "00:01:97": "Cisco", "00:01:c7": "Cisco",
    "00:01:c9": "Cisco", "00:02:16": "Cisco", "00:02:17": "Cisco", "00:02:4b": "Cisco",
    "00:02:4c": "Cisco", "00:02:7d": "Cisco", "00:02:7e": "Cisco", "00:02:ba": "Cisco",
    "00:02:fc": "Cisco", "00:02:fd": "Cisco", "00:03:31": "Cisco", "00:03:32": "Cisco",
    "00:03:6b": "Cisco", "00:03:6c": "Cisco", "00:1a:a1": "Cisco", "00:1b:0d": "Cisco",
    "00:1c:0e": "Cisco", "00:1d:45": "Cisco", "00:21:55": "Cisco", "00:22:55": "Cisco",
    "00:24:14": "Cisco", "00:26:0b": "Cisco", "50:06:04": "Cisco", "70:10:5c": "Cisco",
    "88:f0:31": "Cisco", "d4:b4:c0": "Cisco",

    # Dell
    "00:14:22": "Dell", "00:18:8b": "Dell", "00:1a:a0": "Dell", "00:21:70": "Dell",
    "00:24:e8": "Dell", "00:26:b9": "Dell", "18:03:73": "Dell", "18:66:da": "Dell",
    "20:4e:f6": "Dell", "24:b6:fd": "Dell", "34:17:eb": "Dell", "44:a8:42": "Dell",
    "5c:f9:dd": "Dell", "74:86:7a": "Dell", "84:7b:eb": "Dell", "90:b1:1c": "Dell",
    "a4:ba:db": "Dell", "b8:ac:6f": "Dell", "bc:30:5b": "Dell", "d4:be:d9": "Dell",
    "e0:db:55": "Dell", "f8:bc:12": "Dell",

    # HP
    "00:01:e6": "HP", "00:02:a5": "HP", "00:08:02": "HP", "00:0b:cd": "HP",
    "00:0e:7f": "HP", "00:11:85": "HP", "00:12:79": "HP", "00:14:38": "HP",
    "00:15:60": "HP", "00:16:35": "HP", "00:17:a4": "HP", "00:18:fe": "HP",
    "00:1a:4b": "HP", "00:1e:0b": "HP", "00:21:5a": "HP", "00:22:64": "HP",
    "00:23:7d": "HP", "00:24:81": "HP", "00:25:b3": "HP", "00:26:55": "HP",
    "3c:d9:2b": "HP", "9c:b6:54": "HP", "b4:b5:2f": "HP", "d8:9d:67": "HP",

    # Intel
    "00:02:b3": "Intel", "00:03:47": "Intel", "00:04:23": "Intel", "00:0e:0c": "Intel",
    "00:13:02": "Intel", "00:13:e8": "Intel", "00:15:00": "Intel", "00:15:17": "Intel",
    "00:16:6f": "Intel", "00:16:76": "Intel", "00:19:d1": "Intel", "00:1b:21": "Intel",
    "00:1c:c0": "Intel", "00:1e:67": "Intel", "00:21:6a": "Intel", "00:23:14": "Intel",
    "00:24:d7": "Intel", "28:70:4e": "Intel", "34:13:e8": "Intel", "3c:fd:fe": "Intel",
    "48:51:b7": "Intel", "4c:79:6e": "Intel", "68:05:ca": "Intel", "80:86:f2": "Intel",
    "8c:ec:4b": "Intel", "a0:36:9f": "Intel", "a4:4e:31": "Intel",

    # Raspberry Pi
    "28:cd:c1": "Raspberry Pi", "b8:27:eb": "Raspberry Pi", "d8:3a:dd": "Raspberry Pi",
    "dc:a6:32": "Raspberry Pi", "e4:5f:01": "Raspberry Pi",

    # Espressif (ESP8266 / ESP32)
    "18:fe:34": "Espressif", "24:0a:c4": "Espressif", "24:6f:28": "Espressif",
    "24:b2:de": "Espressif", "2c:3a:e8": "Espressif", "30:ae:a4": "Espressif",
    "80:7d:3a": "Espressif", "a4:cf:12": "Espressif", "ac:67:b2": "Espressif",
    "b4:e6:2d": "Espressif", "bc:dd:c2": "Espressif", "cc:50:e3": "Espressif",
    "d8:a0:1d": "Espressif", "dc:4f:22": "Espressif",

    # TP-Link
    "00:1d:0f": "TP-Link", "00:25:86": "TP-Link", "14:cc:20": "TP-Link", "18:a6:f7": "TP-Link",
    "1c:3b:f3": "TP-Link", "30:b5:c2": "TP-Link", "50:c7:bf": "TP-Link", "50:d8:55": "TP-Link",
    "54:e6:fc": "TP-Link", "70:4f:57": "TP-Link", "98:da:c4": "TP-Link", "a0:f3:c1": "TP-Link",
    "b0:95:75": "TP-Link", "c0:4a:00": "TP-Link", "c4:6e:1f": "TP-Link", "d8:07:b6": "TP-Link",
    "e8:48:b8": "TP-Link", "ec:08:6b": "TP-Link", "ec:17:2f": "TP-Link", "f4:f2:6d": "TP-Link",

    # Samsung
    "00:02:78": "Samsung", "00:07:ab": "Samsung", "00:09:18": "Samsung", "00:0d:ae": "Samsung",
    "00:12:47": "Samsung", "00:15:99": "Samsung", "00:16:32": "Samsung", "00:16:6b": "Samsung",
    "00:17:c9": "Samsung", "00:17:d5": "Samsung", "00:18:af": "Samsung", "00:1a:8a": "Samsung",
    "00:1c:43": "Samsung", "00:1d:25": "Samsung", "00:1e:7d": "Samsung", "00:1f:cc": "Samsung",
    "00:21:19": "Samsung", "00:21:4c": "Samsung", "00:23:39": "Samsung", "00:23:99": "Samsung",
    "00:24:54": "Samsung", "00:24:90": "Samsung", "00:24:91": "Samsung", "00:25:66": "Samsung",
    "00:25:67": "Samsung", "00:26:37": "Samsung", "00:26:5d": "Samsung", "34:23:87": "Samsung",
    "48:44:f7": "Samsung", "5c:e8:eb": "Samsung", "84:25:19": "Samsung", "a0:0b:ba": "Samsung",
    "cc:07:ab": "Samsung",

    # Microsoft
    "00:03:ff": "Microsoft", "00:0d:3a": "Microsoft", "00:12:5a": "Microsoft",
    "00:15:5d": "Microsoft", "00:17:fa": "Microsoft", "00:1d:d8": "Microsoft",
    "00:22:48": "Microsoft", "00:25:ae": "Microsoft", "00:50:f2": "Microsoft",
    "28:18:78": "Microsoft", "28:56:5a": "Microsoft", "60:45:bd": "Microsoft",
    "70:b5:e8": "Microsoft", "7c:1e:52": "Microsoft", "dc:b4:c4": "Microsoft",

    # Google
    "00:1a:11": "Google", "3c:5a:37": "Google", "54:60:09": "Google", "70:ee:50": "Google",
    "94:eb:cd": "Google", "a4:77:33": "Google", "d8:6c:63": "Google", "f4:03:04": "Google",
    "f4:f5:d8": "Google", "f8:8f:ca": "Google",

    # Amazon
    "00:fc:8b": "Amazon", "0c:47:c9": "Amazon", "18:74:2e": "Amazon", "38:f7:3d": "Amazon",
    "40:b4:cd": "Amazon", "44:65:0d": "Amazon", "50:dc:e7": "Amazon", "68:37:e9": "Amazon",
    "68:54:5a": "Amazon", "74:75:48": "Amazon", "84:d6:d0": "Amazon", "ac:63:be": "Amazon",
    "fc:65:de": "Amazon",

    # Asus & Netgear & D-Link & Realtek
    "00:09:5b": "Netgear", "00:0f:b5": "Netgear", "00:14:6c": "Netgear", "00:18:4d": "Netgear",
    "00:1b:2f": "Netgear", "00:1e:2a": "Netgear", "00:1f:33": "Netgear", "00:22:3f": "Netgear",
    "00:24:b2": "Netgear", "00:26:f2": "Netgear", "04:a1:51": "Netgear", "08:02:8e": "Netgear",
    "10:da:43": "Netgear", "20:0c:c8": "Netgear", "20:4e:7f": "Netgear", "28:80:88": "Netgear",
    "00:0c:6e": "Asus", "00:0e:a6": "Asus", "00:11:2f": "Asus", "00:11:d8": "Asus",
    "00:13:d4": "Asus", "00:15:f2": "Asus", "00:17:31": "Asus", "00:18:f3": "Asus",
    "00:1a:92": "Asus", "00:1b:fc": "Asus", "00:1d:60": "Asus", "00:1e:8c": "Asus",
    "00:1f:c6": "Asus", "00:22:15": "Asus", "00:23:54": "Asus", "00:24:8c": "Asus",
    "00:07:0d": "Realtek", "00:0e:2e": "Realtek", "00:18:e7": "Realtek", "00:26:18": "Realtek",
    "52:54:00": "Realtek / QEMU", "74:da:38": "Realtek",
    "00:05:5d": "D-Link", "00:0d:88": "D-Link", "00:13:46": "D-Link", "00:15:e9": "D-Link",
    "00:17:9a": "D-Link", "00:19:5b": "D-Link", "00:1b:11": "D-Link", "00:1c:f0": "D-Link",
    "00:1e:58": "D-Link", "00:21:91": "D-Link", "00:22:b0": "D-Link", "00:24:01": "D-Link",
    "00:26:5a": "D-Link", "14:d6:4d": "D-Link", "1c:7e:e5": "D-Link", "28:10:7b": "D-Link",

    # Virtualization
    "00:05:69": "VMware", "00:0c:29": "VMware", "00:1c:14": "VMware", "00:50:56": "VMware",
    "08:00:27": "Oracle VirtualBox",

    # Huawei & Xiaomi & Sony & Ubiquiti
    "00:18:82": "Huawei", "00:1e:10": "Huawei", "00:25:9e": "Huawei", "00:46:4b": "Huawei",
    "04:25:c5": "Huawei", "04:f9:38": "Huawei", "0c:37:dc": "Huawei", "10:1b:54": "Huawei",
    "10:47:80": "Huawei", "20:0b:c7": "Huawei", "20:f3:a3": "Huawei", "24:69:68": "Huawei",
    "28:31:52": "Huawei", "2c:9d:1e": "Huawei", "34:00:a3": "Huawei", "38:f8:89": "Huawei",
    "00:9e:c8": "Xiaomi", "04:cf:8c": "Xiaomi", "10:2a:b3": "Xiaomi", "14:f6:5a": "Xiaomi",
    "18:59:36": "Xiaomi", "28:6c:07": "Xiaomi", "34:ce:00": "Xiaomi", "50:64:2b": "Xiaomi",
    "58:44:98": "Xiaomi", "64:09:80": "Xiaomi", "74:23:44": "Xiaomi", "78:11:dc": "Xiaomi",
    "7c:49:eb": "Xiaomi", "88:c3:97": "Xiaomi", "9c:99:a0": "Xiaomi", "a4:45:19": "Xiaomi",
    "c4:0b:cb": "Xiaomi",
    "00:01:4a": "Sony", "00:04:1f": "Sony", "00:0a:d9": "Sony", "00:13:15": "Sony",
    "00:15:c1": "Sony", "00:19:c5": "Sony", "00:1a:80": "Sony", "00:1d:0d": "Sony",
    "00:1e:dc": "Sony", "00:21:9e": "Sony", "00:24:8d": "Sony", "f0:bf:97": "Sony",
    "00:15:6d": "Ubiquiti", "00:27:22": "Ubiquiti", "24:a4:3c": "Ubiquiti", "44:d9:e7": "Ubiquiti",
    "68:72:51": "Ubiquiti", "74:83:c2": "Ubiquiti", "78:8a:20": "Ubiquiti", "80:2a:a8": "Ubiquiti",
    "b4:fb:e4": "Ubiquiti", "dc:9f:db": "Ubiquiti", "e0:63:da": "Ubiquiti", "f0:9f:c2": "Ubiquiti"
}


class LANScanner:
    """Discovers active local area network devices using native ARP tables and hostname resolution."""

    @staticmethod
    def _get_local_ip() -> str:
        """Auto-detects the machine's primary outbound IPv4 address."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Does not send actual traffic, only determines routing interface
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    @staticmethod
    def _resolve_hostname(ip: str) -> str:
        """Attempts to resolve the fully qualified domain name or hostname for a given IP."""
        try:
            fqdn = socket.getfqdn(ip)
            if fqdn and fqdn != ip:
                return fqdn
            # Fallback reverse DNS lookup
            host, _, _ = socket.gethostbyaddr(ip)
            return host if host else "Unknown"
        except Exception:
            return "Unknown"

    @staticmethod
    def _lookup_vendor(mac: str) -> str:
        """Looks up the manufacturer vendor from the MAC address OUI prefix."""
        clean_mac = re.sub(r"[^0-9a-fA-F]", "", mac).lower()
        if len(clean_mac) < 6:
            return "Unknown"

        oui = f"{clean_mac[0:2]}:{clean_mac[2:4]}:{clean_mac[4:6]}"
        if oui in OUI_VENDORS:
            return OUI_VENDORS[oui]

        # Check for locally administered / randomized MAC (bit 1 of byte 0 is 1)
        try:
            first_byte = int(clean_mac[0:2], 16)
            if first_byte & 0x02:
                return "Private / Randomized MAC"
        except Exception:
            pass

        return "Unknown"

    @staticmethod
    def _is_valid_device_ip(ip: str) -> bool:
        """Checks whether an IP is a valid unicast host address (excluding multicast/broadcast/loopback)."""
        try:
            octets = [int(p) for p in ip.split(".")]
            if len(octets) != 4:
                return False
            # Exclude loopback (127.x.x.x)
            if octets[0] == 127:
                return False
            # Exclude multicast (224.0.0.0 to 239.255.255.255)
            if 224 <= octets[0] <= 239:
                return False
            # Exclude all-hosts broadcast (255.255.255.255) or network zero (0.x.x.x)
            if ip == "255.255.255.255" or octets[0] == 0:
                return False
            return True
        except Exception:
            return False

    @staticmethod
    def _is_valid_device_mac(mac: str) -> bool:
        """Checks whether a MAC address is a valid unicast physical address."""
        clean_mac = re.sub(r"[^0-9a-fA-F]", "", mac).lower()
        if len(clean_mac) != 12:
            return False
        # Exclude broadcast MAC
        if clean_mac == "ffffffffffff":
            return False
        # Exclude all-zeros
        if clean_mac == "000000000000":
            return False
        # Exclude multicast MACs (01-00-5e-...)
        if clean_mac.startswith("01005e"):
            return False
        return True

    @classmethod
    def scan_network(cls, subnet: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scans the local network by executing `arp -a` via subprocess, parsing entries,
        filtering devices based on the target subnet, resolving hostnames, and identifying vendors.

        :param subnet: Optional subnet prefix or CIDR (e.g. '192.168.1', '10.1.0.0/16').
                       If None, auto-detects the active local subnet.
        :return: List of device dictionaries: [{'ip': '...', 'mac': '...', 'hostname': '...', 'vendor': '...'}, ...]
        """
        devices: List[Dict[str, Any]] = []
        local_ip = cls._get_local_ip()

        # Determine target subnet filter prefix if not explicitly specified
        target_subnet = subnet.strip() if subnet else None
        if not target_subnet:
            # Derive prefix from detected local IP (e.g. '192.168.1.' or '10.1.')
            parts = local_ip.split(".")
            if len(parts) == 4:
                if parts[0] == "10":
                    target_subnet = f"{parts[0]}.{parts[1]}."
                elif parts[0] == "172" and 16 <= int(parts[1]) <= 31:
                    target_subnet = f"{parts[0]}.{parts[1]}."
                else:
                    target_subnet = f"{parts[0]}.{parts[1]}.{parts[2]}."

        try:
            # Execute ARP table query
            if os.name == "nt":
                proc = subprocess.run(
                    ["arp", "-a"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                )
                arp_output = proc.stdout
            else:
                proc = subprocess.run(
                    ["arp", "-a"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                arp_output = proc.stdout

            # Regex pattern matching IP and MAC address pairs
            arp_pattern = re.compile(
                r"([0-9]{1,3}(?:\.[0-9]{1,3}){3})\s+([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})",
                re.IGNORECASE
            )

            raw_entries: List[Tuple[str, str]] = []
            seen_ips = set()

            for match in arp_pattern.finditer(arp_output):
                ip = match.group(1).strip()
                raw_mac = match.group(2).strip()

                if not cls._is_valid_device_ip(ip):
                    continue
                if not cls._is_valid_device_mac(raw_mac):
                    continue
                if ip in seen_ips:
                    continue

                # Apply subnet filtering if applicable
                if target_subnet:
                    # Clean subnet check for CIDR or prefix notation
                    clean_filter = target_subnet.split("/")[0].rstrip(".")
                    if not ip.startswith(clean_filter):
                        continue

                # Format standard MAC representation (xx:xx:xx:xx:xx:xx)
                clean_mac = re.sub(r"[^0-9a-fA-F]", "", raw_mac).lower()
                formatted_mac = ":".join(clean_mac[i:i+2] for i in range(0, 12, 2))

                seen_ips.add(ip)
                raw_entries.append((ip, formatted_mac))

            # Resolve hostnames in parallel for speed
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(raw_entries) or 1, 10)) as executor:
                future_to_entry = {
                    executor.submit(cls._resolve_hostname, ip): (ip, mac)
                    for ip, mac in raw_entries
                }
                for future in concurrent.futures.as_completed(future_to_entry):
                    ip, mac = future_to_entry[future]
                    try:
                        hostname = future.result()
                    except Exception:
                        hostname = "Unknown"

                    vendor = cls._lookup_vendor(mac)
                    devices.append({
                        "ip": ip,
                        "mac": mac,
                        "hostname": hostname,
                        "vendor": vendor
                    })

            # Sort results by IP address
            devices.sort(key=lambda d: [int(x) for x in d["ip"].split(".") if x.isdigit()])

        except Exception as e:
            print(f"[LANScanner Error] scan_network failed: {e}")

        return devices


class WakeOnLAN:
    """Dispatches Wake-on-LAN (WOL) magic packets over UDP broadcast to power on network devices."""

    @staticmethod
    def wake(mac_address: str, broadcast_ip: str = "255.255.255.255", port: int = 9) -> Dict[str, Any]:
        """
        Sends a standard Wake-on-LAN magic packet to power on a target device.

        The magic packet payload contains:
        - 6 bytes of 0xFF (synchronization header)
        - 16 repetitions of the target device's 6-byte MAC address
        Total: 102 bytes broadcasted via UDP (default port 9).

        :param mac_address: Target MAC address in any standard notation (e.g. 'AA:BB:CC:DD:EE:FF', 'AA-BB-CC-DD-EE-FF', 'aabbccddeeff').
        :param broadcast_ip: Broadcast destination address (default '255.255.255.255').
        :param port: Destination UDP port (default 9).
        :return: Execution summary dictionary with success status, message, and details.
        """
        try:
            # Sanitize and validate MAC address string
            clean_mac = re.sub(r"[^0-9a-fA-F]", "", mac_address)
            if len(clean_mac) != 12:
                return {
                    "success": False,
                    "status": "INVALID_MAC",
                    "message": f"Invalid MAC address format: '{mac_address}'. Must contain exactly 12 hexadecimal characters.",
                    "mac": mac_address
                }

            # Standardized MAC formatting (AA:BB:CC:DD:EE:FF)
            formatted_mac = ":".join(clean_mac[i:i+2].upper() for i in range(0, 12, 2))

            # Pack 6 raw MAC bytes
            mac_bytes = bytes.fromhex(clean_mac)

            # Construct 102-byte WOL Magic Packet payload
            header = struct.pack("!6B", *([0xFF] * 6))
            payload = header + (mac_bytes * 16)

            # Transmit via UDP broadcast socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(payload, (broadcast_ip, port))

            return {
                "success": True,
                "status": "SUCCESS",
                "message": f"Wake-on-LAN magic packet successfully transmitted to {formatted_mac} via {broadcast_ip}:{port}.",
                "mac": formatted_mac,
                "broadcast_ip": broadcast_ip,
                "port": port
            }

        except Exception as e:
            print(f"[WakeOnLAN Error] Failed to transmit WOL packet: {e}")
            return {
                "success": False,
                "status": "ERROR",
                "message": f"Failed to send Wake-on-LAN packet to '{mac_address}': {str(e)}",
                "mac": mac_address,
                "error": str(e)
            }


if __name__ == "__main__":
    print("=" * 60)
    print("AEGIS Network Tools - LAN Scanner & Wake-on-LAN Diagnostic")
    print("=" * 60)

    # 1. Test LAN Scanner
    local_ip = LANScanner._get_local_ip()
    print(f"Detected Local Outbound IP: {local_ip}")
    print("\nScanning local area network for active devices...")

    discovered_devices = LANScanner.scan_network()
    print(f"\nDiscovered Devices ({len(discovered_devices)} found):")
    print("-" * 60)
    print(f"{'IP Address':<18} {'MAC Address':<20} {'Hostname':<22} {'Vendor'}")
    print("-" * 60)

    for dev in discovered_devices:
        print(f"{dev['ip']:<18} {dev['mac']:<20} {dev['hostname']:<22} {dev['vendor']}")

    print("-" * 60)

    # 2. Test WakeOnLAN
    test_mac = "AA:BB:CC:DD:EE:FF"
    print(f"\nTesting Wake-on-LAN transmission to '{test_mac}'...")
    wol_result = WakeOnLAN.wake(test_mac)
    print(f"WOL Result: {wol_result['status']} -> {wol_result['message']}")
    print("=" * 60)
