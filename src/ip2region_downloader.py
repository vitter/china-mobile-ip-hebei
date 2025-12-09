import requests
from pathlib import Path

URL = "https://github.com/lionsoul2014/ip2region/raw/refs/heads/master/data/ip2region_v4.xdb"
OUT = Path("../data/ip2region.xdb")

def download_xdb(force=False):
    if OUT.exists() and not force:
        print("ip2region xdb already exists, skip download.")
        return OUT
    OUT.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    OUT.write_bytes(r.content)
    print("Downloaded ip2region xdb to:", OUT.resolve())
    return OUT

if __name__ == "__main__":
    download_xdb()
