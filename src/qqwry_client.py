"""
纯真 IP 数据库查询客户端
用于补充 ip2region 数据不全的问题
"""
import struct
import socket
from pathlib import Path


class QQWryClient:
    """纯真 IP 数据库查询客户端"""
    
    def __init__(self, db_path):
        """
        初始化纯真 IP 数据库
        
        Args:
            db_path: qqwry.dat 文件路径
        """
        self.db_path = str(Path(db_path))
        self.db = None
        self.idx_start = 0
        self.idx_end = 0
        
        try:
            self._load_db()
        except Exception as e:
            print(f"Warning: Failed to load QQWry database: {e}")
            self.db = None
    
    def _load_db(self):
        """加载数据库文件"""
        with open(self.db_path, 'rb') as f:
            self.db = f.read()
        
        # 读取索引区起始和结束位置
        self.idx_start = struct.unpack('<I', self.db[0:4])[0]
        self.idx_end = struct.unpack('<I', self.db[4:8])[0]
    
    def _read_string(self, offset):
        """读取以 \x00 结尾的字符串"""
        if not self.db or offset >= len(self.db):
            return ""
        
        end = self.db.find(b'\x00', offset)
        if end == -1:
            return ""
        
        try:
            return self.db[offset:end].decode('gbk', errors='ignore')
        except:
            return ""
    
    def _read_area(self, offset):
        """读取地区信息"""
        if not self.db or offset >= len(self.db):
            return ""
        
        mode = self.db[offset]
        
        if mode == 0x01 or mode == 0x02:
            # 重定向模式
            offset = struct.unpack('<I', self.db[offset+1:offset+4] + b'\x00')[0]
            if offset == 0:
                return ""
            return self._read_string(offset)
        else:
            return self._read_string(offset)
    
    def search(self, ip):
        """
        查询 IP 地址的地理信息
        
        Args:
            ip: IP 地址字符串
            
        Returns:
            地理信息字符串，格式: "国家 地区"
        """
        if not self.db:
            return None
        
        try:
            ip_int = struct.unpack('!I', socket.inet_aton(ip))[0]
        except:
            return None
        
        # 二分查找
        left = 0
        right = (self.idx_end - self.idx_start) // 7
        
        while left <= right:
            mid = (left + right) // 2
            offset = self.idx_start + mid * 7
            
            start_ip = struct.unpack('<I', self.db[offset:offset+4])[0]
            
            if ip_int < start_ip:
                right = mid - 1
            else:
                # 读取记录偏移
                rec_offset = struct.unpack('<I', self.db[offset+4:offset+7] + b'\x00')[0]
                end_ip = struct.unpack('<I', self.db[rec_offset:rec_offset+4])[0]
                
                if ip_int > end_ip:
                    left = mid + 1
                else:
                    # 找到了
                    return self._parse_record(rec_offset + 4)
        
        return None
    
    def _parse_record(self, offset):
        """解析记录"""
        if not self.db or offset >= len(self.db):
            return None
        
        mode = self.db[offset]
        
        if mode == 0x01:
            # 国家和地区都重定向
            offset = struct.unpack('<I', self.db[offset+1:offset+4] + b'\x00')[0]
            mode = self.db[offset]
            
            if mode == 0x02:
                # 国家重定向，地区可能重定向
                country_offset = struct.unpack('<I', self.db[offset+1:offset+4] + b'\x00')[0]
                country = self._read_string(country_offset)
                area = self._read_area(offset + 4)
            else:
                # 国家和地区都在这里
                country = self._read_string(offset)
                area = self._read_area(offset + len(country.encode('gbk')) + 1)
        
        elif mode == 0x02:
            # 国家重定向
            country_offset = struct.unpack('<I', self.db[offset+1:offset+4] + b'\x00')[0]
            country = self._read_string(country_offset)
            area = self._read_area(offset + 4)
        
        else:
            # 国家和地区都在这里
            country = self._read_string(offset)
            area = self._read_area(offset + len(country.encode('gbk')) + 1)
        
        return f"{country} {area}".strip()
    
    def is_hebei_mobile(self, ip):
        """
        判断 IP 是否属于河北移动
        
        Args:
            ip: IP 地址字符串
            
        Returns:
            bool: True 表示是河北移动
        """
        result = self.search(ip)
        if not result:
            return False
        
        # 纯真数据库的格式不固定，需要灵活匹配
        result_lower = result.lower()
        
        # 检查是否包含河北相关关键词
        hebei_keywords = ['河北', 'hebei', '石家庄', 'shijiazhuang', '唐山', '秦皇岛', 
                          '邯郸', '邢台', '保定', '张家口', '承德', '沧州', '廊坊', '衡水']
        has_hebei = any(kw in result_lower for kw in hebei_keywords)
        
        # 检查是否包含移动相关关键词
        mobile_keywords = ['移动', 'mobile', 'cmcc', '中国移动']
        has_mobile = any(kw in result_lower for kw in mobile_keywords)
        
        return has_hebei and has_mobile


def download_qqwry():
    """
    下载纯真 IP 数据库
    
    注意: 纯真 IP 数据库需要从官方网站或镜像下载
    官方: https://cz88.net/
    """
    print("请从以下地址下载纯真 IP 数据库 (qqwry.dat):")
    print("  官方: https://cz88.net/")
    print("  或搜索: 纯真IP数据库下载")
    print("\n下载后请放置到: data/qqwry.dat")


if __name__ == '__main__':
    # 测试代码
    import sys
    
    db_path = Path(__file__).parent.parent / 'data' / 'qqwry.dat'
    
    if not db_path.exists():
        print(f"纯真 IP 数据库不存在: {db_path}")
        download_qqwry()
        sys.exit(1)
    
    client = QQWryClient(db_path)
    
    test_ips = [
        '111.55.24.114',   # 测试案例（ip2region 显示为 0）
        '111.11.0.1',      # 已知河北移动
        '8.8.8.8',         # Google DNS
    ]
    
    print("测试纯真 IP 数据库:\n")
    for ip in test_ips:
        result = client.search(ip)
        is_hebei = client.is_hebei_mobile(ip)
        print(f"{ip:18} -> {result:50} [河北移动: {is_hebei}]")
