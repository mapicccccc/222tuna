# IronGolem Enhanced - Real-time Anti DDoS for Minecraft
# Made by @j0rrdnn - hit me up on Discord if you need help

import os
import json
import subprocess
import datetime
import requests
import time
import threading
import signal
import sys
import re
from collections import defaultdict, deque
from colorama import Fore, Style, init
import psutil
import socket

init(autoreset=True)

# configure this shit
CONFIG = {
    "minecraft_port": 25565,
    "ssh_port": 22,
    "trusted_ips": ["127.0.0.1"],
    "use_discord_webhook": True,
    "discord_webhook_url": "https://discord.com/api/webhooks/1393826650420154378/V_aE0rTM-UKpo4UQPPng7vVGoFoVHVWlpoRJCaUfGs6CG6Y_6SoUwWsLAAAvUqR6g7JX",
    "log_file": "firewall.log",
    "enable_logging": True,
    "monitoring_interval": 5,
    "auto_unban_time": 3600,   # 1 hour
    "rate_limits": {
        "mc_connlimit": 5,
        "mc_flood_seconds": 20,
        "mc_flood_hitcount": 10,
        "global_pps_limit": 1000,
        "syn_flood_limit": 50,
        "connection_tracking_max": 1000
    },
    "thresholds": {
        "cpu_alert": 80,
        "memory_alert": 85,
        "network_alert_mbps": 100,
        "suspicious_connections": 50
    },
    "geolocation_api": "http://ip-api.com/json/",
    "auto_country_block": ["CN", "RU", "KP"],  # countries to block
    "enable_country_blocking": False
}

# IPs that shouldnt exist on the internet
BOGON_IPS = [
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
    "169.254.0.0/16", "172.16.0.0/12", "192.0.2.0/24", "192.168.0.0/16",
    "198.18.0.0/15", "224.0.0.0/4", "240.0.0.0/4"
]

# Known bad ranges - tor exits, proxies, etc
MALICIOUS_RANGES = [
    "185.220.100.0/22",
    "185.220.101.0/24", 
    "199.87.154.0/24",
]

