import random
from ipaddress import ip_network

def sample_ips_from_cidr(cidr: str, n: int = 3):
    net = ip_network(cidr)
    # prefer hosts for small nets
    try:
        total = net.num_addresses
    except Exception:
        total = 0
    if total <= 1024:
        hosts = list(net.hosts())
        if not hosts:
            return [str(net.network_address)]
        if len(hosts) <= n:
            return [str(ip) for ip in hosts]
        return [str(random.choice(hosts)) for _ in range(n)]
    else:
        ips = set()
        attempts = 0
        while len(ips) < n and attempts < n*20:
            offset = random.randrange(1, total-1)
            ip = net.network_address + offset
            ips.add(str(ip))
            attempts += 1
        if not ips:
            return [str(net.network_address)]
        return list(ips)
