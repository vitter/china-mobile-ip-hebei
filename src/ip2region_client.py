import io
from pathlib import Path
import sys

# 添加ip2region的binding/python路径
sys.path.insert(0, str(Path(__file__).parent / 'ip2region'))

import util
import searcher as xdb_searcher


class IP2RegionClient:
    def __init__(self, db_path):
        self.db_path = str(Path(db_path))
        
        # 打开xdb文件
        handle = io.open(self.db_path, "rb")
        
        # 获取header和version
        header = util.load_header(handle)
        self.version = util.version_from_header(header)
        if self.version is None:
            handle.close()
            raise Exception("failed to get version from header")
        
        # 加载vector index以提升性能
        v_index = util.load_vector_index(handle)
        handle.close()
        
        # 创建searcher
        self.searcher = xdb_searcher.new_with_vector_index(self.version, self.db_path, v_index)

    def search(self, ip):
        """查询IP地址的区域信息"""
        return self.searcher.search(ip)
    
    def lookup_region_str(self, ip):
        """查询IP地址的区域信息（兼容旧API）"""
        return self.search(ip)
    
    def is_hebei_mobile(self, ip):
        """判断IP是否属于河北移动"""
        try:
            region = self.search(ip)
            if region and '|' in region:
                parts = region.split('|')
                # 格式: 国家|省份|城市|ISP
                if len(parts) >= 4:
                    province = parts[1] if len(parts) > 1 else ''
                    isp = parts[3] if len(parts) > 3 else ''
                    # 检查是否为河北省且运营商包含"移动"
                    return '河北' in province and '移动' in isp
            return False
        except Exception:
            return False
    
    def close(self):
        """关闭searcher"""
        if self.searcher:
            self.searcher.close()