class EnhancedFirewall:
    def __init__(self):
        self.mc_port = CONFIG["minecraft_port"]
        self.ssh_port = CONFIG["ssh_port"]
        self.running = True
        self.blocked_ips = {}
        self.connection_stats = defaultdict(int)
        self.traffic_history = deque(maxlen=60)
        self.banned_ips = {}
        self.whitelist = set(CONFIG["trusted_ips"])
        self.monitoring_thread = None
        
        # handle ctrl+c properly
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, sig, frame):
        self.log("Shutting down...", "INFO")
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        sys.exit(0)

    def log(self, message, tag="LOGS"):
        colors = {
            "LOGS": Fore.GREEN,
            "BLOCKED": Fore.RED,
            "INFO": Fore.CYAN,
            "ERROR": Fore.MAGENTA,
            "WARNING": Fore.YELLOW,
            "CRITICAL": Fore.RED + Style.BRIGHT
        }
        
        color = colors.get(tag.upper(), Fore.WHITE)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = f"{Fore.WHITE}[{color}{tag.upper()}{Fore.WHITE}]"
        log_message = f"{prefix} {Fore.LIGHTBLACK_EX}{timestamp}{Style.RESET_ALL} {Fore.WHITE}{message}"
        print(log_message)

        if CONFIG["enable_logging"]:
            try:
                with open(CONFIG["log_file"], "a") as f:
                    f.write(f"[{tag.upper()}] [{timestamp}] {message}\n")
            except:
                pass

    def alert(self, msg, severity="INFO"):
        if not CONFIG["use_discord_webhook"] or CONFIG["discord_webhook_url"] == "https://discord.com/api/webhooks/your_webhook_here":
            return
            
        try:
            colors = {
                "INFO": 3447003,
                "WARNING": 16776960,
                "CRITICAL": 15158332,
                "BLOCKED": 15158332
            }
            
            embed = {
                "title": f"🛡️ IronGolem Alert - {severity}",
                "description": msg,
                "color": colors.get(severity, 3447003),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "footer": {"text": "IronGolem Enhanced Anti-DDoS"}
            }
            
            payload = {"embeds": [embed]}
            response = requests.post(CONFIG["discord_webhook_url"], json=payload, timeout=10)
            
            if response.status_code != 204:
                self.log(f"Discord webhook failed: {response.status_code}", "ERROR")
                
        except Exception as e:
            self.log(f"Discord webhook error: {e}", "ERROR")

    def run(self, cmd, tag="LOGS", alert=False, alert_severity="INFO"):
        self.log(cmd, tag)
        try:
            result = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True)
            if result.returncode != 0 and result.stderr:
                self.log(f"Command failed: {result.stderr}", "ERROR")
            if alert:
                self.alert(f"🚨 Executed: `{cmd}`", alert_severity)
            return result.returncode == 0
        except Exception as e:
            self.log(f"Error running command: {e}", "ERROR")
            return False

    def get_country_code(self, ip):
        try:
            if ip in self.whitelist or ip.startswith("127.") or ip.startswith("10."):
                return None
            
            response = requests.get(f"{CONFIG['geolocation_api']}{ip}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('countryCode', 'Unknown')
        except:
            pass
        return None

    def block_ip(self, ip, reason="Suspicious activity", duration=None):
        if ip in self.whitelist:
            return False
            
        if duration is None:
            duration = CONFIG["auto_unban_time"]
            
        self.run(f"iptables -I INPUT -s {ip} -j DROP", "BLOCKED", True, "BLOCKED")
        self.banned_ips[ip] = {
            "reason": reason,
            "timestamp": time.time(),
            "duration": duration
        }
        self.alert(f"🚫 Blocked {ip} - {reason}", "BLOCKED")
        return True

    def unblock_ip(self, ip):
        self.run(f"iptables -D INPUT -s {ip} -j DROP", "INFO")
        if ip in self.banned_ips:
            del self.banned_ips[ip]
        self.alert(f"✅ Unblocked {ip}", "INFO")

    def check_auto_unban(self):
        current_time = time.time()
        to_unban = []
        
        for ip, ban_info in self.banned_ips.items():
            if current_time - ban_info["timestamp"] > ban_info["duration"]:
                to_unban.append(ip)
                
        for ip in to_unban:
            self.unblock_ip(ip)
            self.log(f"Auto-unbanned {ip}", "INFO")

    def monitor_system_resources(self):
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        if cpu_percent > CONFIG["thresholds"]["cpu_alert"]:
            self.alert(f"⚠️ High CPU usage: {cpu_percent:.1f}%", "WARNING")
            
        if memory.percent > CONFIG["thresholds"]["memory_alert"]:
            self.alert(f"⚠️ High memory usage: {memory.percent:.1f}%", "WARNING")

    def monitor_network_connections(self):
        try:
            connections = psutil.net_connections(kind='inet')
            connection_counts = defaultdict(int)
            
            for conn in connections:
                if conn.status == 'ESTABLISHED' and conn.laddr.port == self.mc_port:
                    if conn.raddr:
                        connection_counts[conn.raddr.ip] += 1
            
            for ip, count in connection_counts.items():
                if count > CONFIG["thresholds"]["suspicious_connections"]:
                    if ip not in self.banned_ips:
                        self.block_ip(ip, f"Too many connections: {count}", 1800)
                        
        except Exception as e:
            self.log(f"Error monitoring connections: {e}", "ERROR")

    def monitor_traffic(self):
        try:
            net_io = psutil.net_io_counters()
            current_time = time.time()
            
            if hasattr(self, 'last_net_io'):
                time_diff = current_time - self.last_net_time
                bytes_recv_diff = net_io.bytes_recv - self.last_net_io.bytes_recv
                
                if time_diff > 0:
                    mbps = (bytes_recv_diff * 8) / (time_diff * 1024 * 1024)
                    
                    self.traffic_history.append({
                        'timestamp': current_time,
                        'mbps': mbps,
                        'packets_recv': net_io.packets_recv
                    })
                    
                    if mbps > CONFIG["thresholds"]["network_alert_mbps"]:
                        self.alert(f"⚠️ High network traffic: {mbps:.1f} Mbps", "WARNING")
            
            self.last_net_io = net_io
            self.last_net_time = current_time
            
        except Exception as e:
            self.log(f"Error monitoring traffic: {e}", "ERROR")

    def analyze_log_patterns(self):
        try:
            # check for dropped packets in dmesg
            result = subprocess.run(
                "dmesg | grep 'DROPPED:' | tail -20", 
                shell=True, capture_output=True, text=True
            )
            
            if result.stdout:
                ip_pattern = r'SRC=(\d+\.\d+\.\d+\.\d+)'
                dropped_ips = re.findall(ip_pattern, result.stdout)
                
                ip_counts = defaultdict(int)
                for ip in dropped_ips:
                    ip_counts[ip] += 1
                
                for ip, count in ip_counts.items():
                    if count > 10 and ip not in self.banned_ips:
                        self.block_ip(ip, f"High drop count: {count}", 7200)
                        
        except Exception as e:
            self.log(f"Error analyzing logs: {e}", "ERROR")

    def advanced_tcp_protection(self):
        rules = [
            # syn flood protection
            "iptables -A INPUT -p tcp --syn -m limit --limit 1/s --limit-burst 3 -j RETURN",
            "iptables -A INPUT -p tcp --syn -j DROP",
            
            # connection tracking limits
            "iptables -A INPUT -m conntrack --ctstate NEW -m limit --limit 60/s --limit-burst 20 -j ACCEPT",
            "iptables -A INPUT -m conntrack --ctstate NEW -j DROP",
            
            # port scan protection
            "iptables -N port-scan",
            "iptables -A port-scan -p tcp --tcp-flags SYN,ACK,FIN,RST RST -m limit --limit 1/s -j RETURN",
            "iptables -A port-scan -j DROP",
            
            # anti-spoofing
            f"iptables -A INPUT ! -i lo -s 127.0.0.0/8 -j DROP",
            f"iptables -A INPUT -s 224.0.0.0/4 -j DROP",
            f"iptables -A INPUT -d 224.0.0.0/4 -j DROP",
            f"iptables -A INPUT -s 240.0.0.0/5 -j DROP",
            
            # limit rst packets
            "iptables -A INPUT -p tcp --tcp-flags RST RST -m limit --limit 2/s --limit-burst 2 -j ACCEPT",
            "iptables -A INPUT -p tcp --tcp-flags RST RST -j DROP"
        ]
        
        for rule in rules:
            self.run(rule, "BLOCKED", False)

    def create_custom_chains(self):
        chains = [
            "iptables -N ANTI_DDOS",
            "iptables -N RATE_LIMIT", 
            "iptables -N GEO_BLOCK",
            "iptables -N MALICIOUS_BLOCK"
        ]
        
        for chain in chains:
            self.run(chain, "INFO")

    def monitoring_loop(self):
        self.log("Starting monitoring loop", "INFO")
        
        while self.running:
            try:
                self.check_auto_unban()
                self.monitor_system_resources()
                self.monitor_network_connections()
                self.monitor_traffic()
                self.analyze_log_patterns()
                
                # status update every 5 minutes
                if int(time.time()) % 300 == 0:
                    self.log(f"Status: {len(self.banned_ips)} IPs banned", "INFO")
                    
                time.sleep(CONFIG["monitoring_interval"])
                
            except Exception as e:
                self.log(f"Error in monitoring: {e}", "ERROR")
                time.sleep(5)

    def flush(self):
        commands = [
            "iptables -F",
            "iptables -X", 
            "iptables -Z",
            "iptables -t nat -F",
            "iptables -t nat -X",
            "iptables -t mangle -F",
            "iptables -t mangle -X"
        ]
        
        for cmd in commands:
            self.run(cmd, "INFO")

    def allow_trusted(self):
        for ip in CONFIG["trusted_ips"]:
            self.run(f"iptables -I INPUT -s {ip} -j ACCEPT", "LOGS")

    def allow_basics(self):
        ssh = self.ssh_port
        rules = [
            "iptables -A INPUT -i lo -j ACCEPT",
            "iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT",
            f"iptables -A INPUT -p tcp --dport {ssh} -m conntrack --ctstate NEW -m recent --set",
            f"iptables -A INPUT -p tcp --dport {ssh} -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 3 -j DROP",
            f"iptables -A INPUT -p tcp --dport {ssh} -j ACCEPT"
        ]
        
        for rule in rules:
            self.run(rule, "LOGS")

    def block_bogons(self):
        all_ranges = BOGON_IPS + MALICIOUS_RANGES
        for ip_range in all_ranges:
            self.run(f"iptables -A INPUT -s {ip_range} -j DROP", "BLOCKED", True, "BLOCKED")

    def rate_limiting(self):
        rl = CONFIG["rate_limits"]
        port = self.mc_port
        
        rules = [
            # connection limiting
            f"iptables -A INPUT -p tcp --dport {port} -m connlimit --connlimit-above {rl['mc_connlimit']} --connlimit-mask 32 -j DROP",
            
            # flood protection
            f"iptables -A INPUT -p tcp --dport {port} -m recent --name mc-flood --set",
            f"iptables -A INPUT -p tcp --dport {port} -m recent --name mc-flood --update --seconds {rl['mc_flood_seconds']} --hitcount {rl['mc_flood_hitcount']} -j DROP",
            
            # syn flood protection
            f"iptables -A INPUT -p tcp --dport {port} --syn -m recent --name syn-flood --set",
            f"iptables -A INPUT -p tcp --dport {port} --syn -m recent --name syn-flood --update --seconds 1 --hitcount {rl['syn_flood_limit']} -j DROP",
            
            # packet rate limiting
            f"iptables -A INPUT -p tcp --dport {port} -m limit --limit {rl['global_pps_limit']}/s -j ACCEPT",
            f"iptables -A INPUT -p tcp --dport {port} -j DROP"
        ]
        
        for rule in rules:
            self.run(rule, "BLOCKED", False)

    def block_udp_icmp(self):
        rules = [
            f"iptables -A INPUT -p udp --dport {self.mc_port} -j DROP",
            "iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s --limit-burst 2 -j ACCEPT",
            "iptables -A INPUT -p icmp --icmp-type echo-request -j DROP"
        ]
        
        for rule in rules:
            self.run(rule, "BLOCKED", True, "BLOCKED")

    def allow_minecraft(self):
        self.run(f"iptables -A INPUT -p tcp --dport {self.mc_port} -m conntrack --ctstate NEW -j ACCEPT", "LOGS")

    def setup_logging(self):
        rules = [
            "iptables -N LOGGING",
            "iptables -A INPUT -j LOGGING",
            "iptables -A LOGGING -m limit --limit 5/min --limit-burst 10 -j LOG --log-prefix 'DROPPED: ' --log-level 4",
            "iptables -A LOGGING -j DROP"
        ]
        
        for rule in rules:
            self.run(rule, "INFO")

    def persist(self):
        self.run("apt update && apt install -y iptables-persistent", "INFO")
        self.run("netfilter-persistent save", "INFO")

    def print_banner(self):
        banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                    IronGolem Enhanced v2.0                   ║
║                 Real-time Anti-DDoS System                   ║
║                                                              ║
║  Made by @j0rrdnn - Discord me if you need help              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
Port: {self.mc_port:<4} | SSH: {self.ssh_port:<4} | Check interval: {CONFIG['monitoring_interval']}s
        """
        print(banner)

    def apply_protection(self):
        self.print_banner()
        self.log("Setting up firewall protection...", "INFO")
        
        # apply all the rules
        self.flush()
        self.create_custom_chains()
        self.allow_trusted()
        self.allow_basics()
        self.block_bogons()
        self.advanced_tcp_protection()
        self.rate_limiting()
        self.block_udp_icmp()
        self.allow_minecraft()
        self.setup_logging()
        self.persist()
        
        self.log("Protection enabled successfully!", "INFO")
        self.alert("🛡️ IronGolem is now protecting your server!", "INFO")
        
        # start monitoring in background
        self.monitoring_thread = threading.Thread(target=self.monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        # keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.signal_handler(None, None)

def main():
    if os.geteuid() != 0:
        print(f"{Fore.RED}[!] You need to run this as root: sudo python3 main.py{Style.RESET_ALL}")
        sys.exit(1)
    
    # check if we have the tools we need
    tools = ['iptables', 'netfilter-persistent']
    for tool in tools:
        if subprocess.run(f"which {tool}", shell=True, capture_output=True).returncode != 0:
            print(f"{Fore.YELLOW}[!] {tool} not found, will try to install it{Style.RESET_ALL}")
    
    try:
        firewall = EnhancedFirewall()
        firewall.apply_protection()
    except Exception as e:
        print(f"{Fore.RED}[!] Something went wrong: {e}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()