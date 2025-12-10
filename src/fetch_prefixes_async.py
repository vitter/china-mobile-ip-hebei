import aiohttp
import asyncio
import json
import ipaddress
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# 获取项目根目录下的data目录
CACHE_PATH = Path(__file__).parent.parent / 'data' / 'prefixes_cache.json'
# 使用RIPEstat API - 公开且无需认证
API_URL = "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}"
# 缓存有效期（天）
CACHE_EXPIRY_DAYS = 7
# API 请求配置
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 2  # 重试延迟（秒）
REQUEST_DELAY = 0.5  # 请求间延迟（秒），避免触发速率限制

def is_cache_expired(cache_data: dict) -> bool:
    """检查缓存是否过期"""
    if 'timestamp' not in cache_data:
        return True
    
    cache_time = datetime.fromtimestamp(cache_data['timestamp'])
    expiry_time = cache_time + timedelta(days=CACHE_EXPIRY_DAYS)
    is_expired = datetime.now() >= expiry_time
    
    if is_expired:
        age_days = (datetime.now() - cache_time).days
        print(f"⏰ 缓存已过期（{age_days} 天前创建，有效期 {CACHE_EXPIRY_DAYS} 天）")
    else:
        age_days = (datetime.now() - cache_time).days
        remaining_days = CACHE_EXPIRY_DAYS - age_days
        print(f"✓ 缓存仍有效（{age_days} 天前创建，还剩 {remaining_days} 天）")
    
    return is_expired

def load_cache() -> Dict[str, List[str]]:
    if CACHE_PATH.exists():
        try:
            content = CACHE_PATH.read_text(encoding="utf-8")
            if content.strip():
                cache_data = json.loads(content)
                
                # 检查缓存是否过期
                if is_cache_expired(cache_data):
                    print("🗑️  删除过期缓存")
                    CACHE_PATH.unlink()
                    return {}
                
                # 返回缓存的前缀数据（不包括元数据）
                return {k: v for k, v in cache_data.items() if k not in ['timestamp', 'version']}
        except (json.JSONDecodeError, ValueError):
            pass
    return {}

def save_cache(cache: Dict[str, List[str]]):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 添加时间戳和版本信息
    cache_data = {
        'timestamp': time.time(),
        'version': '1.0',
        **cache
    }
    
    CACHE_PATH.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding="utf-8")
    cache_time = datetime.fromtimestamp(cache_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
    print(f"💾 缓存已保存（创建时间: {cache_time}，有效期: {CACHE_EXPIRY_DAYS} 天）")

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

async def fetch_one(session: aiohttp.ClientSession, asn: int, semaphore: asyncio.Semaphore):
    """
    获取单个 ASN 的前缀，带重试和速率限制
    """
    url = API_URL.format(asn=asn)
    
    async with semaphore:  # 限制并发数
        for attempt in range(MAX_RETRIES):
            try:
                # 添加请求延迟，避免触发速率限制
                if attempt > 0:
                    delay = RETRY_DELAY * (2 ** (attempt - 1))  # 指数退避
                    print(f"  AS{asn}: Retry {attempt}/{MAX_RETRIES} after {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    await asyncio.sleep(REQUEST_DELAY)
                
                async with session.get(url, timeout=30) as r:
                    # 处理速率限制
                    if r.status == 429:
                        retry_after = int(r.headers.get('Retry-After', RETRY_DELAY * 2))
                        print(f"⚠️  AS{asn}: Rate limited, waiting {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    # 处理服务器错误（502, 503 等）
                    if r.status in [502, 503, 504]:
                        print(f"⚠️  AS{asn}: Server error {r.status}, retrying...")
                        continue
                    
                    if r.status != 200:
                        print(f"⚠️  AS{asn}: HTTP {r.status}")
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
                    
                    print(f"✓ AS{asn}: {len(prefixes)} IPv4 prefixes")
                    return str(asn), sorted(set(prefixes))
                    
            except asyncio.TimeoutError:
                print(f"⏱️  AS{asn}: Timeout (attempt {attempt + 1}/{MAX_RETRIES})")
            except Exception as e:
                print(f"❌ AS{asn}: {type(e).__name__}: {e}")
                if attempt == MAX_RETRIES - 1:
                    return str(asn), []
        
        # 所有重试都失败
        print(f"❌ AS{asn}: Failed after {MAX_RETRIES} attempts")
        return str(asn), []

async def fetch_all(asns: List[int], use_cache=True, concurrency=5):
    """
    并发获取多个 ASN 的前缀
    
    Args:
        asns: ASN 列表
        use_cache: 是否使用缓存
        concurrency: 并发数（默认 5，避免触发 API 速率限制）
    """
    print(f"\n🔍 Total ASNs to process: {len(asns)}")
    print(f"📋 Use cache: {use_cache}, Concurrency: {concurrency}")
    
    cache = load_cache() if use_cache else {}
    print(f"💾 Loaded cache contains {len(cache)} ASNs")
    
    tasks = []
    uncached = []

    for asn in asns:
        s = str(asn)
        if use_cache and s in cache:
            continue
        uncached.append(asn)
    
    print(f"📊 Cached: {len(asns) - len(uncached)}, Need to fetch: {len(uncached)}")

    if not uncached:
        print("✓ All ASNs found in cache")
    else:
        print(f"📡 Fetching {len(uncached)} ASNs (concurrency: {concurrency})...")
    
    # 使用信号量限制并发数
    semaphore = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit=concurrency * 2)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_one(session, asn, semaphore) for asn in uncached]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for item in results:
        if isinstance(item, Exception):
            continue
        asn, prefixes = item
        cache[asn] = prefixes

    # 在保存缓存前拆分大网段，确保缓存中保存的是已拆分的 /24 子网
    print("\n正在拆分大网段 (>=/24)...")
    total_before = sum(len(prefixes) for prefixes in cache.values())
    print(f"📊 Prefixes before split: {total_before}")
    
    for asn_str, prefixes in cache.items():
        split_result = split_large_prefixes(prefixes)
        cache[asn_str] = split_result
    
    total_after = sum(len(prefixes) for prefixes in cache.values())
    print(f"📊 Prefixes after split: {total_after}")
    
    save_cache(cache)

    all_prefixes = []
    for v in cache.values():
        all_prefixes.extend(v)
    
    unique_count = len(set(all_prefixes))
    print(f"📊 Total unique prefixes to return: {unique_count}")
    
    return sorted(set(all_prefixes))

def get_prefixes_sync(asns, use_cache=True, concurrency=5):
    """
    同步方式获取前缀（内部使用异步）
    
    Args:
        asns: ASN 列表
        use_cache: 是否使用缓存
        concurrency: 并发数（默认 5）
    """
    return asyncio.run(fetch_all(asns, use_cache=use_cache, concurrency=concurrency))
