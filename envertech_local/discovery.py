#discovery.py
import asyncio
import socket
import netifaces
import logging

_LOGGER = logging.getLogger(__name__)

UDP_DISCOVERY_MSG = b"LOCALCON-1508-READ"
UDP_DISCOVERY_MSG_WIFI = b"www.usr.cn"

DEST_PORTS = {
    "localcon": 48889,
    "wifi": 48899,
}

RECV_BUFFER = 1024


def get_interface_ips():
    """Get list of non-loopback, non-virtual IPv4 addresses."""
    skip_ifaces = {"docker0", "br-", "veth"}
    ips = []
    for iface in netifaces.interfaces():
        if any(iface.startswith(prefix) for prefix in skip_ifaces):
            continue
        addrs = netifaces.ifaddresses(iface)
        inet_addrs = addrs.get(netifaces.AF_INET, [])
        for addr in inet_addrs:
            ip = addr.get("addr")
            if ip and not ip.startswith("127."):
                ips.append(ip)
    return ips



def decode_localcon_response(data):
    ip = '.'.join(str(b) for b in data[:4])
    serial = ''.join(f"{b:02X}" for b in data[6:10])
    return {
        "ip": ip,
        "serial_number": serial,
        "mac": None,  # No MAC in LOCALCON response
        "source": "ethernet"
    }


def decode_wifi_response(data):
    text = data.decode("utf-8", errors="ignore")
    parts = text.split(",")
    if len(parts) >= 3:
        return {
            "ip": parts[0].strip(),
            "mac": parts[1].strip(),
            "serial_number": parts[2].strip(),
            "source": "wifi"
        }
    return None


async def send_and_receive(loop, interface_ip, msg_type, msg, dest_port, timeout):
    discovered = []
    seen_serials = set()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        sock.bind((interface_ip, 0))  # Let OS pick the port
        local_port = sock.getsockname()[1]
        _LOGGER.debug(f"[{msg_type}] Bound to {interface_ip}:{local_port}")

        # Send broadcast message
        sock.sendto(msg, ("255.255.255.255", dest_port))
        _LOGGER.info(f"[{msg_type}] Sent from {interface_ip}:{local_port} to 255.255.255.255:{dest_port}")

        end_time = loop.time() + timeout

        while loop.time() < end_time:
            try:
                future = loop.sock_recvfrom(sock, RECV_BUFFER)
                data, addr = await asyncio.wait_for(future, timeout=end_time - loop.time())
                _LOGGER.debug(f"[{msg_type}] Received from {addr}: {data}")

                if msg_type == "localcon":
                    try:
                        device = decode_localcon_response(data)
                    except Exception as e:
                        _LOGGER.warning(f"[{msg_type}] Failed to decode binary response: {e}")
                        continue
                elif msg_type == "wifi":
                    try:
                        device = decode_wifi_response(data)
                        if not device:
                            continue
                    except Exception as e:
                        _LOGGER.warning(f"[{msg_type}] Failed to decode text response: {e}")
                        continue
                else:
                    continue

                serial = device["serial_number"]
                if serial and serial not in seen_serials:
                    seen_serials.add(serial)
                    discovered.append(device)

            except asyncio.TimeoutError:
                break
    finally:
        sock.close()

    return discovered


async def discover_devices_async(timeout=3):
    interface_ips = get_interface_ips()

    loop = asyncio.get_running_loop()
    tasks = []

    for interface_ip in interface_ips:
        tasks.append(
            send_and_receive(loop, interface_ip, "localcon", UDP_DISCOVERY_MSG, DEST_PORTS["localcon"], timeout)
        )
        tasks.append(
            send_and_receive(loop, interface_ip, "wifi", UDP_DISCOVERY_MSG_WIFI, DEST_PORTS["wifi"], timeout)
        )

    results = await asyncio.gather(*tasks)

    # Flatten and deduplicate
    discovered = []
    seen_serials = set()
    for device_list in results:
        for device in device_list:
            if device["serial_number"] not in seen_serials:
                discovered.append(device)
                seen_serials.add(device["serial_number"])

    return discovered
