#!/usr/bin/env python
"""Discover Huidu HD-C08L async control cards on the local network.

Sends the SDK 2.0/3.0 UDP discovery packet (broadcast, port 10001) and prints
every card that answers: its IP, device ID, and raw reply. Optionally probes
TCP port 10001 on each discovered card to confirm the SDK command channel.

Protocol source: LED/SDK/SDK_FullColor V3.0/SDK_FullColor_test/
SDK_FullColor_2.0.10.test/SDK2.0/SDKLibrary (DataProtocol.cs, CmdType enum)

Usage:
    python discover_card.py                # broadcast scan, 3 s listen
    python discover_card.py --wait 6       # listen 6 s
    python discover_card.py --ip 192.168.1.50   # skip scan, probe one IP
"""

import argparse
import socket
import struct
import sys

UDP_PORT = 10001          # discovery + SDK command port
PROTOCOL_VERSION = 0x1000005
CMD_SEARCH_DEVICE_ASK = 0x1001
SCAN_PACKET = struct.pack("<IH", PROTOCOL_VERSION, CMD_SEARCH_DEVICE_ASK)


def scan(wait_seconds):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(1.0)

    targets = [("<broadcast>", UDP_PORT)]

    print(f"Broadcasting discovery packet to UDP port {UDP_PORT}, listening {wait_seconds}s...")
    replies = {}
    import time
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        for target in targets:
            sock.sendto(SCAN_PACKET, target)
        try:
            data, addr = sock.recvfrom(4096)
        except socket.timeout:
            continue
        ip = addr[0]
        device_id = data[6:21].decode("utf-8", errors="replace").rstrip("\x00") \
            if len(data) >= 21 else "(short reply)"
        if ip not in replies:
            replies[ip] = (device_id, data)
            print(f"  CARD FOUND  ip={ip:<16} id={device_id!r}")
            print(f"              raw={data.hex()}")
    sock.close()
    return replies


def probe_tcp(ip, timeout=3.0):
    """Connect to the SDK port and send protocol version negotiation."""
    negotiation = struct.pack("<HHI", 8, 0x2001, PROTOCOL_VERSION)
    try:
        with socket.create_connection((ip, UDP_PORT), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(negotiation)
            reply = s.recv(256)
            print(f"  TCP {ip}:{UDP_PORT} open, version negotiation reply: {reply.hex()}")
            return True
    except OSError as exc:
        print(f"  TCP {ip}:{UDP_PORT} failed: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait", type=float, default=3.0,
                        help="seconds to listen for replies (default 3)")
    parser.add_argument("--ip", help="skip UDP scan, probe this card IP only")
    args = parser.parse_args()

    if args.ip:
        print(f"Probing card at {args.ip}")
        ok = probe_tcp(args.ip)
        sys.exit(0 if ok else 1)

    cards = scan(args.wait)
    if not cards:
        print("No cards found. Check: card powered, LAN cable to router, "
              "PC on the same network, router firewall allows UDP 10001.")
        sys.exit(1)
    print(f"\n{len(cards)} card(s) found. Probing TCP SDK port on each...")
    reachable = {ip: probe_tcp(ip) for ip in cards}
    print("\nSummary:")
    for ip, (device_id, _) in cards.items():
        status = "TCP OK" if reachable[ip] else "TCP unreachable"
        print(f"  {ip:<16} {device_id!r}  {status}")


if __name__ == "__main__":
    main()
