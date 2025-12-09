#!/usr/bin/env python3
import argparse
from asn_loader import load_asns_from_file
from fetch_prefixes_async import get_prefixes_sync
from ip2region_downloader import download_xdb
from ip2region_client import IP2RegionClient
from scanner_advanced import scan_prefixes_concurrent
from pathlib import Path
import json, csv

def summarize_by_province(prefixes, ip2):
    stats = {}
    for cidr in prefixes:
        try:
            net = __import__('ipaddress').ip_network(cidr)
            ip = str(net.network_address)
            region = ip2.lookup_region_str(ip) or ''
            parts = region.split('|')
            prov = parts[1] if len(parts) > 1 else '未知'
            prov = prov.replace('省','').replace('市','')
            stats[prov] = stats.get(prov, 0) + 1
        except Exception:
            stats['未知'] = stats.get('未知', 0) + 1
    return stats

def generate_stats_markdown(stats: dict):
    lines = ['| 省份 | 命中 IP 段数 |', '|------|------------:|']
    for p, count in sorted(stats.items(), key=lambda x: -x[1]):
        lines.append(f'| {p} | {count} |')
    return '\n'.join(lines)

def save_results(results, out_dir=Path('../output')):
    out_dir.mkdir(parents=True, exist_ok=True)
    txt_path = out_dir / 'hebei_cmcc_cidr.txt'
    csv_path = out_dir / 'hebei_cmcc_cidr.csv'
    json_path = out_dir / 'hebei_cmcc_cidr.json'

    # txt: include high + medium
    lines = [r['cidr'] for r in results if r['status'] != 'none']
    txt_path.write_text('\n'.join(lines), encoding='utf-8')

    # csv: detailed
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['cidr','status','hits','samples','sampled_ips'])
        writer.writeheader()
        for r in results:
            writer.writerow({
                'cidr': r['cidr'],
                'status': r['status'],
                'hits': r['hits'],
                'samples': r['samples'],
                'sampled_ips': '|'.join(r['sampled'])
            })
    # json
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    return txt_path, csv_path, json_path

def update_readme_with_stats(readme_path: Path, stats_md: str):
    if not readme_path.exists():
        return
    content = readme_path.read_text(encoding='utf-8')
    marker_start = '<!-- STATS_START -->'
    marker_end = '<!-- STATS_END -->'
    new_section = f"""\n## 按省份统计（自动生成）\n\n{stats_md}\n\n"""
    if marker_start in content and marker_end in content:
        pre = content.split(marker_start)[0]
        post = content.split(marker_end)[1]
        content = pre + marker_start + "\n" + new_section + marker_end + post
    else:
        content += '\n' + marker_start + '\n' + new_section + marker_end + '\n'
    readme_path.write_text(content, encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description='Scan CMCC prefixes and filter Hebei Mobile')
    parser.add_argument('--cmcc', default='../data/cmcc.txt')
    parser.add_argument('--sample', type=int, default=3)
    parser.add_argument('--use-cache', action='store_true')
    parser.add_argument('--fetch-concurrency', type=int, default=20)
    parser.add_argument('--scan-workers', type=int, default=24)
    args = parser.parse_args()

    # ensure cmcc exists
    cmcc = Path(args.cmcc)
    if not cmcc.exists():
        raise FileNotFoundError(f'cmcc not found: {cmcc.resolve()}')

    # download ip2region xdb if needed
    download_xdb()

    # load asns and fetch prefixes
    asns = load_asns_from_file(str(cmcc))
    prefixes = get_prefixes_sync(asns, use_cache=args.use_cache, concurrency=args.fetch_concurrency)

    ip2 = IP2RegionClient(xdb_path='../data/ip2region.xdb')

    results = scan_prefixes_concurrent(prefixes, ip2, sample_per_cidr=args.sample, max_workers=args.scan_workers)

    txt_path, csv_path, json_path = save_results(results)

    # summarize by province using positive prefixes (high + medium)
    positives = [r['cidr'] for r in results if r['status'] != 'none']
    stats = summarize_by_province(positives, ip2)
    stats_md = generate_stats_markdown(stats)

    # update README with stats table
    update_readme_with_stats(Path('../README.md'), stats_md)

    print('Done. Outputs:', txt_path, csv_path, json_path)

if __name__ == '__main__':
    main()
