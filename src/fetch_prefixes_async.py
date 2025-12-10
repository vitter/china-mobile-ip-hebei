import aiohttp
import asyncio
import json
import ipaddress
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

def split_large_prefixes(prefixes: List[str], max_prefixlen: int = 24) -> List[str]:
    """
    将大网段（掩码位数 < max_prefixlen）拆分成小网段
    
    Args:
        prefixes: CIDR 列表
        max_prefixlen: 最大掩码位数，默认 24（一个 C 类网段）
    
    Returns:
        拆分后的 CIDR 列表
    
    Example:
        ['10.0.0.0/22'] -> ['10.0.0.0/24', '10.0.1.0/24', '10.0.2.0/24', '10.0.3.0/24']
    """
    result = []
    split_count = 0
    
    for cidr in prefixes:
        try:
            network = ipaddress.IPv4Network(cidr, strict=False)
            
            # 如果网段已经是 /24 或更小，直接保留
            if network.prefixlen >= max_prefixlen:
                result.append(str(network))
            else:
                # 拆分成 /24 子网
                subnets = list(network.subnets(new_prefix=max_prefixlen))
                result.extend([str(subnet) for subnet in subnets])
                split_count += 1
                
                # 输出拆分信息（仅对大网段）
                if network.prefixlen <= 20:  # 只显示 /20 及以上的大网段拆分信息
                    print(f"  Split {cidr} -> {len(subnets)} x /{max_prefixlen} subnets")
        
        except Exception as e:
            print(f"Warning: Failed to parse {cidr}: {e}")
            result.append(cidr)  # 解析失败，保留原样
    
    if split_count > 0:
        print(f"✓ Split {split_count} large prefixes into {len(result)} subnets (/{max_prefixlen})")
    
    return sorted(set(result))

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

    # 在保存缓存前拆分大网段，确保缓存中保存的是已拆分的 /24 子网
    print("\n正在拆分大网段 (>=/24)...")
    for asn_str, prefixes in cache.items():
        cache[asn_str] = split_large_prefixes(prefixes)
    
    save_cache(cache)

    all_prefixes = []
    for v in cache.values():
        all_prefixes.extend(v)
    
    return sorted(set(all_prefixes))

def get_prefixes_sync(asns, use_cache=True, concurrency=20):
    return asyncio.run(fetch_all(asns, use_cache=use_cache, concurrency=concurrency))
