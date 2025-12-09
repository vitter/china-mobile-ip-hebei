import aiohttp
import asyncio
import json
from pathlib import Path
from typing import Dict, List

CACHE_PATH = Path("../data/prefixes_cache.json")
API_URL = "https://bgp.tools/as/{asn}?v=1"

def load_cache() -> Dict[str, List[str]]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}

def save_cache(cache: Dict[str, List[str]]):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
async def fetch_one(session: aiohttp.ClientSession, asn: int):
    url = API_URL.format(asn=asn)
    async with session.get(url, timeout=20) as r:
        data = await r.json()
        prefixes = data.get("v4_prefixes", [])
        return str(asn), sorted(set(prefixes))

async def fetch_all(asns: List[int], use_cache=True, concurrency=20):
    cache = load_cache() if use_cache else {}
    tasks = []
    uncached = []

    for asn in asns:
        s = str(asn)
        if use_cache and s in cache:
            continue
        uncached.append(asn)

    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_one(session, asn) for asn in uncached]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for item in results:
        if isinstance(item, Exception):
            continue
        asn, prefixes = item
        cache[asn] = prefixes

    save_cache(cache)

    all_prefixes = []
    for v in cache.values():
        all_prefixes.extend(v)

    return sorted(set(all_prefixes))

def get_prefixes_sync(asns, use_cache=True, concurrency=20):
    return asyncio.run(fetch_all(asns, use_cache=use_cache, concurrency=concurrency))
