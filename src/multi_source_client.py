"""
多数据源 IP 查询客户端
结合多个 IP 数据库提高查询准确性
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent))

from ip2region_client import IP2RegionClient
from qqwry_client import QQWryClient


class MultiSourceIPClient:
    """
    多数据源 IP 查询客户端
    
    策略 (针对 n 版 + 纯真补充):
    1. 优先使用 n 版 ip2region（数据最准确，识别率最高）
    2. 如果 n 版省份字段为空（约10%的情况），使用纯真 IP 补充
    3. 补充时需验证纯真数据准确性：
       - 只在纯真明确显示"河北"时才使用
       - 如果纯真显示其他省份，保持 n 版结果（避免误判）
    4. 优势：可将识别率从 3,544 提升至 ~3,900+
    """
    
    def __init__(self, ip2region_path=None, qqwry_path=None):
        """
        初始化多数据源客户端
        
        Args:
            ip2region_path: ip2region 数据库路径
            qqwry_path: 纯真 IP 数据库路径
        """
        # 默认路径
        if ip2region_path is None:
            ip2region_path = Path(__file__).parent.parent / 'data' / 'ip2region_v4.xdb'
        if qqwry_path is None:
            qqwry_path = Path(__file__).parent.parent / 'data' / 'qqwry.dat'
        
        # 加载 ip2region
        self.ip2region = None
        if Path(ip2region_path).exists():
            try:
                self.ip2region = IP2RegionClient(ip2region_path)
                print(f"✓ 已加载 ip2region 数据库")
            except Exception as e:
                print(f"✗ ip2region 加载失败: {e}")
        else:
            print(f"✗ ip2region 数据库不存在: {ip2region_path}")
        
        # 加载纯真 IP
        self.qqwry = None
        if Path(qqwry_path).exists():
            try:
                self.qqwry = QQWryClient(qqwry_path)
                print(f"✓ 已加载纯真 IP 数据库")
            except Exception as e:
                print(f"✗ 纯真 IP 加载失败: {e}")
        else:
            print(f"⚠ 纯真 IP 数据库不存在: {qqwry_path} (可选)")
    
    def search(self, ip: str) -> Dict[str, str]:
        """
        查询 IP 地址的地理信息
        
        Args:
            ip: IP 地址字符串
            
        Returns:
            字典包含各数据源的查询结果
        """
        results = {
            'ip': ip,
            'ip2region': None,
            'qqwry': None,
            'final': None,
            'source': None
        }
        
        # 查询 ip2region
        if self.ip2region:
            try:
                results['ip2region'] = self.ip2region.search(ip)
            except:
                pass
        
        # 查询纯真 IP
        if self.qqwry:
            try:
                results['qqwry'] = self.qqwry.search(ip)
            except:
                pass
        
        # 决定最终结果
        results['final'], results['source'] = self._choose_best_result(results)
        
        return results
    
    def _choose_best_result(self, results: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        从多个数据源中选择最佳结果
        
        优化策略 (针对 n 版 + 纯真):
        1. n版优先：如果省份字段有值且不为空，直接使用
        2. 智能补充：n版省份为空时，检查纯真是否明确显示"河北"
        3. 保守原则：纯真显示其他省份时，保持 n版 结果（避免误判）
        """
        ip2region_result = results.get('ip2region')
        qqwry_result = results.get('qqwry')
        
        # 检查 n版 是否有完整省份信息
        if ip2region_result and '|' in ip2region_result:
            parts = ip2region_result.split('|')
            province = parts[1] if len(parts) > 1 else ''
            
            # n版有省份信息，直接使用
            if province and province not in ['0', '']:
                return ip2region_result, 'ip2region'
            
            # n版省份缺失，检查是否可以用纯真补充
            if qqwry_result and '河北' in qqwry_result and '移动' in qqwry_result:
                # 纯真明确显示"河北+移动"，可以使用
                return qqwry_result, 'qqwry_补充'
            
            # 纯真没有河北信息，保持 n版 原结果
            return ip2region_result, 'ip2region_incomplete'
        
        # n版无数据，尝试纯真
        if qqwry_result:
            return qqwry_result, 'qqwry_fallback'
        
        return None, None
    
    def is_hebei_mobile(self, ip: str) -> Tuple[bool, str]:
        """
        判断 IP 是否属于河北移动
        
        Args:
            ip: IP 地址字符串
            
        Returns:
            (is_hebei_mobile, reason): 布尔值和判断依据
        """
        results = self.search(ip)
        final_result = results['final']
        source = results['source']
        
        if not final_result:
            return False, "no_data"
        
        # 统一检查：在整个结果字符串中搜索关键字（适配多种格式）
        result_text = final_result
        
        # 检查是否包含"河北"
        hebei_keywords = ['河北', '河北省']
        has_hebei = any(kw in result_text for kw in hebei_keywords)
        
        # 检查是否包含"移动"
        mobile_keywords = ['移动', '中国移动']
        has_mobile = any(kw in result_text for kw in mobile_keywords)
        
        is_hebei_mobile = has_hebei and has_mobile
        
        return is_hebei_mobile, f"{source}: {result_text[:50]}"
        
        return False, "unknown_format"
    
    def get_stats(self) -> Dict[str, bool]:
        """
        获取数据源加载状态
        
        Returns:
            各数据源的可用状态
        """
        return {
            'ip2region': self.ip2region is not None,
            'qqwry': self.qqwry is not None,
            'total_sources': sum([
                self.ip2region is not None,
                self.qqwry is not None
            ])
        }


if __name__ == '__main__':
    # 测试代码
    client = MultiSourceIPClient()
    
    stats = client.get_stats()
    print(f"\n数据源状态: {stats['total_sources']} 个可用\n")
    print("=" * 80)
    
    test_ips = [
        '111.55.24.114',   # 问题 IP（ip2region 显示为 0）
        '111.11.0.1',      # 已知河北移动
        '183.196.0.1',     # 已知河北移动
        '8.8.8.8',         # Google DNS
        '114.114.114.114', # 国内 DNS
    ]
    
    print(f"{'IP 地址':<18} {'数据源':<15} {'结果':<50} {'河北移动'}")
    print("-" * 80)
    
    for ip in test_ips:
        results = client.search(ip)
        is_hebei, reason = client.is_hebei_mobile(ip)
        
        source = results['source'] or 'N/A'
        final = results['final'] or 'N/A'
        
        print(f"{ip:<18} {source:<15} {final[:48]:<50} {is_hebei}")
    
    print("\n" + "=" * 80)
    print("\n详细结果:")
    print("-" * 80)
    
    for ip in test_ips[:2]:  # 只显示前两个的详细信息
        print(f"\nIP: {ip}")
        results = client.search(ip)
        print(f"  ip2region: {results['ip2region']}")
        print(f"  qqwry:     {results['qqwry']}")
        print(f"  最终:      {results['final']} (来源: {results['source']})")
        is_hebei, reason = client.is_hebei_mobile(ip)
        print(f"  判断:      河北移动={is_hebei} ({reason})")
