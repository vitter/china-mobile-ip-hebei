#!/usr/bin/env python3
"""
CIDR合并工具
将连续的IP地址段合并成更大的网段，减少结果数量
"""
import ipaddress
from typing import List, Set


def merge_cidrs(cidrs: List[str]) -> List[str]:
    """
    保守合并CIDR列表，只合并完全连续的地址段，不扩大覆盖范围
    
    策略：只有当相邻的两个同等级网段可以精确合并为一个更大网段时才合并
    例如：1.2.0.0/24 + 1.2.1.0/24 → 1.2.0.0/23 ✓
         1.2.0.0/24 + 1.2.2.0/24 → 不合并 ✗ (中间缺失1.2.1.0/24)
    
    Args:
        cidrs: CIDR字符串列表
    
    Returns:
        合并后的CIDR列表（保证覆盖范围完全一致）
    """
    if not cidrs:
        return []
    
    # 解析所有CIDR为IPv4Network对象
    networks = []
    for cidr in cidrs:
        try:
            net = ipaddress.IPv4Network(cidr, strict=False)
            networks.append(net)
        except Exception as e:
            print(f"Warning: 无法解析CIDR {cidr}: {e}")
            continue
    
    if not networks:
        return []
    
    # 按网络地址排序
    networks.sort(key=lambda x: (x.network_address, x.prefixlen))
    
    # 去重和合并重叠（仅使用collapse_addresses处理重叠情况）
    # 但要注意：collapse_addresses会扩大范围，所以我们需要验证
    collapsed = list(ipaddress.collapse_addresses(networks))
    
    # 验证合并是否保持覆盖范围一致
    # 如果collapsed的总IP数等于原始的总IP数，说明是安全的合并
    original_ip_count = sum(net.num_addresses for net in networks)
    collapsed_ip_count = sum(net.num_addresses for net in collapsed)
    
    if collapsed_ip_count == original_ip_count:
        # 安全合并，覆盖范围一致
        return [str(net) for net in collapsed]
    else:
        # collapse_addresses扩大了范围，使用保守策略
        return merge_conservative(networks)


def merge_conservative(networks: List[ipaddress.IPv4Network]) -> List[str]:
    """
    保守合并策略：只合并完全连续的相邻网段
    
    算法：对于两个相邻的同等级网段，只有当它们恰好组成一对时才合并
    例如：x.x.0.0/24 和 x.x.1.0/24 → x.x.0.0/23
    """
    if not networks:
        return []
    
    # 已经排序
    result = []
    i = 0
    
    while i < len(networks):
        current = networks[i]
        
        # 尝试与下一个合并
        if i + 1 < len(networks):
            next_net = networks[i + 1]
            
            # 只有同等级才尝试合并
            if current.prefixlen == next_net.prefixlen:
                try:
                    # 计算应该合并成的超网
                    supernet = current.supernet(prefixlen_diff=1)
                    
                    # 检查超网是否恰好包含这两个网段（不多不少）
                    subnets = list(supernet.subnets(prefixlen_diff=1))
                    if len(subnets) == 2 and current in subnets and next_net in subnets:
                        # 可以安全合并
                        result.append(supernet)
                        i += 2  # 跳过下一个
                        continue
                except Exception:
                    pass
        
        # 无法合并，保留原样
        result.append(current)
        i += 1
    
    # 递归合并（可能出现更大的连续段）
    if len(result) < len(networks):
        # 继续尝试合并
        return merge_conservative(result)
    else:
        # 无法进一步合并
        return [str(net) for net in result]


