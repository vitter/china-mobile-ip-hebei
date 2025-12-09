from pathlib import Path
from ip2region.xdbReader import XdbReader
from ip2region.xdbSearcher import XdbSearcher

class IP2RegionClient:
    def __init__(self, xdb_path="../data/ip2region.xdb"):
        p = Path(xdb_path)
        if not p.exists():
            raise FileNotFoundError(f"ip2region xdb not found: {p.resolve()}")
        self.searcher = Ip2Region(str(p))

    def lookup_region_str(self, ip: str):
        rec = self.searcher.search(ip)
        if isinstance(rec, dict) and "region" in rec:
            return rec["region"]
        return rec

    def is_hebei_mobile(self, ip: str):
        r = self.lookup_region_str(ip)
        if not r:
            return False
        low = r.replace("省", "").replace("市", "")
        return ("河北" in low) and ("移动" in low)
