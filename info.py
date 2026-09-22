import socket

# ASCII-Art Banner
print ("""
████████╗██████╗ ███████╗██╗  ██╗ █████╗ ███████╗
╚══██╔══╝██╔══██╗██╔════╝╚██╗██╔╝██╔══██╗██╔════╝
   ██║   ██████╔╝█████╗   ╚███╔╝ ███████║███████╗
   ██║   ██╔══██╗██╔══╝   ██╔██╗ ██╔══██║╚════██║
   ██║   ██║  ██║███████╗██╔╝ ██╗██║  ██║███████║
   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
                                                 
""")

def find_open_ports(host):
    print(f"Scanning {host} for open ports...")
    open_ports = []
    common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 3306, 8080]

    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            if result == 0:
                open_ports.append(port)
            sock.close()
        except Exception as e:
            print(f"Error scanning port {port}: {e}")
    
    if open_ports:
        print(f"Open ports found: {open_ports}")
    else:
        print("No common ports are open.")

    return open_ports

def get_server_info(ip):
    try:
        server_ip = socket.gethostbyname(ip)
        print("\n--- Server Information ---")
        print(f"IP Address: {server_ip}")
        open_ports = find_open_ports(server_ip)
        if open_ports:
            print(f"Suggested Port: {open_ports[0]}")
        else:
            print("No open port found.")
    except socket.gaierror:
        print("Invalid IP address or domain name!")

def main():
    print("Enter the IP address or domain name of the server:")
    server_ip = input("IP/Domain: ")
    get_server_info(server_ip)

if __name__ == "__main__":
    main()