def merge_cidrs_aggressive(cidrs: List[str]) -> List[str]:
    """
    激进合并模式：尝试将相邻的网段合并成更大的超网
    即使它们不是完全连续的，只要能合并就合并
    
    Args:
        cidrs: CIDR字符串列表
    
    Returns:
        合并后的CIDR列表
    """
    if not cidrs:
        return []
    
    # 首先使用标准合并
    networks = []
    for cidr in cidrs:
        try:
            net = ipaddress.IPv4Network(cidr, strict=False)
            networks.append(net)
        except Exception:
            continue
    
    if not networks:
        return []
    
    # 排序
    networks.sort(key=lambda x: (x.network_address, x.prefixlen))
    
    # 第一步：使用collapse_addresses标准合并
    merged = list(ipaddress.collapse_addresses(networks))
    
    # 第二步：尝试进一步超网合并
    # 对于相邻的同等级网段，尝试合并成更大的超网
    changed = True
    while changed:
        changed = False
        new_merged = []
        skip_next = False
        
        for i in range(len(merged)):
            if skip_next:
                skip_next = False
                continue
            
            # 如果是最后一个，直接添加
            if i == len(merged) - 1:
                new_merged.append(merged[i])
                continue
            
            current = merged[i]
            next_net = merged[i + 1]
            
            # 尝试合并为超网
            try:
                # 检查是否可以合并（前缀长度相同，且可以组成一对）
                if current.prefixlen == next_net.prefixlen:
                    # 尝试创建超网
                    supernet = current.supernet(prefixlen_diff=1)
                    
                    # 检查超网是否恰好包含这两个网段
                    subnets = list(supernet.subnets(prefixlen_diff=1))
                    if len(subnets) == 2 and current in subnets and next_net in subnets:
                        new_merged.append(supernet)
                        skip_next = True
                        changed = True
                        continue
            except Exception:
                pass
            
            new_merged.append(current)
        
        merged = new_merged
    
    return [str(net) for net in merged]


def summarize_cidrs(original: List[str], merged: List[str]) -> str:
    """
    生成合并统计摘要
    
    Args:
        original: 原始CIDR列表
        merged: 合并后的CIDR列表
    
    Returns:
        统计摘要字符串
    """
    orig_count = len(original)
    merged_count = len(merged)
    reduction = orig_count - merged_count
    reduction_pct = (reduction / orig_count * 100) if orig_count > 0 else 0
    
    # 统计不同掩码位数的分布
    def count_by_prefix(cidrs):
        prefix_counts = {}
        for cidr in cidrs:
            try:
                prefixlen = ipaddress.IPv4Network(cidr, strict=False).prefixlen
                prefix_counts[prefixlen] = prefix_counts.get(prefixlen, 0) + 1
            except Exception:
                pass
        return prefix_counts
    
    orig_dist = count_by_prefix(original)
    merged_dist = count_by_prefix(merged)
    
    summary = f"""
CIDR合并统计
{'='*50}
原始网段数量: {orig_count}
合并后数量:   {merged_count}
减少数量:     {reduction} ({reduction_pct:.1f}%)

原始掩码分布:
{format_prefix_distribution(orig_dist)}

合并后掩码分布:
{format_prefix_distribution(merged_dist)}
"""
    return summary


def format_prefix_distribution(dist: dict) -> str:
    """格式化掩码位数分布"""
    lines = []
    for prefix in sorted(dist.keys()):
        count = dist[prefix]
        bar = '█' * min(50, count // max(1, max(dist.values()) // 50))
        lines.append(f"  /{prefix:2d}: {count:5d} {bar}")
    return '\n'.join(lines) if lines else "  (无数据)"


if __name__ == '__main__':
    # 测试示例
    test_cidrs = [
        '111.11.0.0/24',
        '111.11.1.0/24',
        '111.11.2.0/24',
        '111.11.3.0/24',
        '111.11.4.0/24',
        '111.11.5.0/24',
        '111.11.6.0/24',
        '111.11.7.0/24',
    ]
    
    print("原始CIDR:")
    for cidr in test_cidrs:
        print(f"  {cidr}")
    
    merged = merge_cidrs(test_cidrs)
    print(f"\n标准合并后 ({len(merged)} 个):")
    for cidr in merged:
        print(f"  {cidr}")
    
    aggressive = merge_cidrs_aggressive(test_cidrs)
    print(f"\n激进合并后 ({len(aggressive)} 个):")
    for cidr in aggressive:
        print(f"  {cidr}")
    
    print(summarize_cidrs(test_cidrs, aggressive))
