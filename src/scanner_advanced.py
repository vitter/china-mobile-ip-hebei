from ip2region_client import IP2RegionClient
from tqdm import tqdm
from sample_ips import sample_ips_from_cidr
from concurrent.futures import ThreadPoolExecutor, as_completed

def scan_single(cidr, ip2, sample_per_cidr=3):
    ips = sample_ips_from_cidr(cidr, n=sample_per_cidr)
    hits = 0
    for ip in ips:
        try:
            if ip2.is_hebei_mobile(ip):
                hits += 1
        except Exception:
            continue
    if hits == 0:
        status = 'none'
    elif hits == len(ips):
        status = 'high'
    else:
        status = 'medium'
    return {
        'cidr': cidr,
        'sampled': ips,
        'hits': hits,
        'samples': len(ips),
        'status': status
    }

def scan_prefixes_concurrent(prefixes, ip2, sample_per_cidr=3, max_workers=24):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(scan_single, p, ip2, sample_per_cidr): p for p in prefixes}
        for fut in tqdm(as_completed(futures), total=len(futures), desc='Scanning CIDR'):
            try:
                res = fut.result()
                results.append(res)
            except Exception:
                continue
    # sort: high -> medium -> none
    results_sorted = sorted(results, key=lambda x: (0 if x['status']=='high' else 1 if x['status']=='medium' else 2, x['cidr']))
    return results_sorted
