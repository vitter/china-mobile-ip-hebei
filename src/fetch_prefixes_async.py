import aiohttp
import asyncio
import json
from pathlib import Path
from typing import Dict, List

# 获取项目根目录下的data目录
CACHE_PATH = Path(__file__).parent.parent / 'data' / 'prefixes_cache.json'
# 使用RIPEstat API - 公开且无需认证
API_URL = "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}"

def load_cache() -> Dict[str, List[str]]:
    if CACHE_PATH.exists():
        try:
            content = CACHE_PATH.read_text(encoding="utf-8")
            if content.strip():
                return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            pass
    return {}

def save_cache(cache: Dict[str, List[str]]):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")

async def fetch_one(session: aiohttp.ClientSession, asn: int):
    url = API_URL.format(asn=asn)
    try:
        async with session.get(url, timeout=30) as r:
            if r.status != 200:
                print(f"Warning: AS{asn} returned status {r.status}")
                return str(asn), []
            
            data = await r.json()
            # RIPEstat API 返回格式: data.prefixes[].prefix
            prefixes = []
            if 'data' in data and 'prefixes' in data['data']:
                for item in data['data']['prefixes']:
                    prefix = item.get('prefix', '')
                    # 只获取IPv4前缀
                    if prefix and ':' not in prefix:
                        prefixes.append(prefix)
            
            print(f"AS{asn}: fetched {len(prefixes)} IPv4 prefixes")
            return str(asn), sorted(set(prefixes))
    except Exception as e:
        print(f"Error fetching AS{asn}: {e}")
        return str(asn), []

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
