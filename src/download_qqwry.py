#!/usr/bin/env python3
"""
纯真 IP 数据库下载器

纯真 IP 数据库 (qqwry.dat) 是一个免费的 IP 地址数据库，
包含详细的地理位置和运营商信息。

使用方法:
    python download_qqwry.py
"""
import requests
from pathlib import Path
import sys


def download_qqwry():
    """
    下载纯真 IP 数据库
    
    注意: 纯真 IP 数据库有多个镜像源，这里提供几个选项
    """
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = data_dir / 'qqwry.dat'
    
    print("=" * 70)
    print("纯真 IP 数据库下载器")
    print("=" * 70)
    
    print("\n可用的下载源:\n")
    
    # 提供多个下载源
    sources = [
        {
            'name': 'GitHub 镜像（推荐）',
            'url': 'https://raw.githubusercontent.com/FW27623/qqwry/master/qqwry.dat',
            'note': '自动下载（约 10 MB）',
            'auto': True
        },
        {
            'name': 'jsdelivr CDN',
            'url': 'https://cdn.jsdelivr.net/gh/FW27623/qqwry@master/qqwry.dat',
            'note': '自动下载（CDN加速）',
            'auto': True
        },
        {
            'name': 'jsDelivr 备用',
            'url': 'https://fastly.jsdelivr.net/gh/FW27623/qqwry@master/qqwry.dat',
            'note': '自动下载（Fastly CDN）',
            'auto': True
        }
    ]
    
    for i, source in enumerate(sources, 1):
        auto_mark = "✓" if source['auto'] else "✗"
        print(f"{i}. [{auto_mark}] {source['name']}")
        print(f"   URL: {source['url']}")
        print(f"   说明: {source['note']}\n")
    
    print("=" * 70)
    
    # 尝试自动下载
    auto_sources = [s for s in sources if s['auto']]
    
    for source in auto_sources:
        print(f"\n尝试从 {source['name']} 下载...")
        print(f"URL: {source['url']}")
        
        try:
            print("正在下载... (约 10 MB)")
            response = requests.get(source['url'], timeout=30, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = downloaded / total_size * 100
                            print(f"\r下载进度: {progress:.1f}% ({downloaded:,}/{total_size:,} bytes)", end='')
            
            print(f"\n\n✓ 下载成功!")
            print(f"✓ 保存到: {output_path}")
            
            # 验证文件
            file_size = output_path.stat().st_size
            print(f"✓ 文件大小: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
            
            if file_size < 1024 * 1024:  # 小于 1 MB 可能有问题
                print("⚠ 警告: 文件大小异常，可能下载不完整")
                output_path.unlink()
                continue
            
            print("\n下载完成! 现在可以使用多数据源查询了。")
            return True
            
        except Exception as e:
            print(f"\n✗ 下载失败: {e}")
            if output_path.exists():
                output_path.unlink()
            continue
    
    print("\n" + "=" * 70)
    print("自动下载失败，请手动下载:")
    print("=" * 70)
    print("\n1. 访问官方网站: https://cz88.net/")
    print("2. 下载 qqwry.dat 文件")
    print(f"3. 将文件复制到: {output_path}")
    print("\n或者使用以下命令手动下载:")
    print(f"\n  curl -L -o {output_path} \\")
    print(f"    {auto_sources[0]['url']}")
    
    return False


if __name__ == '__main__':
    success = download_qqwry()
    sys.exit(0 if success else 1)
