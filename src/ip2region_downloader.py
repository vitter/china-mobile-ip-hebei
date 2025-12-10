import requests
import time
from pathlib import Path

URLS = [
    # ip2region_update 增强版 (n版) - 推荐使用
    # 数据更全面，识别率比官方免费版提升 23%
    "https://github.com/hel2o/ip2region_update/releases/download/250820/ip2region_n.xdb",
    
    # CDN 镜像加速
    "https://ghproxy.net/https://github.com/hel2o/ip2region_update/releases/download/250820/ip2region_n.xdb",
    "https://gh-proxy.org/https://github.com/hel2o/ip2region_update/releases/download/250820/ip2region_n.xdb",
    
    # 备用：官方免费版（数据不全，不推荐）
    "https://raw.githubusercontent.com/lionsoul2014/ip2region/master/data/ip2region_v4.xdb",
]

def get_db_path():
    """获取数据库文件的绝对路径"""
    from pathlib import Path
    return Path(__file__).parent.parent / 'data' / 'ip2region_v4.xdb'

DB_PATH = get_db_path()

def http_download(url, file_path, retry=3):
    for i in range(retry):
        try:
            print(f"Downloading: {url} (attempt {i+1}/{retry})")
            with requests.get(url, timeout=30, stream=True) as r:
                r.raise_for_status()
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return True
        except Exception as e:
            print(f"[WARN] failed: {e}")
            time.sleep(1)
    return False


def download_xdb():
    p = Path(DB_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)

    if p.exists() and p.stat().st_size > 0:
        print("ip2region_v4.xdb already exists, skip download.")
        return

    for url in URLS:
        if http_download(url, DB_PATH):
            print(f"[OK] downloaded from {url}")
            return

    raise RuntimeError("❌ All download URLs failed! Please check network.")
