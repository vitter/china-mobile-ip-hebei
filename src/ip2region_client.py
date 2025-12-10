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
        """判断IP是否属于河北移动
        
        支持多种数据库格式:
        - 标准v3: 国家|省份|城市|ISP
        - 增强版: |国家|省份|城市|区域|街道|ISP|经度|维度
        - qqwry: 中国–省份|ISP
        - n版本: 国家|省份||||ISP
        """
        try:
            region = self.search(ip)
            if not region:
                return False
            
            # 将整个字符串转为小写进行匹配，提高容错性
            region_lower = region.lower()
            full_text = region  # 保留原文用于检查
            
            # 检查是否包含"河北"和"移动"关键字（在整个字符串中搜索）
            has_hebei = '河北' in full_text or '河北省' in full_text
            has_mobile = '移动' in full_text or '中国移动' in full_text or 'mobile' in region_lower
            
            return has_hebei and has_mobile
            
        except Exception:
            return False
    
    def close(self):
        """关闭searcher"""
        if self.searcher:
            self.searcher.close()
